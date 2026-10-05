"""Local, offline-only BGE and Chinese-CLIP worker in an isolated Python runtime."""

from __future__ import annotations

import base64
import hashlib
import io
import json
import os
import threading
import time
from contextlib import asynccontextmanager
from pathlib import Path

# Must precede torch/CUDA initialization for reproducible float32 inference.
os.environ.setdefault("CUBLAS_WORKSPACE_CONFIG", ":4096:8")
os.environ.setdefault("HF_HUB_OFFLINE", "1")
os.environ.setdefault("TRANSFORMERS_OFFLINE", "1")

import torch
from fastapi import FastAPI, HTTPException
from PIL import Image, ImageOps
from pydantic import BaseModel, Field
from transformers import AutoModel, AutoTokenizer, ChineseCLIPModel, ChineseCLIPProcessor

from app.retrieval.providers.model_contract import MODEL_SPECS, QUERY_INSTRUCTION

root = Path(os.environ.get("TUJI_MODEL_ROOT", "D:/codex-models/jitu-retrieval"))
device = os.environ.get("TUJI_MODEL_DEVICE", "cuda" if torch.cuda.is_available() else "cpu")
mutex = threading.Lock()
models = {}
cache = {}
lock_hash = ""


def verify_artifacts() -> None:
    global lock_hash
    content = (root / "models.lock.json").read_bytes()
    lock = json.loads(content)
    lock_hash = hashlib.sha256(content).hexdigest()
    for key, entry in lock["models"].items():
        expected = MODEL_SPECS["text" if key == "bge" else "image"]
        if entry["repo"] != expected["model"] or entry["revision"] != expected["version"]:
            raise ValueError("model revision does not match pinned contract")
        for filename, record in entry["files"].items():
            path = root / key / filename
            if path.resolve().parent != (root / key).resolve():
                raise ValueError("invalid model artifact path")
            with path.open("rb") as file:
                digest = hashlib.file_digest(file, "sha256").hexdigest()
            if digest != record["sha256"]:
                raise ValueError(f"model artifact hash mismatch: {key}/{filename}")
    if set(lock["models"]) != {"bge", "chinese_clip"}:
        raise ValueError("both model checkpoints are required")


@asynccontextmanager
async def lifespan(app):
    verify_artifacts()
    torch.set_num_threads(2)
    torch.use_deterministic_algorithms(True)
    torch.backends.cuda.matmul.allow_tf32 = False
    torch.backends.cudnn.allow_tf32 = False
    models["tokenizer"] = AutoTokenizer.from_pretrained(root / "bge", local_files_only=True)
    models["bge"] = (
        AutoModel.from_pretrained(root / "bge", local_files_only=True, trust_remote_code=False)
        .eval()
        .to(device)
    )
    models["processor"] = ChineseCLIPProcessor.from_pretrained(
        root / "chinese_clip", local_files_only=True
    )
    models["clip"] = (
        ChineseCLIPModel.from_pretrained(
            root / "chinese_clip", local_files_only=True, trust_remote_code=False
        )
        .eval()
        .to(device)
    )
    yield
    models.clear()
    cache.clear()


app = FastAPI(title="机图索隐本地检索模型", lifespan=lifespan)


class EncodeRequest(BaseModel):
    modality: str
    text: str | None = Field(default=None, max_length=20000)
    image_base64: str | None = Field(default=None, max_length=14 * 1024 * 1024)
    query: bool = False


def metadata(modality: str, latency_ms: float = 0.0):
    spec = MODEL_SPECS[modality]
    return {
        **{key: value for key, value in spec.items() if key != "contract"},
        "preprocessing_hash": hashlib.sha256(spec["contract"].encode()).hexdigest(),
        "latency_ms": latency_ms,
    }


@app.get("/health")
def health():
    return {
        "status": "ready",
        "device": device,
        "torch": torch.__version__,
        "artifact_lock_sha256": lock_hash,
        "providers": [
            {**metadata(modality), "available": bool(models)} for modality in MODEL_SPECS
        ],
    }


@app.post("/encode")
def encode(request: EncodeRequest):
    if request.modality not in MODEL_SPECS:
        raise HTTPException(422, "unknown modality")
    started = time.perf_counter()
    image = None
    if request.modality == "image":
        try:
            content = base64.b64decode(request.image_base64 or "", validate=True)
            if len(content) > 10 * 1024 * 1024:
                raise ValueError("image bytes exceed limit")
            with Image.open(io.BytesIO(content)) as source:
                if source.width * source.height > 25_000_000:
                    raise ValueError("image pixels exceed limit")
                image = ImageOps.exif_transpose(source).convert("RGB")
            value = hashlib.sha256(content).hexdigest()
        except Exception as exc:
            raise HTTPException(422, "invalid image") from exc
    else:
        if not request.text:
            raise HTTPException(422, "text is required")
        value = request.text
    cache_key = hashlib.sha256(f"{request.modality}:{request.query}:{value}".encode()).hexdigest()
    try:
        with mutex, torch.inference_mode():
            vector = cache.get(cache_key)
            if vector is None:
                if request.modality == "text":
                    text = (QUERY_INSTRUCTION if request.query else "") + request.text
                    inputs = models["tokenizer"](
                        text, return_tensors="pt", truncation=True, max_length=512
                    ).to(device)
                    features = models["bge"](**inputs).last_hidden_state[:, 0]
                elif request.modality == "clip_text":
                    inputs = models["processor"](
                        text=[request.text],
                        return_tensors="pt",
                        padding=True,
                        truncation=True,
                        max_length=52,
                    ).to(device)
                    features = models["clip"].get_text_features(**inputs)
                else:
                    inputs = models["processor"](images=image, return_tensors="pt").to(device)
                    features = models["clip"].get_image_features(**inputs)
                vector = torch.nn.functional.normalize(features.float(), dim=-1)[0].cpu().tolist()
                if len(cache) >= 512:
                    cache.pop(next(iter(cache)))
                cache[cache_key] = vector
        return {
            "vector": vector,
            "metadata": metadata(request.modality, (time.perf_counter() - started) * 1000),
        }
    finally:
        if image is not None:
            image.close()


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8767, log_level="info")
