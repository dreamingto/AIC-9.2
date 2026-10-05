"""Optional OCR contracts for the V1.1-B real-book pilot.

The production dependency is intentionally optional.  A missing PaddleOCR
installation must be visible as unavailable rather than silently falling back
to the synthetic fixture text or an untracked OCR result.
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from io import BytesIO
from pathlib import Path
from typing import Any, Protocol

from PIL import Image

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
    model_name = "PP-OCRv5_mobile"
    version = "optional"
    dimension = 0
    preprocessing_contract = "paddleocr-input-contract-v1"

    def __init__(
        self,
        engine: Any,
        *,
        version: str = "optional",
        model_name: str = "PP-OCRv5_mobile",
    ) -> None:
        self._engine = engine
        self.version = version
        self.model_name = model_name


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
            result = self._engine.predict(_paddle_input(image))
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


def _paddle_input(image: str | Path | bytes) -> Any:
    """Load local images through Pillow to avoid OpenCV Unicode-path failures."""

    if isinstance(image, bytes):
        source: Any = BytesIO(image)
    else:
        source = str(image)
    with Image.open(source) as opened:
        rgb = opened.convert("RGB")
        try:
            import numpy as np  # type: ignore[import-not-found]
        except ImportError as exc:
            raise RuntimeError("PaddleOCR requires numpy for local image input") from exc
        return np.asarray(rgb)


def _normalize_paddle_result(result: Any) -> list[OCRLine]:
    """Normalize legacy and 3.x Paddle result objects into the pilot schema."""

    rows: list[Any] = []
    if isinstance(result, list):
        rows = result
    elif result is not None:
        rows = [result]
    lines: list[OCRLine] = []
    for order, item in enumerate(rows):
        item = _result_payload(item)
        if isinstance(item, dict):
            if isinstance(item.get("res"), dict):
                item = item["res"]
            texts = item.get("rec_texts", [])
            scores = item.get("rec_scores", [])
            boxes = item.get("rec_boxes", [])
            for index, text in enumerate(texts):
                normalized_text = str(text)
                if not normalized_text.strip():
                    continue
                box = boxes[index] if index < len(boxes) else [0, 0, 0, 0]
                score = float(scores[index]) if index < len(scores) else 0.0
                lines.append(
                    OCRLine(
                        text=normalized_text,
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
                normalized_text = str(payload[0])
                if not normalized_text.strip():
                    continue
                lines.append(
                    OCRLine(
                        text=normalized_text,
                        bbox=_box_from_points(points),
                        confidence=max(0.0, min(1.0, float(payload[1]))),
                        order=order + index,
                    )
                )
    return lines


def _result_payload(item: Any) -> Any:
    """Convert PaddleX BaseCVResult objects and array values to plain Python."""

    payload = getattr(item, "json", None)
    if payload is not None:
        try:
            payload = payload() if callable(payload) else payload
        except Exception:
            payload = None
        if payload is not None:
            item = payload
    tolist = getattr(item, "tolist", None)
    if callable(tolist):
        try:
            return tolist()
        except (TypeError, ValueError):
            return item
    return item


def _box_from_points(points: Any) -> tuple[float, float, float, float]:
    points = _result_payload(points)
    if isinstance(points, (list, tuple)) and len(points) >= 4:
        try:
            points = [_result_payload(point) for point in points]
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
        import paddleocr  # type: ignore[import-not-found]
    except ImportError:
        return UnavailableOCRProvider()
    try:
        engine = paddleocr.PaddleOCR(
            text_detection_model_name="PP-OCRv5_mobile_det",
            text_recognition_model_name="PP-OCRv5_mobile_rec",
            use_doc_orientation_classify=False,
            use_doc_unwarping=False,
            use_textline_orientation=False,
            device="cpu",
        )
    except Exception:
        return UnavailableOCRProvider()
    return PaddleOCRProvider(engine, version=str(getattr(paddleocr, "__version__", "unknown")))


__all__ = [
    "OCRLine",
    "OCRProvider",
    "OCRResult",
    "PaddleOCRProvider",
    "UnavailableOCRProvider",
    "create_optional_ocr_provider",
]
