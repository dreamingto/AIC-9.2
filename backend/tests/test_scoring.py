"""Unit tests for the dependency-free EAFR scoring primitives."""

from __future__ import annotations

import json
import math

import pytest

from app.retrieval.rerank.scoring import (
    EAFRWeights,
    EvidenceItem,
    clip,
    cosine_similarity,
    cosine_to_unit,
    evidence_coverage,
    model_uncertainty,
    normalize_score,
    normalized_entropy,
    score_candidate,
)


def test_cosine_similarity_handles_regular_and_degenerate_vectors() -> None:
    assert cosine_similarity([1, 0], [1, 0]) == pytest.approx(1.0)
    assert cosine_similarity([1, 0], [0, 1]) == pytest.approx(0.0)
    assert cosine_similarity([1, 0], [-1, 0]) == pytest.approx(-1.0)
    assert cosine_similarity([], []) == 0.0
    assert cosine_similarity([0, 0], [1, 2]) == 0.0
    assert cosine_similarity([1], [1, 2]) == 0.0


def test_cosine_similarity_is_stable_for_large_values_and_bad_inputs() -> None:
    value = cosine_similarity([1e308, 1e308], [1e308, -1e308])
    assert math.isfinite(value)
    assert value == pytest.approx(0.0)
    assert cosine_similarity([float("nan")], [1.0]) == 0.0


def test_calibration_clips_and_maps_ranges() -> None:
    assert clip(-1) == 0.0
    assert clip(2) == 1.0
    assert normalize_score(-1, -1, 1) == 0.0
    assert normalize_score(0, -1, 1) == 0.5
    assert normalize_score(1, -1, 1) == 1.0
    assert normalize_score(7, 3, 3) == 0.5
    assert cosine_to_unit(-1) == 0.0
    assert cosine_to_unit(1) == 1.0


def test_evidence_coverage_is_query_candidate_specific_and_quality_aware() -> None:
    query = ["轮轴", "传动"]
    exact = [
        EvidenceItem(status="Verified", supports=("轮轴",)),
        {"status": "Documented", "claim_id": "传动"},
    ]
    assert evidence_coverage(query, exact) == pytest.approx((1.0 + 0.9) / 2)

    lexical = [{"status": "Observed", "text": "图中可见轮轴结构"}]
    assert 0.0 < evidence_coverage(["轮轴"], lexical) <= 0.8
    # Long unrelated text cannot increase coverage when the query claim is not
    # supported; this guards against document-length bias.
    assert evidence_coverage(["水车"], [{"text": "无关" * 1000}]) == 0.0
    assert evidence_coverage([], exact) == 0.0


def test_entropy_and_model_uncertainty_are_bounded() -> None:
    assert normalized_entropy([1]) == 0.0
    assert normalized_entropy([1, 1]) == pytest.approx(1.0)
    assert normalized_entropy([1, 0]) == pytest.approx(0.0)
    assert normalized_entropy([0, 0]) == pytest.approx(1.0)
    assert model_uncertainty(component_scores=[0.5]) == 0.0
    assert 0.0 < model_uncertainty(component_scores=[0.0, 1.0]) <= 1.0


def test_missing_modality_does_not_renormalize_or_boost_score() -> None:
    weights = EAFRWeights(beta_v=0.5, beta_t=0.5, lambda_e=0.0, lambda_u=0.0)
    complete = score_candidate({"visual": 1.0, "text": 1.0}, weights=weights)
    visual_only = score_candidate({"visual": 1.0, "text": None}, weights=weights)
    assert complete.score == pytest.approx(1.0)
    assert visual_only.score == pytest.approx(0.5)
    assert "text" in visual_only.components.missing_modalities
    assert visual_only.components.reliability["text"] == 0.0


def test_eafr_formula_and_component_serialization() -> None:
    weights = EAFRWeights(
        beta_v=0.2,
        beta_t=0.2,
        beta_r=0.1,
        beta_f=0.2,
        beta_g=0.1,
        lambda_e=0.1,
        lambda_u=0.1,
    )
    result = score_candidate(
        {"sv": 0.8, "st": 0.6, "sr": 0.4, "sf": 0.9, "sg": 0.5},
        evidence_score=0.7,
        model_uncertainty_score=0.2,
        weights=weights,
    )
    expected = 0.2 * 0.8 + 0.2 * 0.6 + 0.1 * 0.4 + 0.2 * 0.9 + 0.1 * 0.5 + 0.1 * 0.7 - 0.1 * 0.2
    assert result.score == pytest.approx(expected)
    payload = result.to_dict()
    # Every field is JSON serializable and symbolic equation keys are present.
    json.dumps(payload, ensure_ascii=False)
    for key in ("sv", "st", "sr", "sf", "sg", "se", "u_model", "contributions"):
        assert key in result.score_components


def test_reliability_and_availability_are_explicit() -> None:
    result = score_candidate(
        {"visual": 0.9, "text": 0.9},
        modality_reliability={"visual": 0.5, "text": 1.0},
        availability={"text": False},
        evidence_score=0.0,
    )
    assert result.components.reliability["visual"] == pytest.approx(0.5)
    assert result.components.reliability["text"] == 0.0
    assert "text" in result.components.missing_modalities
