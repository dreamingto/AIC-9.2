"""Optional OCR contracts for the V1.1-B real-book pilot.

The production dependency is intentionally optional.  A missing PaddleOCR
installation must be visible as unavailable rather than silently falling back
to the synthetic fixture text or an untracked OCR result.
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol

from app.core.errors import DomainError

from .base import OfflineProvider, ProviderHealth, ProviderMetadata


@dataclass(frozen=True, slots=True)
class OCRLine:
    """One OCR line in source-image pixel coordinates."""

    text: str
    bbox: tuple[float, float, float, float]
    confidence: float
    order: int
    candidates: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class OCRResult:
    raw_text: str
    lines: tuple[OCRLine, ...]
    metadata: ProviderMetadata
    status: str = "inferred"


class OCRProvider(Protocol):
    """Provider contract kept independent from PaddleOCR's changing API."""

    def health(self) -> ProviderHealth: ...

    def recognize(self, image: str | Path | bytes) -> OCRResult: ...


class UnavailableOCRProvider(OfflineProvider):
    """Explicit provider used when no OCR runtime is installed."""

    provider_name = "ocr"
    model_name = "unavailable"
    version = "0.0.0"
    dimension = 0
    preprocessing_contract = "real-pilot-ocr-contract-v1"

    def health(self) -> ProviderHealth:
        return ProviderHealth(
            provider=self.provider_name,
            model=self.model_name,
            version=self.version,
            dimension=0,
            preprocessing_hash=self.preprocessing_hash,
            available=False,
            details="OCR runtime is not installed; install the selected provider explicitly",
        )

    def recognize(self, image: str | Path | bytes) -> OCRResult:
        del image
        raise DomainError(
            "MODEL_UNAVAILABLE",
            "真实 OCR Provider 尚未安装，当前仅完成页面准备",
            503,
        )


class PaddleOCRProvider(OfflineProvider):
    """Thin adapter for an installed PaddleOCR runtime.

    Construction is explicit so importing the backend never downloads models
    or imports Paddle.  The adapter accepts the common PaddleOCR result shape;
    unsupported versions fail with a clear model error for later pinning.
    """

    provider_name = "paddleocr"
    model_name = "PaddleOCR"
    version = "optional"
    dimension = 0
    preprocessing_contract = "paddleocr-input-contract-v1"

    def __init__(self, engine: Any, *, version: str = "optional") -> None:
        self._engine = engine
        self.version = version


    def health(self) -> ProviderHealth:
        return ProviderHealth(
            provider=self.provider_name,
            model=self.model_name,
            version=self.version,
            dimension=0,
            preprocessing_hash=self.preprocessing_hash,
            available=True,
            details="ready (optional PaddleOCR runtime)",
        )

    def recognize(self, image: str | Path | bytes) -> OCRResult:
        started = time.perf_counter_ns()
        try:
            result = self._engine.predict(str(image))
        except Exception as exc:  # Paddle versions expose heterogeneous runtime errors.
            raise DomainError("MODEL_UNAVAILABLE", "PaddleOCR 识别失败", 503) from exc
        lines = _normalize_paddle_result(result)
        text = "\n".join(line.text for line in lines)
        elapsed_ms = (time.perf_counter_ns() - started) / 1_000_000
        metadata = ProviderMetadata(
            provider=self.provider_name,
            model=self.model_name,
            version=self.version,
            dimension=0,
            preprocessing_hash=self.preprocessing_hash,
            latency_ms=elapsed_ms,
        )
        return OCRResult(raw_text=text, lines=tuple(lines), metadata=metadata)


def _normalize_paddle_result(result: Any) -> list[OCRLine]:
    """Normalize legacy and 3.x Paddle result objects into the pilot schema."""

    rows: list[Any] = []
    if isinstance(result, list):
        rows = result
    elif result is not None:
        rows = [result]
    lines: list[OCRLine] = []
    for order, item in enumerate(rows):
        if isinstance(item, dict):
            texts = item.get("rec_texts", [])
            scores = item.get("rec_scores", [])
            boxes = item.get("rec_boxes", [])
            for index, text in enumerate(texts):
                box = boxes[index] if index < len(boxes) else [0, 0, 0, 0]
                score = float(scores[index]) if index < len(scores) else 0.0
                lines.append(
                    OCRLine(
                        text=str(text),
                        bbox=_box_from_points(box),
                        confidence=max(0.0, min(1.0, score)),
                        order=order + index,
                    )
                )
            continue
        # Legacy PaddleOCR returns [[points, (text, score)], ...].
        if isinstance(item, list):
            for index, row in enumerate(item):
                if not isinstance(row, (list, tuple)) or len(row) < 2:
                    continue
                points, payload = row[0], row[1]
                if not isinstance(payload, (list, tuple)) or len(payload) < 2:
                    continue
                lines.append(
                    OCRLine(
                        text=str(payload[0]),
                        bbox=_box_from_points(points),
                        confidence=max(0.0, min(1.0, float(payload[1]))),
                        order=order + index,
                    )
                )
    return lines


def _box_from_points(points: Any) -> tuple[float, float, float, float]:
    if isinstance(points, (list, tuple)) and len(points) >= 4:
        try:
            xs = [float(point[0]) for point in points]
            ys = [float(point[1]) for point in points]
            return (min(xs), min(ys), max(xs), max(ys))
        except (TypeError, ValueError, IndexError):
            pass
    if isinstance(points, (list, tuple)) and len(points) == 4:
        try:
            return tuple(float(value) for value in points)  # type: ignore[return-value]
        except (TypeError, ValueError):
            pass
    return (0.0, 0.0, 0.0, 0.0)


def create_optional_ocr_provider() -> OCRProvider:
    """Return PaddleOCR when installed, otherwise an explicit unavailable provider."""

    try:
        from paddleocr import PaddleOCR  # type: ignore[import-not-found]
    except ImportError:
        return UnavailableOCRProvider()
    try:
        engine = PaddleOCR(use_doc_orientation_classify=False, use_doc_unwarping=False)
    except Exception:
        return UnavailableOCRProvider()
    return PaddleOCRProvider(engine)


__all__ = [
    "OCRLine",
    "OCRProvider",
    "OCRResult",
    "PaddleOCRProvider",
    "UnavailableOCRProvider",
    "create_optional_ocr_provider",
]
