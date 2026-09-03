"""Functional relation graph utilities."""

from importlib import import_module
from typing import Any

__all__ = [
    "FixtureRelationProvider",
    "FunctionalRelation",
    "GraphResult",
    "GraphSimilarityResult",
    "weighted_graph_jaccard",
]


def __getattr__(name: str) -> Any:
    if name not in __all__:
        raise AttributeError(name)
    return getattr(import_module(".weighted", __name__), name)
