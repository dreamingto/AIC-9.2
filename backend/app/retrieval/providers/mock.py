"""Explicit test double for services that consume vector providers."""

from __future__ import annotations

from app.retrieval.providers.base import OfflineProvider, ProviderHealth, VectorResult


class MockProvider(OfflineProvider):
    provider_name = "mock"
    model_name = "fixed-vector"
    preprocessing_contract = "fixed-vector-test-double-v1"

    def __init__(self, vector: tuple[float, ...], *, available: bool = True) -> None:
        self._vector = vector
        self.dimension = len(vector)
        self._available = available

    def encode(self, _value: object) -> VectorResult:
        if not self._available:
            raise RuntimeError("mock provider is unavailable")
        return VectorResult(vector=self._vector, metadata=self.metadata(0.0))

    def health(self) -> ProviderHealth:
        health = super().health()
        if self._available:
            return health
        return ProviderHealth(
            provider=health.provider,
            model=health.model,
            version=health.version,
            dimension=health.dimension,
            preprocessing_hash=health.preprocessing_hash,
            available=False,
            details="unavailable (configured test double)",
        )
