"""Dependency-free baseline retrieval implementations."""

from importlib import import_module
from typing import Any

__all__ = ["BM25Hit", "BM25SearchResult", "BM25TextProvider", "tokenize_zh"]


def __getattr__(name: str) -> Any:
    if name not in __all__:
        raise AttributeError(name)
    return getattr(import_module(".bm25", __name__), name)
