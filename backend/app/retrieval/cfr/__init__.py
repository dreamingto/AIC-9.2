"""Contextual Functional Representation providers."""

from importlib import import_module
from typing import Any

__all__ = ["CFRConcept", "CFRResult", "RuleBasedCFRProvider"]


def __getattr__(name: str) -> Any:
    if name not in __all__:
        raise AttributeError(name)
    return getattr(import_module(".rule_based", __name__), name)
