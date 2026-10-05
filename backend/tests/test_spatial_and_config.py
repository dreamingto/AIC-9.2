from __future__ import annotations

import json
from uuid import uuid4

import pytest
from pydantic import ValidationError

from app.core.config import Settings
from app.db.models import Figure, FunctionalAssertion, Relation, TextChunk
from app.retrieval.evidence.spatial import contained, scoped_region_context
from app.services.search_service import SearchService


def source() -> Figure:
    left = {"x": 0.05, "y": 0.1, "width": 0.3, "height": 0.5}
    whole = {"x": 0, "y": 0, "width": 1, "height": 1}
    figure = Figure(
        id=uuid4(), page_id=uuid4(), title="水力舂捣 谷物加工",
        bbox_x=0, bbox_y=0, bbox_width=1, bbox_height=1,
        provenance={"ai_review": {"text_traces": [
            {"text_id": "left", "bbox": left}, {"text_id": "whole", "bbox": whole},
        ]}},
        text_chunks=[
            TextChunk(text="水轮", source_pointer="left"),
            TextChunk(text="谷物加工", source_pointer="whole"),
            TextChunk(text="无定位加工", source_pointer="legacy"),
        ],
        assertions=[
            FunctionalAssertion(slot="power_source", concept="water", confidence=.8,
                                state="Inferred", evidence_pointer=json.dumps({"bbox": left})),
            FunctionalAssertion(slot="action", concept="pounding", confidence=.8,
                                state="Inferred", evidence_pointer=json.dumps({"bbox": whole})),
        ],
        relations=[Relation(subject="水轮", predicate="驱动", object="杵", confidence=.9)],
    )
    return figure


def test_local_crop_excludes_whole_figure_claims_and_unlocated_context() -> None:
    text, assertions, relations = scoped_region_context(
        source(), {"x": 0, "y": 0, "width": .5, "height": 1},
    )
    assert text == "水轮"
    assert [a["concept"] for a in assertions] == ["water"]
    assert relations == []
    claims = SearchService._claims_from_text(text, assertions)
    assert "pounding" not in claims and "谷物" not in claims


def test_whole_figure_keeps_located_support_but_not_unlocated_text() -> None:
    text, assertions, relations = scoped_region_context(
        source(), {"x": 0, "y": 0, "width": 1, "height": 1},
    )
    assert text == "水轮 谷物加工"
    assert len(assertions) == 2 and len(relations) == 1


def test_foreign_page_and_cross_crop_supports_are_rejected() -> None:
    figure = source()
    figure.text_chunks[0].source_pointer = json.dumps({
        "bbox": {"x": 0, "y": 0, "width": .1, "height": .1}, "page_id": str(uuid4()),
    })
    figure.assertions[0].evidence_pointer = json.dumps({"supports": [
        {"bbox": {"x": 0, "y": 0, "width": .1, "height": .1}},
        {"bbox": {"x": .8, "y": 0, "width": .1, "height": .1}},
    ]})
    text, assertions, _ = scoped_region_context(
        figure, {"x": 0, "y": 0, "width": .5, "height": 1},
    )
    assert text == "" and assertions == []


def test_invalid_extent_does_not_establish_a_location() -> None:
    assert not contained({"x": float("nan")}, {"x": 0, "y": 0, "width": 1, "height": 1})


def test_environment_weights_reach_search_and_keep_explicit_policy(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("EAFR_WEIGHTS", '{"beta_v":0.4,"lambda_e":0.03}')
    service = SearchService(Settings(_env_file=None))
    assert service.weights.beta_v == .4 and service.weights.lambda_e == .03
    assert service.weights.beta_t == .25


@pytest.mark.parametrize("weights", [{"beta_v": -1}, {"lambda_e": float("nan")}, {"typo": .1}])
def test_invalid_weight_configuration_fails_at_startup(weights: dict[str, float]) -> None:
    with pytest.raises(ValidationError):
        Settings(_env_file=None, eafr_weights=weights)
