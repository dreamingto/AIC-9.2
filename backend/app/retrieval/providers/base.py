"""Shared contracts for deterministic, offline retrieval providers."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import asdict, dataclass
from hashlib import sha256
from math import sqrt


@dataclass(frozen=True, slots=True)
class ProviderMetadata:
    provider: str
    model: str
    version: str
    dimension: int
    preprocessing_hash: str
    latency_ms: float

    def as_dict(self) -> dict[str, str | int | float]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class ProviderHealth:
    provider: str
    model: str
    version: str
    dimension: int
    preprocessing_hash: str
    available: bool
    details: str

    def as_dict(self) -> dict[str, str | int | bool]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class VectorResult:
    vector: tuple[float, ...]
    metadata: ProviderMetadata


class OfflineProvider:
    """Small common surface used by the capability endpoint and search services."""

    provider_name = "offline"
    model_name = "unspecified"
    version = "1.0.0"
    dimension = 0
    preprocessing_contract = "identity-v1"

    @property
    def preprocessing_hash(self) -> str:
        return sha256(self.preprocessing_contract.encode("utf-8")).hexdigest()

    def metadata(
        self, latency_ms: float = 0.0, *, dimension: int | None = None
    ) -> ProviderMetadata:
        return ProviderMetadata(
            provider=self.provider_name,
            model=self.model_name,
            version=self.version,
            dimension=self.dimension if dimension is None else dimension,
            preprocessing_hash=self.preprocessing_hash,
            latency_ms=max(0.0, latency_ms),
        )

    # ``get_metadata``/``status`` are intentionally tiny aliases. Keeping the
    # aliases here lets API and ingestion code consume providers without
    # coupling to a particular implementation's naming convention.
    def get_metadata(self, latency_ms: float = 0.0) -> ProviderMetadata:
        return self.metadata(latency_ms)

    def health(self) -> ProviderHealth:
        return ProviderHealth(
            provider=self.provider_name,
            model=self.model_name,
            version=self.version,
            dimension=self.dimension,
            preprocessing_hash=self.preprocessing_hash,
            available=True,
            details="ready (offline)",
        )

    def status(self) -> ProviderHealth:
        return self.health()


def l2_normalize(values: Iterable[float]) -> tuple[float, ...]:
    vector = tuple(float(value) for value in values)
    norm = sqrt(sum(value * value for value in vector))
    if norm == 0.0:
        return tuple(0.0 for _ in vector)
    return tuple(value / norm for value in vector)
