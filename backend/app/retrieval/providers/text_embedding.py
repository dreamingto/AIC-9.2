"""Deterministic text embeddings for offline development and tests."""

from __future__ import annotations

import hashlib
import math
import time
from collections import Counter

from app.retrieval.baseline.bm25 import tokenize_zh
from app.retrieval.providers.base import OfflineProvider, VectorResult, l2_normalize


class DeterministicTextEmbeddingProvider(OfflineProvider):
    provider_name = "deterministic_text_embedding"
    model_name = "signed-feature-hashing-256"
    version = "1.0.0"
    dimension = 256
    preprocessing_contract = "bm25-zh-tokenizer+blake2b-signed-hashing+l2-v1"

    def encode(self, text: str) -> VectorResult:
        started = time.perf_counter_ns()
        values = [0.0] * self.dimension
        for token, count in Counter(tokenize_zh(text)).items():
            digest = hashlib.blake2b(token.encode("utf-8"), digest_size=16).digest()
            index = int.from_bytes(digest[:8], "big") % self.dimension
            sign = 1.0 if digest[8] & 1 else -1.0
            values[index] += sign * (1.0 + math.log(count))
        vector = l2_normalize(values)
        elapsed_ms = (time.perf_counter_ns() - started) / 1_000_000
        return VectorResult(vector=vector, metadata=self.metadata(elapsed_ms))

    def encode_many(self, texts: list[str] | tuple[str, ...]) -> tuple[VectorResult, ...]:
        return tuple(self.encode(text) for text in texts)

    def encode_query(self, text: str) -> VectorResult:
        return self.encode(text)
