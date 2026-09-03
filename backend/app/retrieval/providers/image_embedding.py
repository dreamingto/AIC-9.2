"""Pillow-only deterministic image features for the offline baseline."""

from __future__ import annotations

import hashlib
import io
import time
from functools import lru_cache
from pathlib import Path
from typing import BinaryIO

from PIL import Image, ImageOps

from app.retrieval.providers.base import OfflineProvider, VectorResult, l2_normalize

ImageSource = Image.Image | bytes | bytearray | BinaryIO | str | Path


@lru_cache(maxsize=1024)
def _projection_targets(feature_index: int) -> tuple[tuple[int, float], ...]:
    digest = hashlib.blake2b(
        f"deterministic-image-v1:{feature_index}".encode("ascii"), digest_size=16
    ).digest()
    targets: list[tuple[int, float]] = []
    for offset in range(0, 16, 4):
        index = int.from_bytes(digest[offset : offset + 2], "big") % 256
        sign = 1.0 if digest[offset + 2] & 1 else -1.0
        targets.append((index, sign))
    return tuple(targets)


def _open_image(source: ImageSource) -> Image.Image:
    if isinstance(source, Image.Image):
        opened = source.copy()
    elif isinstance(source, bytes | bytearray):
        with Image.open(io.BytesIO(bytes(source))) as image:
            image.load()
            opened = image.copy()
    else:
        with Image.open(source) as image:
            image.load()
            opened = image.copy()
    transposed = ImageOps.exif_transpose(opened)
    if transposed is not opened:
        opened.close()
    rgb = transposed.convert("RGB")
    if rgb is not transposed:
        transposed.close()
    return rgb


def _source_features(image: Image.Image) -> list[float]:
    resized = image.resize((16, 16), Image.Resampling.LANCZOS)
    grayscale = resized.convert("L")
    pixels = list(grayscale.getdata())
    features = [pixel / 255.0 for pixel in pixels]

    gray_histogram = grayscale.histogram()
    for start in range(0, 256, 16):
        features.append(sum(gray_histogram[start : start + 16]) / 256.0)

    for channel in resized.split():
        histogram = channel.histogram()
        for start in range(0, 256, 32):
            features.append(sum(histogram[start : start + 32]) / 256.0)

    horizontal = [0.0] * 8
    vertical = [0.0] * 8
    for y in range(16):
        for x in range(16):
            current = pixels[y * 16 + x]
            if x < 15:
                magnitude = abs(current - pixels[y * 16 + x + 1])
                horizontal[min(7, magnitude // 32)] += 1.0 / 240.0
            if y < 15:
                magnitude = abs(current - pixels[(y + 1) * 16 + x])
                vertical[min(7, magnitude // 32)] += 1.0 / 240.0
    features.extend(horizontal)
    features.extend(vertical)
    return features


class DeterministicImageEmbeddingProvider(OfflineProvider):
    provider_name = "deterministic_image_embedding"
    model_name = "pillow-handcrafted-projection-256"
    version = "1.0.0"
    dimension = 256
    preprocessing_contract = (
        "exif-transpose+rgb+16x16-lanczos+gray-rgb-hist+gradient+blake2b-fixed-projection+l2-v1"
    )

    def encode(self, source: ImageSource) -> VectorResult:
        started = time.perf_counter_ns()
        image = _open_image(source)
        try:
            source_features = _source_features(image)
        finally:
            image.close()

        values = [0.0] * self.dimension
        for feature_index, feature in enumerate(source_features):
            if feature == 0.0:
                continue
            for target, sign in _projection_targets(feature_index):
                values[target] += sign * feature
        vector = l2_normalize(values)
        elapsed_ms = (time.perf_counter_ns() - started) / 1_000_000
        return VectorResult(vector=vector, metadata=self.metadata(elapsed_ms))
