from __future__ import annotations

import copy
import io
import json
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest
from PIL import Image
from pydantic import ValidationError

from app.core.config import Settings
from app.ingestion.contracts import AIRealManifest, RealManifest
from app.ingestion.loader import ManifestValidationError, load_manifest
from app.schemas.common import SearchFilters
from app.services.ingestion_service import _figure_image_input, _review_provenance, stable_id
from app.services.search_service import SearchService
from app.services.serializers import data_status
from scripts.prepare_domestic_ai_manifest import prepare, sha256


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False), encoding="utf-8")


@pytest.fixture
def ai_workspace(tmp_path: Path) -> dict[str, Any]:
    """Isolated artificial scans for contract tests, never competition data."""
    pdf = tmp_path / "backend/data/assets/real_pilot_v1/test.pdf"
    pdf.parent.mkdir(parents=True)
    pdf.write_bytes(b"%PDF-test-only-not-a-real-book")
    scan = tmp_path / "processed/test.png"
    scan.parent.mkdir()
    image = Image.new("RGB", (100, 100), "red")
    image.paste("green", (50, 0, 100, 100))
    image.save(scan)
    source = {
        "source_id": "test-source",
        "sha256": sha256(pdf),
        "local_filename": "test.pdf",
        "book_title": "隔离测试资料",
        "author": "测试作者",
        "edition_note": "test-only",
        "volume": "1",
        "source_name": "test-only",
        "source_url": "https://example.invalid",
        "license_status": "public_domain",
        "license_note": "isolated synthetic test input",
        "allow_training": False,
        "allow_redistribution": True,
        "retrieved_at": "2026-10-05T00:00:00+00:00",
    }
    registry, inventory, raw, selection = [
        tmp_path / f"{n}.json" for n in ("sources", "inventory", "raw", "selection")
    ]
    write_json(registry, {"sources": [source]})
    write_json(
        inventory,
        {
            "generated_at": source["retrieved_at"],
            "pages": [
                {
                    "page_id": "test-page",
                    "source_id": "test-source",
                    "image_path": "processed/test.png",
                    "pdf_page": 1,
                    "page_or_folio": "pdf-page-0001",
                    "volume": "1",
                    "width": 100,
                    "height": 100,
                    "sha256": sha256(scan),
                    "provenance": {"pdf_sha256": sha256(pdf)},
                }
            ],
        },
    )
    write_json(
        raw,
        {
            "run_status": "completed",
            "run_identity": {"inventory_sha256": sha256(inventory)},
            "pages": [
                {
                    "page_id": "test-page",
                    "source_id": "test-source",
                    "input_sha256": sha256(scan),
                    "status": "inferred",
                    "provider": "test",
                    "model": "test",
                    "version": "1",
                    "lines": [
                        {
                            "bbox": [5, 0, 40, 10],
                            "text": "页顶题诗",
                            "confidence": 0.5,
                            "reading_order": 0,
                        },
                        {
                            "bbox": [10, 40, 25, 60],
                            "text": "左raw错字",
                            "confidence": 0.5,
                            "reading_order": 1,
                        },
                        {
                            "bbox": [60, 40, 75, 60],
                            "text": "右raw",
                            "confidence": 0.5,
                            "reading_order": 2,
                        },
                    ],
                }
            ],
        },
    )
    figures = []
    for key, x in [("left", 0.05), ("right", 0.55)]:
        figures.append(
            {
                "figure_id": f"ai-test-{key}",
                "page_id": "test-page",
                "title": f"{key}（AI场景名）",
                "title_origin": "ai_visual_description",
                "description": "AI场景描述，不是古文。",
                "visual_note": "isolated test",
                "bbox": {"x": x, "y": 0.25, "width": 0.40, "height": 0.7},
                "regions": [
                    {
                        "label": "test-region",
                        "bbox": {
                            "x": x + 0.05,
                            "y": 0.4,
                            "width": 0.2,
                            "height": 0.2,
                        },
                    }
                ],
            }
        )
    write_json(
        selection,
        {
            "schema_version": "1.0",
            "selection_id": "test-selection",
            "review_origin": "ai_assisted",
            "human_review_status": "skipped_by_user_for_competition",
            "evaluation_status": "not_evaluated",
            "priority": "domestic_publication",
            "disclaimer": "isolated artificial test not_evaluated",
            "scope_note": "test only",
            "source_categories": {"test-source": "domestic_publication"},
            "figures": figures,
        },
    )
    return {
        "project_root": tmp_path,
        "selection_path": selection,
        "source_registry": registry,
        "inventory_path": inventory,
        "raw_ocr_path": raw,
        "assets_root": tmp_path / "export/assets",
        "manifests_root": tmp_path / "export/manifests",
        "report_root": tmp_path / "export/reports",
    }


def test_ai_export_is_scoped_traced_immutable_and_not_human(ai_workspace: dict[str, Any]) -> None:
    report = prepare(**ai_workspace)
    assert prepare(**ai_workspace) == report
    assert report["counts"]["figures"] == 2 and report["scoped_raw_lines"] == 2
    assert report["metrics"] is None and report["human_review"] is False
    validated = load_manifest(
        report["manifest_name"],
        manifests_root=ai_workspace["manifests_root"],
        assets_root=ai_workspace["assets_root"],
    )
    manifest = validated.manifest
    assert isinstance(manifest, AIRealManifest)
    raws = [c for c in manifest.text_chunks if c.kind == "ocr"]
    assert [c.content for c in raws] == ["左raw错字", "右raw"]
    assert all(c.transcription_review is None for c in manifest.text_chunks)
    assert all(e.state != "Verified" for e in manifest.evidence)
    provenance = _review_provenance(validated, figure_id="ai-test-left")
    assert "human_review" not in provenance
    assert provenance["ai_review"]["human_review"] is False
    assert len(provenance["ai_review"]["text_traces"]) == 3
    assert data_status(SimpleNamespace(provenance=provenance)).human_reviewed is False
    # Real scan embeddings must use the selected scene, not the entire two-scene page.
    crop = _figure_image_input(validated, manifest.figures[0])
    assert isinstance(crop, bytes)
    with Image.open(io.BytesIO(crop)) as image:
        assert image.width == 40 and image.getpixel((0, 0)) == (255, 0, 0)
    with pytest.raises(ValidationError):
        RealManifest.model_validate(manifest.model_dump(mode="json"))


@pytest.mark.parametrize(
    "mutation",
    [
        "human",
        "truth",
        "verified",
        "documented_text",
        "observed_region",
        "missing_audit",
        "wrong_extent",
        "wrong_page",
        "raw_rewritten",
        "corrected",
    ],
)
def test_ai_contract_rejects_false_claims_and_trace_drift(
    ai_workspace: dict[str, Any],
    mutation: str,
) -> None:
    report = prepare(**ai_workspace)
    payload = json.loads(
        (ai_workspace["manifests_root"] / report["manifest_name"]).read_text("utf-8")
    )
    if mutation == "human":
        payload["ai_audit"]["human_review"] = True
    elif mutation == "truth":
        payload["ai_audit"]["independent_ground_truth"] = True
    elif mutation == "verified":
        payload["evidence"][0]["state"] = "Verified"
    elif mutation == "documented_text":
        payload["text_chunks"][0]["evidence_state"] = "Documented"
    elif mutation == "observed_region":
        payload["regions"][0]["evidence_state"] = "Observed"
    elif mutation == "missing_audit":
        payload["ai_audit"]["figures"].pop()
    elif mutation == "wrong_extent":
        payload["ai_audit"]["figures"][0]["bbox"]["width"] = 0.3
    elif mutation == "wrong_page":
        payload["text_chunks"][0]["ai_trace"]["page_id"] = "another-page"
    elif mutation == "raw_rewritten":
        next(c for c in payload["text_chunks"] if c["kind"] == "ocr")["content"] = "假校订"
    elif mutation == "corrected":
        payload["text_chunks"][1]["kind"] = "corrected"
    with pytest.raises(ValidationError):
        AIRealManifest.model_validate(payload)


@pytest.mark.parametrize(
    "target", ["pdf", "scan", "inventory_binding", "license", "path", "majority"]
)
def test_export_rejects_input_drift(ai_workspace: dict[str, Any], target: str) -> None:
    if target == "pdf":
        (ai_workspace["project_root"] / "backend/data/assets/real_pilot_v1/test.pdf").write_bytes(
            b"drift"
        )
    elif target == "scan":
        (ai_workspace["project_root"] / "processed/test.png").write_bytes(b"drift")
    else:
        path = ai_workspace[
            "raw_ocr_path"
            if target == "inventory_binding"
            else "source_registry"
            if target in {"license", "path"}
            else "selection_path"
        ]
        payload = json.loads(path.read_text("utf-8"))
        if target == "inventory_binding":
            payload["run_identity"]["inventory_sha256"] = "0" * 64
        elif target == "license":
            payload["sources"][0]["allow_redistribution"] = False
        elif target == "path":
            payload["sources"][0]["local_filename"] = "../../test.pdf"
        else:
            payload["source_categories"]["test-source"] = "domestic_holding"
        write_json(path, payload)
    with pytest.raises((ValueError, ManifestValidationError)):
        prepare(**ai_workspace)


def test_changed_existing_output_is_not_overwritten(ai_workspace: dict[str, Any]) -> None:
    report = prepare(**ai_workspace)
    output = ai_workspace["manifests_root"] / report["manifest_name"]
    output.write_bytes(b"user content")
    with pytest.raises(ValueError, match="overwrite"):
        prepare(**ai_workspace)
    assert output.read_bytes() == b"user content"


def test_corpus_filter_and_source_category_are_independent() -> None:
    provenance = {
        "dataset_kind": "ai_assisted_real_pilot",
        "source_category": "domestic_publication",
    }
    figure = SimpleNamespace(provenance=copy.deepcopy(provenance))
    assert SearchService._matches_filters(
        figure, SearchFilters(dataset_kinds=["ai_assisted_real_pilot"])
    )
    assert not SearchService._matches_filters(
        figure, SearchFilters(dataset_kinds=["synthetic_fixture"])
    )
    assert data_status(figure).source_category == "domestic_publication"
    with pytest.raises(ValidationError):
        SearchFilters(dataset_kinds=["fake-dataset"])


def test_reloaded_candidate_keeps_similarity_order_of_multiple_regions() -> None:
    regions = [
        SimpleNamespace(
            id=stable_id("region", f"r{i}"),
            label=f"r{i}",
            x=0.1,
            y=0.2,
            width=0.3,
            height=0.4,
        )
        for i in range(2)
    ]
    figure = SimpleNamespace(
        id=stable_id("figure", "f"),
        title="test",
        asset=None,
        regions=regions,
        evidences=[],
        provenance={"dataset_kind": "ai_assisted_real_pilot"},
        page=SimpleNamespace(
            volume="1",
            page_or_folio="1",
            edition=SimpleNamespace(
                book=SimpleNamespace(title="test"),
                name="test",
                source_name="test",
                source_url="https://example.invalid",
                license_status="public_domain",
            ),
        ),
    )
    matched = [str(regions[1].id), str(regions[0].id)]
    candidate = SimpleNamespace(
        id=stable_id("candidate", "c"),
        figure=figure,
        evidence_summary={"matched_region_ids": matched},
        cfr_summary={},
        score=0.5,
        score_components={},
        uncertainty={},
        verification_state="pending",
    )
    reloaded = SearchService(Settings())._stored_result(candidate, stable_id("search", "s"))
    assert [str(r.id) for r in reloaded.matched_regions] == matched
