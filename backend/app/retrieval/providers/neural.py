"""Strict HTTP adapters for a local, pinned neural worker. Never silently fallback."""

from __future__ import annotations

import base64
import io
import json
import math
from typing import Any
from urllib.request import ProxyHandler, Request, build_opener

from PIL import Image

from app.core.errors import DomainError
from app.retrieval.providers.base import OfflineProvider, ProviderHealth, VectorResult
from app.retrieval.providers.image_embedding import ImageSource, _open_image
from app.retrieval.providers.model_contract import MODEL_SPECS


class NeuralProvider(OfflineProvider):
    def __init__(self, modality: str, url: str, timeout: float = 60.0) -> None:
        spec = MODEL_SPECS[modality]
        self.modality = modality
        self.provider_name = str(spec["provider"])
        self.model_name = str(spec["model"])
        self.version = str(spec["version"])
        self.dimension = int(str(spec["dimension"]))
        self.preprocessing_contract = str(spec["contract"])
        self.url = url.rstrip("/")
        self.timeout = timeout

    def _request(self, route: str, payload: dict[str, Any] | None = None) -> Any:
        request = Request(
            self.url + route,
            data=json.dumps(payload).encode("utf-8") if payload is not None else None,
            headers={"Content-Type": "application/json"},
        )
        # Local worker traffic must never be sent to an internet/system proxy.
        timeout = min(3.0, self.timeout) if route == "/health" else self.timeout
        with build_opener(ProxyHandler({})).open(request, timeout=timeout) as response:
            return json.load(response)

    def _matches_identity(self, record: dict[str, Any]) -> bool:
        expected = self.metadata().as_dict()
        return all(
            record.get(key) == value for key, value in expected.items() if key != "latency_ms"
        )

    def health(self) -> ProviderHealth:
        available, detail = False, "本地模型服务不可用"
        try:
            response = self._request("/health")
            available = response.get("status") == "ready" and any(
                self._matches_identity(item) and item.get("available") is True
                for item in response.get("providers", [])
            )
            detail = (
                f"local neural / {response.get('device')} / artifacts SHA256 checked"
                if available
                else "模型版本或预处理契约不匹配"
            )
        except Exception:
            pass
        return ProviderHealth(
            self.provider_name,
            self.model_name,
            self.version,
            self.dimension,
            self.preprocessing_hash,
            available,
            detail,
        )

    def _encode(self, payload: dict[str, Any]) -> VectorResult:
        try:
            response = self._request("/encode", {"modality": self.modality, **payload})
            if not self._matches_identity(response["metadata"]):
                raise ValueError("model identity mismatch")
            vector = tuple(float(value) for value in response["vector"])
            norm = sum(value * value for value in vector)
            if (
                len(vector) != self.dimension
                or any(not math.isfinite(v) for v in vector)
                or not 0.99 <= norm <= 1.01
            ):
                raise ValueError("invalid model vector")
            latency = float(response["metadata"]["latency_ms"])
            if not math.isfinite(latency) or latency < 0:
                raise ValueError("invalid latency")
            return VectorResult(vector, self.metadata(latency))
        except Exception as exc:
            raise DomainError(
                "MODEL_UNAVAILABLE",
                "本地检索模型不可用或版本不匹配",
                503,
                {"provider": self.provider_name, "model": self.model_name},
            ) from exc


class NeuralTextEmbeddingProvider(NeuralProvider):
    def encode(self, text: str) -> VectorResult:
        return self._encode({"text": text[:20000], "query": False})

    def encode_query(self, text: str) -> VectorResult:
        return self._encode({"text": text[:20000], "query": True})


class NeuralImageEmbeddingProvider(NeuralProvider):
    def encode(self, source: ImageSource) -> VectorResult:
        with _open_image(source) as image:
            # Bound transport bytes even when an allowed JPEG expands to a noisy RGB PNG.
            image.thumbnail((1536, 1536), Image.Resampling.LANCZOS)
            output = io.BytesIO()
            image.save(output, format="PNG")
        return self._encode({"image_base64": base64.b64encode(output.getvalue()).decode("ascii")})
