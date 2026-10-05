from __future__ import annotations

import copy
import json
from pathlib import Path
from types import SimpleNamespace
from typing import Any
from unittest.mock import AsyncMock

import pytest
from pydantic import ValidationError
from test_domestic_ai_manifest import ai_workspace  # noqa: F401

from app.core.config import Settings
from app.db.models import Figure
from app.ingestion.contracts import AIRealManifest
from app.ingestion.loader import load_manifest
from app.retrieval.experiments.comparison import (
    ComparisonRunner,
    applicable,
    corpus_snapshot,
    experiment_cfr,
)
from app.retrieval.experiments.contracts import (
    METHODS,
    EvidencePlan,
    FixedQuery,
    FunctionDraft,
    QueryProtocol,
    RelationDraft,
)
from app.retrieval.experiments.evidence import (
    bind_drafts,
    canonical_hash,
    immutable_write,
    scoped_functions,
)
from app.retrieval.experiments.report import summarize
from app.retrieval.providers.base import VectorResult
from app.services.ingestion_service import stable_id
from app.services.search_service import SearchService
from scripts.prepare_domestic_ai_manifest import prepare
from scripts.run_domestic_comparison import run_comparison

DATA = Path(__file__).parents[1] / "data/experiments"


def test_fixed_protocol_is_real_unlabelled_and_has_three_modalities() -> None:
    protocol = QueryProtocol.model_validate_json(
        (DATA / "domestic-queries-v1.json").read_text(encoding="utf-8")
    )
    assert len(protocol.queries) == 24
    assert [
        sum(q.kind == kind for q in protocol.queries) for kind in ("text", "image", "region")
    ] == [16, 4, 4]
    assert all(q.relevance_labels is None for q in protocol.queries)
    assert sum(applicable(m, q) for m in METHODS for q in protocol.queries) == 176
    assert not protocol.independent_ground_truth


@pytest.mark.parametrize(
    "changes",
    [
        {"relevance_labels": {"f": 1}},
        {"qrels": {}},
        {"text": "generated caption"},
        {"exclude_source": False},
        {"bbox": {"x": 0.9, "y": 0, "width": 0.2, "height": 1}},
    ],
)
def test_visual_protocol_rejects_truth_leakage_and_invalid_crop(changes: dict[str, Any]) -> None:
    value = {
        "id": "q",
        "kind": "region",
        "category": "test",
        "purpose": "test",
        "source_figure_key": "f",
        "bbox": {"x": 0, "y": 0, "width": 1, "height": 1},
    }
    with pytest.raises(ValidationError):
        FixedQuery.model_validate({**value, **changes})


@pytest.mark.parametrize("change", [{"state": "Verified"}, {"confidence": 0.9}])
def test_ai_drafts_reject_verification_and_invented_probability(change: dict[str, Any]) -> None:
    with pytest.raises(ValidationError):
        FunctionDraft.model_validate(
            {
                "slot": "action",
                "concept": "unknown",
                "label": "未知",
                "rationale": "未定",
                "supports": [],
                **change,
            }
        )
    with pytest.raises(ValidationError):
        RelationDraft.model_validate(
            {
                "subject": "a",
                "predicate": "b",
                "object": "c",
                "rationale": "test",
                "supports": [{"kind": "scan_region", "reference_id": "r", "note": "test"}],
                **change,
            }
        )


@pytest.fixture
def bound_workspace(request: pytest.FixtureRequest) -> tuple[AIRealManifest, dict[str, Any]]:
    workspace = request.getfixturevalue("ai_workspace")
    report = prepare(**workspace)
    manifest = load_manifest(
        report["manifest_name"],
        manifests_root=workspace["manifests_root"],
        assets_root=workspace["assets_root"],
    ).manifest
    assert isinstance(manifest, AIRealManifest)
    region = next(r for r in manifest.regions if r.figure_id == "ai-test-left")
    chunk = next(c for c in manifest.text_chunks if c.text_id == "ai-test-left-context")
    plan = {
        "schema_version": "1.0",
        "plan_id": "test",
        "review_origin": "ai_assisted",
        "evaluation_status": "not_evaluated",
        "independent_ground_truth": False,
        "confidence_policy": "uncalibrated_null",
        "disclaimer": "test-only",
        "figures": [
            {
                "figure_key": "ai-test-left",
                "case_id": "test-case",
                "functions": [
                    {
                        "slot": "object",
                        "concept": "fiber",
                        "label": "纤维",
                        "rationale": "test",
                        "supports": [
                            {
                                "kind": "scan_region",
                                "reference_id": region.region_id,
                                "note": "test",
                            },
                            {
                                "kind": "ai_visual_description",
                                "reference_id": chunk.text_id,
                                "quote": chunk.content,
                                "note": "AI description, not ancient prose",
                            },
                        ],
                    }
                ],
                "relations": [],
                "unresolved": ["unreviewed"],
            }
        ],
    }
    return manifest, plan


def test_bound_evidence_preserves_hash_origin_and_exact_quote(
    bound_workspace: tuple[AIRealManifest, dict[str, Any]],
) -> None:
    manifest, plan = bound_workspace
    artifact = bind_drafts(EvidencePlan.model_validate(plan), manifest)
    support = artifact["figures"][0]["functions"][0]["supports"]
    assert [s["support_state"] for s in support] == ["Observed", "Inferred"]
    assert all(not s["ancient_prose_verified"] for s in support)
    assert all(s["asset_sha256"] == manifest.assets[0].sha256 for s in support)
    assert all(s["original_pdf_sha256"] for s in support)
    assert artifact["counts"]["graph_rerank_eligible"] == 0
    assert canonical_hash(artifact) == canonical_hash(
        bind_drafts(EvidencePlan.model_validate(plan), manifest)
    )


@pytest.mark.parametrize("target", ["foreign_region", "false_quote", "false_origin"])
def test_draft_support_refuses_wrong_figure_or_fabricated_text(
    bound_workspace: tuple[AIRealManifest, dict[str, Any]],
    target: str,
) -> None:
    manifest, original = bound_workspace
    plan = copy.deepcopy(original)
    supports = plan["figures"][0]["functions"][0]["supports"]
    if target == "foreign_region":
        supports[0]["reference_id"] = next(
            r.region_id for r in manifest.regions if r.figure_id == "ai-test-right"
        )
    elif target == "false_quote":
        supports[1]["quote"] = "从未出现在来源里的古文"
    else:
        supports[1]["kind"] = "ai_visual_transcription"
    with pytest.raises(ValueError):
        bind_drafts(EvidencePlan.model_validate(plan), manifest)


def test_region_scope_does_not_inherit_outside_function() -> None:
    left = {"x": 0.1, "y": 0.1, "width": 0.2, "height": 0.2}
    right = {"x": 0.6, "y": 0.1, "width": 0.2, "height": 0.2}
    draft = {
        "functions": [
            {"slot": "power_source", "concept": "water_power", "supports": [{"bbox": left}]},
            {"slot": "action", "concept": "grinding", "supports": [{"bbox": right}]},
            {
                "slot": "transmission",
                "concept": "shaft",
                "supports": [{"bbox": left}, {"bbox": right}],
            },
        ]
    }
    assert [f["concept"] for f in scoped_functions(draft, left)] == ["water_power"]
    assert [f["concept"] for f in scoped_functions(draft, right)] == ["grinding"]
    assert scoped_functions(None, left) == []


def test_pair_evidence_is_length_invariant_and_empty_query_unavailable() -> None:
    query = [{"slot": "action", "concept": "pounding"}]
    candidate = [{"slot": "action", "concept": "pounding", "supports": [{"content": "短引文"}]}]
    measure = ComparisonRunner.function_evidence_coverage
    assert measure(query, candidate) == 0.5
    candidate[0]["supports"].append({"content": "无关正文" * 10000})
    assert measure(query, candidate) == 0.5
    assert measure([], candidate) is None
    assert measure(query, []) == 0.0
    assert experiment_cfr().extract("舂捣").slots["action"][0].concept == "pounding"
    assert experiment_cfr().extract("研磨").slots["action"][0].concept == "grinding"


@pytest.fixture
def runner(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> ComparisonRunner:
    service = SearchService(Settings(retrieval_profile="neural"))
    # Orthogonal vectors intentionally give BGE and CLIP different winners.
    a, b = [1.0] + [0.0] * 511, [0.0, 1.0] + [0.0] * 510
    figures = [
        Figure(
            id=stable_id("figure", key),
            title=title,
            provenance={"dataset_kind": "ai_assisted_real_pilot"},
            asset=None,
            regions=[],
            text_chunks=[],
            assertions=[],
            relations=[],
            evidences=[],
        )
        for key, title in [("a", "水轮"), ("b", "织机")]
    ]
    vectors = {}
    for f, text_vector, image_vector in [(figures[0], a, b), (figures[1], b, a)]:
        vectors[("figure", f.id, "text")] = text_vector
        vectors[("figure", f.id, "clip_text")] = image_vector
        vectors[("figure", f.id, "image")] = image_vector
    text_provider = service.providers.text_embedding
    clip_provider = service.providers.clip_text
    assert clip_provider is not None
    monkeypatch.setattr(
        text_provider, "encode_query", lambda _: VectorResult(tuple(a), text_provider.metadata())
    )
    monkeypatch.setattr(
        clip_provider, "encode", lambda _: VectorResult(tuple(a), clip_provider.metadata())
    )
    return ComparisonRunner(
        Settings(asset_root=tmp_path),
        figures,
        vectors,
        {"figures": []},
        {"a": figures[0].id, "b": figures[1].id},
        service,
    )


@pytest.mark.asyncio
async def test_methods_use_their_actual_spaces_and_repeat_ranking(runner: ComparisonRunner) -> None:
    query = FixedQuery(id="q", kind="text", category="test", purpose="test", text="水轮")
    bge = await runner.run(query, "bge", 2)
    clip = await runner.run(query, "chinese_clip", 2)
    assert bge["results"][0]["figure_id"] == str(runner.keys["a"])
    assert clip["results"][0]["figure_id"] == str(runner.keys["b"])
    assert (await runner.run(query, "bge", 2))["ranking_sha256"] == bge["ranking_sha256"]
    draft = await runner.run(query, "eafr_drafts", 2)
    assert not draft["results"][0]["score_components"]["availability"]["graph"]
    assert not draft["results"][0]["score_components"]["availability"]["model_uncertainty"]


@pytest.mark.asyncio
async def test_no_visual_caption_fallback_and_exclude_source(runner: ComparisonRunner) -> None:
    query = FixedQuery(id="q", kind="image", category="test", purpose="test", source_figure_key="a")
    assert [f.id for f in runner.candidates(query)] == [runner.keys["b"]]
    for method in ("bm25", "bge"):
        row = await runner.run(query, method, 2)
        assert row["status"] == "not_applicable" and "results" not in row


@pytest.mark.asyncio
async def test_neural_failure_is_not_replaced_with_prior_or_baseline(
    runner: ComparisonRunner,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fail(_: str) -> None:
        raise ConnectionError("worker unavailable")

    monkeypatch.setattr(runner.service.providers.text_embedding, "encode_query", fail)
    with pytest.raises(ConnectionError):
        await runner.run(
            FixedQuery(id="q", kind="text", category="test", purpose="test", text="水轮"), "bge", 2
        )


@pytest.mark.asyncio
async def test_preflight_refuses_manifest_drift_before_model_or_database(tmp_path: Path) -> None:
    value = json.loads((DATA / "domestic-queries-v1.json").read_text(encoding="utf-8"))
    protocol = tmp_path / "protocol.json"
    protocol.write_text(json.dumps(value), encoding="utf-8")
    (tmp_path / value["manifest_name"]).write_bytes(b"drift")
    with pytest.raises(ValueError, match="manifest hash"):
        await run_comparison(
            Settings(retrieval_profile="neural", manifest_root=tmp_path),
            protocol,
            DATA / "domestic-functions-v1.json",
        )


def test_no_overwrite_and_no_metrics_from_rank_change(tmp_path: Path) -> None:
    path = tmp_path / "artifact.json"
    immutable_write(path, b"first")
    immutable_write(path, b"first")
    with pytest.raises(ValueError, match="overwrite"):
        immutable_write(path, b"changed")
    assert path.read_bytes() == b"first"
    result = summarize([])
    assert result["research_metrics"]["status"] == "not_evaluated"
    assert result["research_metrics"]["recall_at_k"] is None


@pytest.fixture
def snapshot_inputs(
    bound_workspace: tuple[AIRealManifest, dict[str, Any]],
    request: pytest.FixtureRequest,
    monkeypatch: pytest.MonkeyPatch,
) -> tuple[Any, SearchService, AIRealManifest, list[Any], dict[Any, Any]]:
    manifest, _ = bound_workspace
    workspace = request.getfixturevalue("ai_workspace")
    service = SearchService(Settings(asset_root=workspace["assets_root"]))
    figures = []
    for spec in manifest.figures:
        asset = next(a for a in manifest.assets if a.asset_id == spec.asset_id)
        page = next(p for p in manifest.pages if p.page_id == spec.page_id)
        source = next(s for s in manifest.sources if s.source_id == page.source_id)
        figures.append(
            SimpleNamespace(
                id=stable_id("figure", spec.figure_id),
                title=spec.title,
                page_id=stable_id("page", page.page_id),
                provenance={
                    "dataset_kind": "ai_assisted_real_pilot",
                    "original_pdf_sha256": source.original_sha256,
                },
                asset=SimpleNamespace(
                    id=stable_id("asset", asset.asset_id),
                    sha256=asset.sha256,
                    relative_path=asset.relative_path,
                    allow_redistribution=source.allow_redistribution,
                ),
                page=SimpleNamespace(
                    edition=SimpleNamespace(
                        source_url=source.source_url,
                        name=source.edition,
                        book=SimpleNamespace(title=source.book_title),
                    )
                ),
                bbox_x=spec.bbox.x,
                bbox_y=spec.bbox.y,
                bbox_width=spec.bbox.width,
                bbox_height=spec.bbox.height,
                assertions=[],
                relations=[],
                text_chunks=[
                    SimpleNamespace(
                        source_pointer=c.text_id,
                        chunk_type=c.kind.value,
                        text=c.content,
                        corrected_text=None,
                        state=str(c.evidence_state),
                    )
                    for c in manifest.text_chunks
                    if c.figure_id == spec.figure_id
                ],
                regions=[
                    SimpleNamespace(
                        id=stable_id("region", r.region_id),
                        x=r.bbox.x,
                        y=r.bbox.y,
                        width=r.bbox.width,
                        height=r.bbox.height,
                    )
                    for r in manifest.regions
                    if r.figure_id == spec.figure_id
                ],
                evidences=[
                    SimpleNamespace(
                        id=stable_id("evidence", e.evidence_id),
                        evidence_type=e.kind.value,
                        status=str(e.state),
                        pointer=e.source_ref,
                        content=e.excerpt or f"{e.kind.value} evidence: {e.source_ref}",
                    )
                    for e in manifest.evidence
                    if e.figure_id == spec.figure_id
                ],
            )
        )
    vectors = {
        ("figure", f.id, m): [1.0] + [0.0] * 511
        for f in figures
        for m in ("text", "clip_text", "image")
    }
    vectors.update(
        {("region", r.id, "image"): [1.0] + [0.0] * 511 for f in figures for r in f.regions}
    )
    monkeypatch.setattr(service, "_embedding_map", AsyncMock(return_value=vectors))
    session = SimpleNamespace(execute=AsyncMock(return_value=SimpleNamespace(scalars=lambda: [])))
    return session, service, manifest, figures, vectors


@pytest.mark.asyncio
@pytest.mark.parametrize("target", ["text", "state", "evidence", "source", "pdf", "vector"])
async def test_snapshot_refuses_database_or_vector_drift(
    snapshot_inputs: tuple[Any, SearchService, AIRealManifest, list[Any], dict[Any, Any]],
    target: str,
) -> None:
    session, service, manifest, figures, vectors = snapshot_inputs
    if target == "text":
        figures[0].text_chunks[0].text = "changed"
    elif target == "state":
        figures[0].text_chunks[0].state = "Verified"
    elif target == "evidence":
        figures[0].evidences[0].content = "changed"
    elif target == "source":
        figures[0].page.edition.source_url = "https://example.invalid/other-source"
    elif target == "pdf":
        figures[0].provenance["original_pdf_sha256"] = "0" * 64
    else:
        vectors.pop(next(iter(vectors)))
    with pytest.raises(ValueError):
        await corpus_snapshot(session, service, manifest, figures)


@pytest.mark.asyncio
async def test_snapshot_refuses_missing_locked_corpus(
    snapshot_inputs: tuple[Any, SearchService, AIRealManifest, list[Any], dict[Any, Any]],
) -> None:
    session, service, manifest, _, _ = snapshot_inputs
    with pytest.raises(ValueError, match="missing"):
        await corpus_snapshot(session, service, manifest, [])
