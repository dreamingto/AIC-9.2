"""High-confidence fixture relations and weighted graph Jaccard."""

from __future__ import annotations

import builtins
import math
import time
import unicodedata
from collections.abc import Iterable, Mapping
from dataclasses import dataclass

from app.retrieval.providers.base import OfflineProvider, ProviderMetadata


def _normalized_label(value: str) -> str:
    return unicodedata.normalize("NFKC", value).strip().casefold()


@dataclass(frozen=True, slots=True)
class FunctionalRelation:
    subject: str
    predicate: str
    object: str
    confidence: float

    @property
    def key(self) -> tuple[str, str, str]:
        return (
            _normalized_label(self.subject),
            _normalized_label(self.predicate),
            _normalized_label(self.object),
        )

    @classmethod
    def from_mapping(cls, value: Mapping[str, builtins.object]) -> FunctionalRelation:
        # Fixture manifests historically called the edge strength ``weight``;
        # accept it as a confidence fallback while preferring the explicit
        # confidence field when both are present.
        raw_confidence = value.get("confidence", value.get("weight", 1.0))
        confidence = float(raw_confidence) if isinstance(raw_confidence, int | float | str) else 1.0
        return cls(
            subject=str(value["subject"]),
            predicate=str(value["predicate"]),
            object=str(value["object"]),
            confidence=confidence,
        )


@dataclass(frozen=True, slots=True)
class GraphResult:
    relations: tuple[FunctionalRelation, ...]
    metadata: ProviderMetadata


@dataclass(frozen=True, slots=True)
class GraphSimilarityResult:
    score: float
    query_edges: int
    candidate_edges: int
    matched_edges: int
    metadata: ProviderMetadata


RelationInput = FunctionalRelation | Mapping[str, object]


def _relation_weights(
    relations: Iterable[RelationInput], *, min_confidence: float
) -> dict[tuple[str, str, str], float]:
    weights: dict[tuple[str, str, str], float] = {}
    for raw_relation in relations:
        relation = (
            raw_relation
            if isinstance(raw_relation, FunctionalRelation)
            else FunctionalRelation.from_mapping(raw_relation)
        )
        confidence = relation.confidence
        if not math.isfinite(confidence) or confidence < min_confidence:
            continue
        confidence = min(1.0, max(0.0, confidence))
        weights[relation.key] = max(weights.get(relation.key, 0.0), confidence)
    return weights


def weighted_graph_jaccard(
    query: Iterable[RelationInput],
    candidate: Iterable[RelationInput],
    *,
    min_confidence: float = 0.7,
) -> float:
    if not 0.0 <= min_confidence <= 1.0:
        raise ValueError("min_confidence must be between zero and one")
    # Materialize once: callers often pass generators from ORM relationships.
    # Without this, the first weight pass would exhaust the iterable and the
    # second pass would silently produce a zero score.
    query_items = tuple(query)
    candidate_items = tuple(candidate)
    query_weights = _relation_weights(query_items, min_confidence=min_confidence)
    candidate_weights = _relation_weights(candidate_items, min_confidence=min_confidence)
    union = query_weights.keys() | candidate_weights.keys()
    if not union:
        return 0.0
    numerator = sum(
        min(query_weights.get(edge, 0.0), candidate_weights.get(edge, 0.0)) for edge in union
    )
    denominator = sum(
        max(query_weights.get(edge, 0.0), candidate_weights.get(edge, 0.0)) for edge in union
    )
    return numerator / denominator if denominator else 0.0


class FixtureRelationProvider(OfflineProvider):
    provider_name = "fixture_relation"
    model_name = "annotated-triples"
    version = "1.0.0"
    preprocessing_contract = "nfkc-casefold-triples+confidence-threshold-v1"

    def __init__(self, *, min_confidence: float = 0.7) -> None:
        if not 0.0 <= min_confidence <= 1.0:
            raise ValueError("min_confidence must be between zero and one")
        self.min_confidence = min_confidence

    def represent(self, relations: Iterable[RelationInput]) -> GraphResult:
        started = time.perf_counter_ns()
        weights = _relation_weights(relations, min_confidence=self.min_confidence)
        normalized = tuple(
            FunctionalRelation(*edge, confidence=confidence)
            for edge, confidence in sorted(weights.items())
        )
        elapsed_ms = (time.perf_counter_ns() - started) / 1_000_000
        return GraphResult(
            relations=normalized,
            metadata=self.metadata(elapsed_ms, dimension=len(normalized)),
        )

    def similarity(
        self,
        query: Iterable[RelationInput],
        candidate: Iterable[RelationInput],
    ) -> GraphSimilarityResult:
        started = time.perf_counter_ns()
        query_items = tuple(query)
        candidate_items = tuple(candidate)
        query_weights = _relation_weights(query_items, min_confidence=self.min_confidence)
        candidate_weights = _relation_weights(candidate_items, min_confidence=self.min_confidence)
        score = weighted_graph_jaccard(
            query_items,
            candidate_items,
            min_confidence=self.min_confidence,
        )
        matched = len(query_weights.keys() & candidate_weights.keys())
        elapsed_ms = (time.perf_counter_ns() - started) / 1_000_000
        return GraphSimilarityResult(
            score=score,
            query_edges=len(query_weights),
            candidate_edges=len(candidate_weights),
            matched_edges=matched,
            metadata=self.metadata(
                elapsed_ms, dimension=len(query_weights.keys() | candidate_weights.keys())
            ),
        )
