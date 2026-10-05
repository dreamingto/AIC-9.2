from __future__ import annotations

import math
from typing import Any
from uuid import uuid4

import pytest

from app.core.config import Settings
from app.core.errors import DomainError
from app.db.models import EmbeddingRecord, Figure
from app.retrieval.providers.neural import NeuralTextEmbeddingProvider
from app.retrieval.providers.registry import ProviderRegistry
from app.services.ingestion_service import _upsert_embedding
from app.services.search_service import SearchService


def provider() -> NeuralTextEmbeddingProvider:
    return NeuralTextEmbeddingProvider("text", "http://127.0.0.1:8767")


def test_real_model_identity_and_query_instruction_role(monkeypatch: pytest.MonkeyPatch) -> None:
    instance = provider()
    payloads = []

    def response(route: str, payload: Any = None) -> dict[str, Any]:
        payloads.append(payload)
        return {"vector": [1.0] + [0.0] * 511, "metadata": instance.metadata().as_dict()}

    monkeypatch.setattr(instance, "_request", response)
    assert len(instance.encode("织机").vector) == 512
    assert instance.encode_query("织机").vector == instance.encode("织机").vector
    assert [p["query"] for p in payloads] == [False, True, False]
    assert all(p["modality"] == "text" for p in payloads)


@pytest.mark.parametrize("invalid", ["dimension", "nan", "norm", "version", "preprocessing"])
def test_reject_wrong_space_or_invalid_neural_response(
    monkeypatch: pytest.MonkeyPatch,
    invalid: str,
) -> None:
    instance = provider()
    response = {"vector": [1.0] + [0.0] * 511, "metadata": instance.metadata().as_dict()}
    if invalid == "dimension":
        response["vector"] = [1.0]
    elif invalid == "nan":
        response["vector"][0] = math.nan
    elif invalid == "norm":
        response["vector"][0] = 2.0
    elif invalid == "version":
        response["metadata"]["version"] = "another-checkpoint"
    else:
        response["metadata"]["preprocessing_hash"] = "0" * 64
    monkeypatch.setattr(instance, "_request", lambda *args: response)
    with pytest.raises(DomainError) as caught:
        instance.encode("织机")
    assert caught.value.code == "MODEL_UNAVAILABLE"
    assert caught.value.status_code == 503


def test_unavailable_does_not_become_baseline(monkeypatch: pytest.MonkeyPatch) -> None:
    instance = provider()

    def fail(*args: Any) -> None:
        raise ConnectionError("offline")

    monkeypatch.setattr(instance, "_request", fail)
    assert not instance.health().available
    with pytest.raises(DomainError):
        instance.encode("水磨")
    registry = ProviderRegistry.create(Settings(retrieval_profile="neural"))
    assert registry.text_embedding.provider_name == "bge_zh"
    assert registry.image_embedding.provider_name == "chinese_clip_image"
    assert registry.clip_text is not None


def test_cross_modal_scores_use_clip_space_not_bge() -> None:
    service = SearchService(Settings())
    from app.domain.enums import SearchType
    from app.services.search_service import QueryContext

    query = QueryContext(SearchType.TEXT, "织机", None, [], [], [], {})
    figure = Figure(id=uuid4(), regions=[], assertions=[], relations=[])
    item = {
        "image": [0.0, 1.0],
        "text_vector": [1.0, 0.0],
        "clip_text_vector": [0.0, 1.0],
        "region_vectors": [],
    }
    scores, _ = service._component_scores(query, figure, item, [1.0, 0.0], None, 0.0, [0.0, 1.0])
    assert scores["sv"] == 1.0
    assert scores["st"] == pytest.approx(0.7)
    image_scores, _ = service._component_scores(
        query,
        figure,
        item,
        None,
        [0.0, 1.0],
        0.0,
    )
    assert image_scores["st"] == 1.0


def test_missing_neural_index_returns_explicit_error() -> None:
    service = SearchService(Settings(retrieval_profile="neural"))
    figure = Figure(id=uuid4(), title="织机", regions=[], text_chunks=[], asset=None)
    with pytest.raises(DomainError) as caught:
        service._candidate_features(figure, {})
    assert caught.value.code == "MODEL_UNAVAILABLE"
    assert caught.value.details["reason"] == "compatible_index_missing"


@pytest.mark.asyncio
async def test_vector_selection_checks_all_space_fields() -> None:
    registry = ProviderRegistry.create(Settings(retrieval_profile="neural"))
    service = SearchService(Settings(), providers=registry)
    figure = Figure(id=uuid4(), regions=[])
    metadata = registry.text_embedding.metadata()
    records = []
    for changes in (
        {"dimension": 256},
        {"provider": "other"},
        {"version": "old"},
        {"model": "different"},
        {"preprocessing_hash": "0" * 64},
        {},
    ):
        record = EmbeddingRecord(
            id=uuid4(),
            entity_id=figure.id,
            entity_type="figure",
            modality="text",
            vector=[1.0] + [0.0] * 511,
            **{**{k: v for k, v in metadata.as_dict().items() if k != "latency_ms"}, **changes},
        )
        records.append(record)
    # The incompatible rows appear last, preventing accidental overwrite by iteration order.
    records.reverse()

    class Result:
        def scalars(self) -> Result:
            return self

        def all(self) -> list[EmbeddingRecord]:
            return records

    class Session:
        async def execute(self, statement: Any) -> Result:
            return Result()

    selected = await service._embedding_map(Session(), [figure])  # type: ignore[arg-type]
    assert selected == {("figure", figure.id, "text"): records[0].vector}


@pytest.mark.asyncio
async def test_baseline_and_neural_embedding_ids_do_not_collide() -> None:
    ids = []

    class Session:
        async def get(self, model: Any, key: Any) -> None:
            ids.append(key)

        def add(self, obj: Any) -> None:
            pass

    entity_id = uuid4()
    baseline = ProviderRegistry.create().text_embedding.encode("织机")
    neural = provider()
    from app.retrieval.providers.base import VectorResult

    result = VectorResult((1.0,) + (0.0,) * 511, neural.metadata())
    for value in (baseline, result, result):
        await _upsert_embedding(Session(), entity_id, "figure", "text", value)  # type: ignore[arg-type]
    assert ids[0] != ids[1]
    assert ids[1] == ids[2]
