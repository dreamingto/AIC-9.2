from __future__ import annotations

import json
from io import BytesIO
from pathlib import Path
from typing import Any

import pytest
from PIL import Image
from test_competition_ocr_evaluation import (
    accept_truth,
    core_workspace,  # noqa: F401 -- imported pytest fixture
    digest,
    write_json,
)

from app.ingestion.contracts import FixtureManifest, RealManifest
from app.ingestion.loader import load_manifest
from app.services.ingestion_service import _figure_image_input, _review_provenance
from scripts.convert_ppocrlabel_annotations import ConversionError
from scripts.export_reviewed_real_manifest import export_reviewed_manifest
from scripts.generate_fixture import generate
from scripts.prepare_competition_scope import prepare_scope


@pytest.fixture
def real_workspace(request: pytest.FixtureRequest) -> dict[str, Any]:
    workspace: dict[str, Any] = request.getfixturevalue("core_workspace")
    args = workspace["args"]
    candidates = json.loads(args["candidate_path"].read_text(encoding="utf-8"))
    for page in candidates["pages"]:
        figure_id = page["page_id"] + "-f001"
        bbox = {"x": 0.1, "y": 0.4, "width": 0.8, "height": 0.5}
        page["figures"] = [
            {
                "figure_id": figure_id,
                "bbox": bbox,
                "caption_box_id": page["boxes"][0]["box_id"],
                "verification_state": "inferred",
            }
        ]
        workspace["overrides"]["records"].append(
            {
                "box_or_figure_id": figure_id,
                "page_id": page["page_id"],
                "kind": "figure",
                "category": "figure",
                "role": "technical_figure",
                "bbox": bbox,
                "reading_order": 2,
                "corrected_text": None,
                "confirmed": True,
                "reviewer": "test-reviewer",
                "reviewed_at": "2026-10-03T10:00:00+08:00",
                "verification_state": "verified",
                "evidence": "scan_level_human_review",
            }
        )
    write_json(args["candidate_path"], candidates)
    workspace["overrides"]["source_candidate_sha256"] = digest(args["candidate_path"])
    prepare_scope(
        **{
            key: args[key]
            for key in (
                "selection_path",
                "candidate_path",
                "inventory_path",
                "project_root",
            )
        },
        output_path=args["scope_path"],
    )
    registry = args["scope_path"].parent / "sources.json"
    write_json(
        registry,
        {
            "retrieved_at": "2026-10-03T01:00:00+00:00",
            "sources": [
                {
                    "source_id": "sample-source",
                    "sha256": digest(workspace["pdf"]),
                    "book_title": "测试古籍（非真实样本）",
                    "author": "测试作者",
                    "edition_note": "isolated synthetic test scan, never research truth",
                    "volume": "1",
                    "source_name": "test",
                    "source_url": "https://example.invalid",
                    "license_status": "public_domain",
                    "license_note": "isolated test",
                    "allow_training": False,
                    "allow_redistribution": True,
                }
            ],
        },
    )
    workspace["export_args"] = {
        "evaluation_kwargs": args,
        "sources_path": registry,
        "manifests_root": args["project_root"] / "export/manifests",
        "assets_root": args["project_root"] / "export/assets",
        "report_path": args["project_root"] / "export-report.json",
    }
    return workspace


def test_export_requires_real_confirmation_and_does_not_create_assets(
    real_workspace: dict[str, Any],
) -> None:
    result = export_reviewed_manifest(**real_workspace["export_args"])
    assert result["status"] == "blocked_pending_human_truth"
    assert result["exported_figures"] == 0
    assert not real_workspace["export_args"]["manifests_root"].exists()
    assert not real_workspace["export_args"]["assets_root"].exists()


def test_roundtrip_export_is_idempotent_preserves_raw_and_crops_figures(
    real_workspace: dict[str, Any],
) -> None:
    accept_truth(real_workspace)
    result = export_reviewed_manifest(**real_workspace["export_args"])
    assert result["status"] == "exported_validated_not_imported"
    export_args = real_workspace["export_args"]
    validated = load_manifest(
        result["manifest_name"],
        manifests_root=export_args["manifests_root"],
        assets_root=export_args["assets_root"],
    )
    assert isinstance(validated.manifest, RealManifest)
    assert validated.counts["figures"] == 2
    assert all(
        validated.counts[key] == 0
        for key in (
            "functional_assertions",
            "relations",
            "benchmark_pairs",
        )
    )
    manifest = validated.manifest
    trace = manifest.text_chunks[0].transcription_review
    assert trace is not None and trace.raw_text == "冶絲圖"
    assert manifest.text_chunks[0].content == "治絲圖"
    assert all(e.state != "Verified" for e in manifest.evidence)
    crop = _figure_image_input(validated, manifest.figures[0])
    assert isinstance(crop, bytes)
    with Image.open(BytesIO(crop)) as image:
        assert image.size == (80, 50)
    provenance = _review_provenance(validated, figure_id=manifest.figures[0].figure_id)
    assert provenance["human_review"]["transcriptions"][0]["raw_text"] == "冶絲圖"
    assert provenance["human_review"]["transcriptions"][0]["corrected_text"] == "治絲圖"
    assert export_reviewed_manifest(**export_args) == result


def test_export_rejects_unreviewed_figure_even_after_text_scope_is_ready(
    real_workspace: dict[str, Any],
) -> None:
    real_workspace["overrides"]["records"] = [
        r for r in real_workspace["overrides"]["records"] if r["kind"] != "figure"
    ]
    accept_truth(real_workspace)
    with pytest.raises(ConversionError, match="unconfirmed"):
        export_reviewed_manifest(**real_workspace["export_args"])
    assert not real_workspace["export_args"]["assets_root"].exists()


@pytest.mark.parametrize("change", ["pdf", "confirmation", "raw", "license", "verified"])
def test_real_contract_rejects_broken_audit_and_state_escalation(
    real_workspace: dict[str, Any],
    change: str,
) -> None:
    accept_truth(real_workspace)
    result = export_reviewed_manifest(**real_workspace["export_args"])
    path = real_workspace["export_args"]["manifests_root"] / result["manifest_name"]
    data = json.loads(path.read_text(encoding="utf-8"))
    if change == "pdf":
        data["sources"][0].pop("original_sha256")
    elif change == "confirmation":
        data["review_audit"]["figures"][0]["title_confirmation"]["confirmed"] = False
    elif change == "raw":
        data["text_chunks"][0].pop("transcription_review")
    elif change == "license":
        data["sources"][0]["license_status"] = "synthetic_fixture"
    else:
        data["evidence"][0]["state"] = "Verified"
    with pytest.raises(ValueError):
        RealManifest.model_validate(data)


def test_corrupted_export_cannot_be_silently_replaced(real_workspace: dict[str, Any]) -> None:
    accept_truth(real_workspace)
    result = export_reviewed_manifest(**real_workspace["export_args"])
    path = real_workspace["export_args"]["manifests_root"] / result["manifest_name"]
    data = json.loads(path.read_text(encoding="utf-8"))
    asset = real_workspace["export_args"]["assets_root"] / data["assets"][0]["relative_path"]
    asset.write_bytes(b"corrupted")
    with pytest.raises(ConversionError, match="asset differs"):
        export_reviewed_manifest(**real_workspace["export_args"])
    assert asset.read_bytes() == b"corrupted"


def test_synthetic_fixture_keeps_full_semantic_requirements(tmp_path: Path) -> None:
    path = generate(assets_root=tmp_path / "assets", manifests_root=tmp_path / "manifests")
    data = json.loads(path.read_text(encoding="utf-8"))
    data["relations"] = []
    with pytest.raises(ValueError):
        FixtureManifest.model_validate(data)
