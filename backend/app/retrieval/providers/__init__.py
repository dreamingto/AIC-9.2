"""Offline, deterministic model providers used by the V1 backend.

Imports are lazy on purpose.  The text embedding provider reuses the Chinese
tokenizer from :mod:`app.retrieval.baseline.bm25`; eager package-level imports
would otherwise create a circular import while that module is initialized.
"""

from importlib import import_module
from typing import Any

__all__ = [
    "DeterministicImageEmbeddingProvider",
    "DeterministicTextEmbeddingProvider",
    "MockProvider",
    "OfflineProvider",
    "ProviderHealth",
    "ProviderMetadata",
    "VectorResult",
    "l2_normalize",
]

_EXPORTS = {
    "OfflineProvider": (".base", "OfflineProvider"),
    "ProviderHealth": (".base", "ProviderHealth"),
    "ProviderMetadata": (".base", "ProviderMetadata"),
    "VectorResult": (".base", "VectorResult"),
    "l2_normalize": (".base", "l2_normalize"),
    "DeterministicImageEmbeddingProvider": (
        ".image_embedding",
        "DeterministicImageEmbeddingProvider",
    ),
    "DeterministicTextEmbeddingProvider": (
        ".text_embedding",
        "DeterministicTextEmbeddingProvider",
    ),
    "MockProvider": (".mock", "MockProvider"),
}


def __getattr__(name: str) -> Any:
    try:
        module_name, attribute_name = _EXPORTS[name]
    except KeyError as error:
        raise AttributeError(name) from error
    return getattr(import_module(module_name, __name__), attribute_name)
