from __future__ import annotations

import math

import pytest
from PIL import Image, ImageDraw

from app.retrieval.baseline.bm25 import BM25TextProvider, tokenize_zh
from app.retrieval.cfr.rule_based import RuleBasedCFRProvider
from app.retrieval.graph.weighted import (
    FixtureRelationProvider,
    FunctionalRelation,
    weighted_graph_jaccard,
)
from app.retrieval.providers.image_embedding import (
    DeterministicImageEmbeddingProvider,
)
from app.retrieval.providers.mock import MockProvider
from app.retrieval.providers.registry import ProviderRegistry
from app.retrieval.providers.text_embedding import (
    DeterministicTextEmbeddingProvider,
)


def test_chinese_tokenizer_includes_unigrams_bigrams_and_latin_words() -> None:
    tokens = tokenize_zh("水轮提水 Gear-Drive")

    assert "水" in tokens
    assert "水轮" in tokens
    assert "轮提" in tokens
    assert "gear-drive" in tokens


def test_bm25_prefers_matching_chinese_mechanism() -> None:
    provider = BM25TextProvider(
        {
            "water_lift": "水轮转动，通过轮轴连续提水灌溉。",
            "loom": "脚踏织机使用梭子织布。",
            "mill": "畜力推动石磨碾磨谷物。",
        }
    )

    result = provider.search("水轮提水", top_k=2)

    assert result.hits[0].document_id == "water_lift"
    assert result.hits[0].score > 0
    assert result.metadata.provider == "bm25_text"
    assert result.metadata.dimension > 0


def test_bm25_has_stable_tie_order_and_rejects_bad_top_k() -> None:
    provider = BM25TextProvider({"b": "轮轴", "a": "轮轴"})

    assert [hit.document_id for hit in provider.search("轮轴").hits] == ["a", "b"]
    with pytest.raises(ValueError):
        provider.search("轮轴", top_k=0)


def test_text_embedding_is_deterministic_normalized_and_256_dimensional() -> None:
    provider = DeterministicTextEmbeddingProvider()

    first = provider.encode("水轮通过轮轴提水")
    second = provider.encode("水轮通过轮轴提水")
    other = provider.encode("脚踏织机纺纱")

    assert first.vector == second.vector
    assert len(first.vector) == 256
    assert math.isclose(sum(value * value for value in first.vector), 1.0)
    assert first.vector != other.vector
    assert first.metadata.preprocessing_hash == second.metadata.preprocessing_hash
    assert set(first.metadata.as_dict()) == {
        "provider",
        "model",
        "version",
        "dimension",
        "preprocessing_hash",
        "latency_ms",
    }


def test_empty_text_embedding_is_a_finite_zero_vector() -> None:
    result = DeterministicTextEmbeddingProvider().encode(" ")

    assert result.vector == (0.0,) * 256
    assert all(math.isfinite(value) for value in result.vector)


def _mechanism_image(diagonal: bool) -> Image.Image:
    image = Image.new("RGB", (64, 64), "white")
    draw = ImageDraw.Draw(image)
    draw.ellipse((12, 12, 52, 52), outline="black", width=4)
    if diagonal:
        draw.line((16, 48, 48, 16), fill="black", width=4)
    else:
        draw.line((12, 32, 52, 32), fill="black", width=4)
    return image


def test_image_embedding_is_deterministic_normalized_and_distinguishes_shapes() -> None:
    provider = DeterministicImageEmbeddingProvider()
    horizontal = _mechanism_image(diagonal=False)
    diagonal = _mechanism_image(diagonal=True)

    first = provider.encode(horizontal)
    second = provider.encode(horizontal)
    other = provider.encode(diagonal)

    assert first.vector == second.vector
    assert len(first.vector) == 256
    assert math.isclose(sum(value * value for value in first.vector), 1.0)
    assert first.vector != other.vector
    assert first.metadata.provider == "deterministic_image_embedding"


def test_rule_based_cfr_is_multi_label_and_uses_unknown_per_empty_slot() -> None:
    result = RuleBasedCFRProvider().extract("人力脚踏与水轮共同驱动轮轴转动，用于提水灌溉。")

    power = {concept.concept for concept in result.slots["power_source"]}
    assert power == {"human_power", "water_power"}
    assert {concept.concept for concept in result.slots["motion"]} == {"rotary"}
    assert {concept.concept for concept in result.slots["transmission"]} == {"shaft"}
    assert "water" in {concept.concept for concept in result.slots["object"]}
    assert not result.is_unknown


def test_rule_based_cfr_returns_all_unknown_for_unmatched_text() -> None:
    result = RuleBasedCFRProvider().extract("图中器物名称已佚。")

    assert result.is_unknown
    assert all(
        concepts == (concepts[0],)
        and concepts[0].concept == "unknown"
        and concepts[0].confidence == 0.0
        for concepts in result.slots.values()
    )


def test_weighted_graph_jaccard_uses_confidence_and_ignores_low_confidence() -> None:
    shared_query = FunctionalRelation("水轮", "驱动", "轮轴", 0.9)
    shared_candidate = FunctionalRelation("水轮", "驱动", "轮轴", 0.8)
    query_only = FunctionalRelation("轮轴", "带动", "水斗", 1.0)
    ignored = FunctionalRelation("传说", "关联", "水斗", 0.2)

    score = weighted_graph_jaccard(
        [shared_query, query_only],
        [shared_candidate, ignored],
        min_confidence=0.7,
    )

    assert score == pytest.approx(0.8 / (0.9 + 1.0))
    assert weighted_graph_jaccard([], []) == 0.0


def test_fixture_relation_provider_normalizes_deduplicates_and_reports_matches() -> None:
    provider = FixtureRelationProvider(min_confidence=0.7)
    query = [
        {"subject": " 水轮 ", "predicate": "驱动", "object": "轮轴", "confidence": 0.8},
        {"subject": "水轮", "predicate": "驱动", "object": "轮轴", "confidence": 0.9},
    ]
    candidate = [FunctionalRelation("水轮", "驱动", "轮轴", 1.0)]

    representation = provider.represent(query)
    similarity = provider.similarity(query, candidate)

    assert len(representation.relations) == 1
    assert representation.relations[0].confidence == 0.9
    assert similarity.score == pytest.approx(0.9)
    assert similarity.matched_edges == 1
    assert similarity.metadata.dimension == 1


def test_provider_health_and_mock_unavailable_state() -> None:
    text_health = DeterministicTextEmbeddingProvider().health()
    unavailable = MockProvider((1.0, 0.0), available=False)

    assert text_health.available
    assert text_health.dimension == 256
    assert len(text_health.preprocessing_hash) == 64
    assert not unavailable.health().available
    with pytest.raises(RuntimeError):
        unavailable.encode("anything")


def test_provider_registry_exposes_all_offline_capabilities() -> None:
    registry = ProviderRegistry.create()

    health = registry.health()

    assert [item.provider for item in health] == [
        "deterministic_text_embedding",
        "deterministic_image_embedding",
        "rule_based_cfr",
        "fixture_relation",
        "bm25_text",
    ]
    assert all(item.available for item in health)
    assert len(registry.all_offline()) == 5
