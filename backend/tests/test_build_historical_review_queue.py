from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest
from PIL import Image

from scripts.build_historical_review_queue import build_review_queue
from scripts.convert_ppocrlabel_annotations import ConversionError


def _candidate(tmp_path: Path, *, state: str = "inferred") -> Path:
    image_path = tmp_path / "page.png"
    Image.new("RGB", (200, 300), "white").save(image_path)
    box_base = {
        "polygon": [[10, 10], [30, 10], [30, 250], [10, 250]],
        "bbox": {"x": 0.05, "y": 0.03, "width": 0.1, "height": 0.8},
        "reading_order": 1,
        "category_confidence": 0.99,
        "normalized_candidate": None,
        "agreement": 1.0,
        "needs_review": False,
        "verification_state": state,
    }
    payload = {
        "evaluation_status": "not_evaluated",
        "pages": [
            {
                "page_id": "source-p0001",
                "image_path": "page.png",
                "boxes": [
                    {
                        **box_base,
                        "box_id": "source-p0001-b001",
                        "raw_text": "凡蠶用浴法",
                        "category_candidate": "text",
                        "role_candidate": "body",
                        "server_ocr": {"text": "凡蠶用浴法", "confidence": 0.99},
                        "reference_candidate": {
                            "text": "凡蠶用浴法",
                            "alignment_confidence": 0.99,
                        },
                    },
                    {
                        **box_base,
                        "box_id": "source-p0001-b002",
                        "raw_text": "圖絲治",
                        "category_candidate": "caption",
                        "role_candidate": "figure_title",
                        "server_ocr": {"text": "治絲圖", "confidence": 0.95},
                        "reference_candidate": None,
                    },
                ],
                "figures": [
                    {
                        "figure_id": "source-p0001-f01",
                        "bbox": {"x": 0.2, "y": 0.2, "width": 0.5, "height": 0.5},
                        "category_candidate": "figure",
                        "candidate_title": "治絲圖",
                        "verification_state": "inferred",
                    }
                ],
            }
        ],
    }
    path = tmp_path / "candidates.json"
    path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    return path


def test_queue_focuses_uncertain_items_without_verifying_them(tmp_path: Path) -> None:
    payload = build_review_queue(
        candidate_path=_candidate(tmp_path),
        output_path=tmp_path / "queue.html",
        manifest_path=tmp_path / "queue.json",
        asset_dir=tmp_path / "assets",
        project_root=tmp_path,
    )

    assert payload["statistics"] == {
        "total_boxes": 2,
        "focused_boxes": 1,
        "figure_regions": 1,
        "queue_items": 2,
        "all_items": 3,
        "missing_caption_candidates": 0,
        "critical_items": 0,
        "deferred_candidates": 1,
        "human_verified": 0,
    }
    assert {item["id"] for item in payload["items"]} == {
        "source-p0001-b001",
        "source-p0001-b002",
        "source-p0001-f01",
    }
    assert all(item["verification_state"] == "inferred" for item in payload["items"])
    assert len(list((tmp_path / "assets").rglob("*.jpg"))) == 3
    assert "已对照扫描确认此项" in (tmp_path / "queue.html").read_text(encoding="utf-8")


def test_queue_rejects_candidate_already_marked_verified(tmp_path: Path) -> None:
    with pytest.raises(ConversionError, match="not inferred"):
        build_review_queue(
            candidate_path=_candidate(tmp_path, state="verified"),
            output_path=tmp_path / "queue.html",
            manifest_path=tmp_path / "queue.json",
            asset_dir=tmp_path / "assets",
            project_root=tmp_path,
        )


def test_queue_adds_missing_title_and_preserves_existing_assets(tmp_path: Path) -> None:
    path = _candidate(tmp_path)
    data = json.loads(path.read_text(encoding="utf-8"))
    figure = data["pages"][0]["figures"][0]
    figure["candidate_title_bbox"] = {"x": 0.2, "y": 0.2, "width": 0.2, "height": 0.1}
    path.write_text(json.dumps(data), encoding="utf-8")
    asset_dir = tmp_path / "assets"
    asset_dir.mkdir()
    sentinel = asset_dir / "existing-human-file.txt"
    sentinel.write_text("preserve", encoding="utf-8")
    payload = build_review_queue(
        candidate_path=path,
        output_path=tmp_path / "queue.html",
        manifest_path=tmp_path / "queue.json",
        asset_dir=asset_dir,
        project_root=tmp_path,
    )

    assert payload["statistics"]["missing_caption_candidates"] == 1
    title = next(item for item in payload["items"] if item["kind"] == "caption")
    assert title["id"] == "source-p0001-f01-title"
    assert title["normalized_candidate"] == "治絲圖"
    assert title["verification_state"] == "inferred"
    assert (tmp_path / title["crop_path"]).is_file()
    assert sentinel.read_text(encoding="utf-8") == "preserve"


def test_queue_rejects_asset_directory_outside_project(tmp_path: Path) -> None:
    with pytest.raises(ConversionError, match="inside the project"):
        build_review_queue(
            candidate_path=_candidate(tmp_path),
            output_path=tmp_path / "queue.html",
            manifest_path=tmp_path / "queue.json",
            asset_dir=tmp_path.parent / "outside",
            project_root=tmp_path,
        )


def test_ai_queue_uses_separate_artifact_and_keeps_candidates_inferred(tmp_path: Path) -> None:
    path = _candidate(tmp_path)
    human_path = tmp_path / "queue.html"
    human_path.write_text("existing human review", encoding="utf-8")
    payload = build_review_queue(
        candidate_path=path,
        output_path=tmp_path / "queue.ai.html",
        manifest_path=tmp_path / "queue.ai.json",
        asset_dir=tmp_path / "assets",
        project_root=tmp_path,
        review_origin="ai_assisted",
    )
    assert human_path.read_text(encoding="utf-8") == "existing human review"
    assert payload["review_origin"] == "ai_assisted"
    assert payload["dataset_kind"] == "real_pilot_ai_assisted_review_queue"
    assert all(item["verification_state"] == "inferred" for item in payload["items"])


def test_queue_rejects_unknown_review_origin(tmp_path: Path) -> None:
    with pytest.raises(ConversionError, match="unsupported review origin"):
        build_review_queue(review_origin="verified_by_model")


def test_human_queue_displays_bound_ai_hints_without_prefilling_confirmations(
    tmp_path: Path,
) -> None:
    candidate_path = _candidate(tmp_path)
    hints = {
        "dataset_kind": "ai_assisted_review_overrides",
        "review_origin": "ai_assisted",
        "source_candidate_sha256": hashlib.sha256(candidate_path.read_bytes()).hexdigest(),
        "input_hashes": {},
        "records": [
            {
                "box_or_figure_id": "source-p0001-b001",
                "page_id": "source-p0001",
                "kind": "box",
                "review_origin": "ai_assisted",
                "verification_state": "inferred",
                "requires_human_confirmation": True,
                "corrected_text": "AI建议",
                "bbox": {"x": 0.1, "y": 0.1, "width": 0.2, "height": 0.2},
            }
        ],
    }
    path = tmp_path / "hints.json"
    path.write_text(json.dumps(hints), encoding="utf-8")
    payload = build_review_queue(
        candidate_path=candidate_path,
        ai_review_path=path,
        output_path=tmp_path / "human.html",
        manifest_path=tmp_path / "human.json",
        asset_dir=tmp_path / "assets",
        project_root=tmp_path,
    )
    item = next(item for item in payload["items"] if item["id"] == "source-p0001-b001")
    assert item["ai_review_hint"]["corrected_text"] == "AI建议"
    assert payload["ai_review_seed"] == []
    assert payload["statistics"]["human_verified"] == 0
    hints["records"][0]["verification_state"] = "verified"
    path.write_text(json.dumps(hints), encoding="utf-8")
    previous = (tmp_path / "human.html").read_bytes()
    with pytest.raises(ConversionError, match="human confirmation"):
        build_review_queue(
            candidate_path=candidate_path,
            ai_review_path=path,
            output_path=tmp_path / "human.html",
            manifest_path=tmp_path / "human.json",
            asset_dir=tmp_path / "assets",
            project_root=tmp_path,
        )
    assert (tmp_path / "human.html").read_bytes() == previous


def test_ai_queue_restores_actual_export_without_mutating_candidate(tmp_path: Path) -> None:
    candidate_path = _candidate(tmp_path)
    previous = candidate_path.read_bytes()
    decision = {
        "box_or_figure_id": "source-p0001-b001", "page_id": "source-p0001", "kind": "box",
        "review_origin": "ai_assisted", "verification_state": "inferred",
        "requires_human_confirmation": True, "corrected_text": "实际UI修订",
        "bbox": {"x": 0.1, "y": 0.1, "width": 0.2, "height": 0.2},
        "confirmed": True, "review_note": "扫描检查依据", "reviewer": "test AI",
    }
    hints = {
        "dataset_kind": "ai_assisted_review_overrides", "review_origin": "ai_assisted",
        "source_candidate_sha256": hashlib.sha256(previous).hexdigest(),
        "input_hashes": {}, "records": [decision],
    }
    path = tmp_path / "hints.json"
    path.write_text(json.dumps(hints), encoding="utf-8")
    payload = build_review_queue(
        candidate_path=candidate_path, ai_review_path=path, review_origin="ai_assisted",
        output_path=tmp_path / "ai.html", manifest_path=tmp_path / "ai.json",
        asset_dir=tmp_path / "assets", project_root=tmp_path,
    )
    assert payload["ai_review_seed"] == [decision]
    assert payload["statistics"]["human_verified"] == 0
    assert payload["ai_hint_export_sha256"] == hashlib.sha256(path.read_bytes()).hexdigest()
    assert candidate_path.read_bytes() == previous
