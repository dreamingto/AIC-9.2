"""Download only pinned official checkpoint files, with SHA256 verification and a lock."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
from urllib.request import ProxyHandler, Request, build_opener

from app.retrieval.providers.model_contract import (
    CLIP_MODEL,
    CLIP_REVISION,
    TEXT_MODEL,
    TEXT_REVISION,
)

FILES = {
    "bge": (
        TEXT_MODEL,
        TEXT_REVISION,
        [
            "config.json",
            "model.safetensors",
            "tokenizer.json",
            "tokenizer_config.json",
            "special_tokens_map.json",
            "vocab.txt",
            "README.md",
        ],
    ),
    "chinese_clip": (
        CLIP_MODEL,
        CLIP_REVISION,
        [
            "config.json",
            "preprocessor_config.json",
            "pytorch_model.bin",
            "vocab.txt",
            "README.md",
        ],
    ),
}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path("D:/codex-models/jitu-retrieval"))
    parser.add_argument("--endpoint", default="https://hf-mirror.com")
    parser.add_argument("--proxy")
    parser.add_argument(
        "--lock-output", type=Path, default=Path(__file__).with_name("models.lock.json")
    )
    args = parser.parse_args()
    opener = build_opener(ProxyHandler({"https": args.proxy} if args.proxy else {}))
    args.root.mkdir(parents=True, exist_ok=True)
    manifest = {"schema_version": 1, "models": {}, "download_endpoint": args.endpoint}
    for key, (repo, revision, files) in FILES.items():
        directory = args.root / key
        directory.mkdir(exist_ok=True)
        tree_url = f"{args.endpoint}/api/models/{repo}/revision/{revision}?blobs=true"
        request = Request(tree_url, headers={"User-Agent": "Mozilla/5.0"})
        with opener.open(request, timeout=45) as response:
            info = json.load(response)
            if info["sha"] != revision:
                raise ValueError("checkpoint revision mismatch")
            tree = {item["rfilename"]: item for item in info["siblings"]}
        records = {}
        for name in files:
            path = directory / name
            expected = tree[name].get("lfs", {}).get("sha256")
            cached_digest = None
            if path.exists():
                with path.open("rb") as file:
                    cached_digest = hashlib.file_digest(file, "sha256").hexdigest()
            if path.exists() and (not expected or cached_digest == expected):
                print(f"cached {key}/{name}", flush=True)
            else:
                url = f"{args.endpoint}/{repo}/resolve/{revision}/{name}"
                partial = path.with_suffix(path.suffix + ".part")
                print(f"download {key}/{name}", flush=True)
                request = Request(url + "?download=true", headers={"User-Agent": "Mozilla/5.0"})
                with opener.open(request, timeout=120) as response, partial.open("wb") as output:
                    while chunk := response.read(1024 * 1024):
                        output.write(chunk)
                with partial.open("rb") as file:
                    digest = hashlib.file_digest(file, "sha256").hexdigest()
                if expected and digest != expected:
                    raise ValueError(f"checkpoint SHA256 mismatch: {key}/{name}")
                os.replace(partial, path)
            with path.open("rb") as file:
                digest = hashlib.file_digest(file, "sha256").hexdigest()
            if not expected:
                content = path.read_bytes()
                git_hash = hashlib.sha1(
                    f"blob {len(content)}\0".encode() + content, usedforsecurity=False
                ).hexdigest()
                if git_hash != tree[name]["blobId"]:
                    raise ValueError(f"git blob mismatch: {key}/{name}")
            records[name] = {"sha256": digest, "bytes": path.stat().st_size}
        manifest["models"][key] = {"repo": repo, "revision": revision, "files": records}
        (args.root / "models.lock.json").write_text(
            json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
        )
    print("model downloads and checkpoint SHA256 checks complete", flush=True)
    args.lock_output.write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )


if __name__ == "__main__":
    main()
