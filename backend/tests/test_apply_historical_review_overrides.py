from __future__ import annotations

import hashlib
import json
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any

import pytest

from scripts.convert_ppocrlabel_annotations import ConversionError, convert_ppocrlabel_annotations


@pytest.mark.parametrize("existing_output", [False, True])
def test_module_cli_rejects_ai_review_without_traceback_or_output_changes(
    review_workspace, existing_output: bool
) -> None:
    kwargs, overrides, override_path = review_workspace
    overrides["dataset_kind"] = "ai_assisted_review_overrides"
    overrides["review_origin"] = "ai_assisted"
    overrides["requires_human_confirmation"] = True
    _write_json(override_path, overrides)

    # Use the real -m entry point in a disposable project, never the user's data.
    project = kwargs["project_root"] / "cli-project"
    backend = project / "backend"
    scripts = backend / "scripts"
    scripts.mkdir(parents=True)
    script_source = Path(__file__).resolve().parents[1] / "scripts"
    for name in (
        "convert_ppocrlabel_annotations.py",
        "apply_historical_review_overrides.py",
        "annotation_errors.py",
    ):
        shutil.copyfile(script_source / name, scripts / name)
    processed = backend / "data/processed/real_pilot_v1"
    shutil.copytree(kwargs["processed_root"], processed)
    real_pilot = backend / "data/real_pilot"
    real_pilot.mkdir(parents=True)
    inventory = json.loads(kwargs["inventory_path"].read_text(encoding="utf-8"))
    inventory["pages"][0]["image_path"] = (
        "backend/data/processed/real_pilot_v1/source-a/page-0001.png"
    )
    _write_json(real_pilot / "derived_pages.json", inventory)
    shutil.copyfile(
        kwargs["review_candidate_path"],
        real_pilot / "annotations.model-assisted-candidates.json",
    )
    output = real_pilot / "annotations.human-reviewed.json"
    prior_bytes = b"existing-human-output-must-be-preserved"
    if existing_output:
        output.write_bytes(prior_bytes)

    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "scripts.convert_ppocrlabel_annotations",
            "--source-id",
            "source-a",
            "--accept-file-state",
            "--reviewer",
            "test-reviewer",
            "--review-overrides",
            str(override_path),
        ],
        cwd=backend,
        capture_output=True,
        text=True,
        check=False,
        timeout=30,
    )
    assert result.returncode == 2
    assert "review artifact kind or state is invalid" in result.stderr
    assert "Traceback" not in result.stderr
    assert not result.stdout.strip()
    if existing_output:
        assert output.read_bytes() == prior_bytes
    else:
        assert not output.exists()


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")


@pytest.fixture
def review_workspace(tmp_path: Path) -> tuple[dict[str, Any], dict[str, Any], Path]:
    source_id = "source-a"
    page_id = "source-a-p0001"
    processed = tmp_path / "processed"
    source = processed / source_id
    source.mkdir(parents=True)
    image = source / "page-0001.png"
    image.write_bytes(b"input-scan")
    boxes = [
        {
            "transcription": text,
            "points": [[x, 10], [x + 10, 10], [x + 10, 90], [x, 90]],
            "difficult": False,
        }
        for x, text in ((10, "机器正文"), (30, "圖絲治"))
    ]
    raw = f"{source_id}/page-0001.png\t{json.dumps(boxes, ensure_ascii=False)}\n"
    for name in ("Cache.cach", "Label.txt"):
        (source / name).write_text(raw, encoding="utf-8")
    (source / "fileState.txt").write_text(f"{source_id}/page-0001.png\t1\n", encoding="utf-8")
    inventory = tmp_path / "inventory.json"
    _write_json(
        inventory,
        {
            "dataset_kind": "real_pilot_page_inventory",
            "evaluation_status": "not_evaluated",
            "pages": [
                {
                    "page_id": page_id,
                    "source_id": source_id,
                    "image_path": "processed/source-a/page-0001.png",
                    "width": 100,
                    "height": 100,
                    "sha256": hashlib.sha256(image.read_bytes()).hexdigest(),
                    "provenance": {},
                }
            ],
        },
    )
    hashes = {
        "inventory_sha256": hashlib.sha256(inventory.read_bytes()).hexdigest(),
        "label_sha256": hashlib.sha256((source / "Label.txt").read_bytes()).hexdigest(),
    }
    candidate = tmp_path / "candidates.json"
    _write_json(
        candidate,
        {
            "dataset_kind": "real_pilot_model_assisted_review_candidates",
            "evaluation_status": "not_evaluated",
            "source_id": source_id,
            "input_hashes": hashes,
            "pages": [
                {
                    "page_id": page_id,
                    "boxes": [
                        {
                            "box_id": f"{page_id}-b{i:03d}",
                            "original_box_index": i,
                            "reading_order": 3 - i,
                            "raw_text": box["transcription"],
                            "verification_state": "inferred",
                        }
                        for i, box in enumerate(boxes, 1)
                    ],
                    "figures": [
                        {
                            "figure_id": f"{page_id}-f01",
                            "caption_box_id": f"{page_id}-b002",
                            "bbox": {"x": 0.5, "y": 0.1, "width": 0.4, "height": 0.8},
                            "verification_state": "inferred",
                        }
                    ],
                }
            ],
        },
    )
    override_path = tmp_path / "overrides.json"
    overrides = {
        "schema_version": "1.0",
        "dataset_kind": "human_review_overrides",
        "source_id": source_id,
        "source_candidate_sha256": hashlib.sha256(candidate.read_bytes()).hexdigest(),
        "input_hashes": hashes,
        "records": [
            {
                "box_or_figure_id": f"{page_id}-b{i:03d}",
                "page_id": page_id,
                "kind": "box",
                "corrected_text": "校订正文" if i == 1 else "治絲圖",
                "category": "text" if i == 1 else "caption",
                "role": "body" if i == 1 else "figure_title",
                "bbox": {"x": 0.1 * i, "y": 0.1, "width": 0.1, "height": 0.8},
                "reading_order": 3 - i,
                "reviewer": "test-reviewer",
                "reviewed_at": "2026-10-02T10:00:00+08:00",
                "confirmed": True,
                "verification_state": "verified",
                "evidence": "scan_level_human_review",
            }
            for i in (1, 2)
        ],
        "page_reviews": [
            {
                "page_id": page_id,
                "reviewer": "test-reviewer",
                "confirmed": True,
                "reviewed_at": "2026-10-02T10:00:00+08:00",
            }
        ],
    }
    kwargs = {
        "source_id": source_id,
        "inventory_path": inventory,
        "project_root": tmp_path,
        "processed_root": processed,
        "output_path": tmp_path / "annotations.json",
        "accept_file_state": True,
        "reviewer": "test-reviewer",
        "review_override_path": override_path,
        "review_candidate_path": candidate,
    }
    return kwargs, overrides, override_path


def test_review_import_preserves_raw_and_tracks_corrected_order(review_workspace) -> None:
    kwargs, overrides, path = review_workspace
    _write_json(path, overrides)
    result = convert_ppocrlabel_annotations(**kwargs)
    page = result["pages"]["source-a-p0001"]

    assert page["text_layers"]["raw_ocr"] == "机器正文\n圖絲治"
    assert page["ocr"]["lines"][0]["text"] == "机器正文"
    assert page["text_layers"]["corrected_text"] == "治絲圖\n校订正文"
    assert page["text_layers"]["correction_state"] == "reviewed"
    assert len(page["text_layers"]["change_log"]) == 2
    assert page["layout"]["reading_order"] == ["source-a-p0001-r002", "source-a-p0001-r001"]
    assert page["figures"][0]["title"] == "治絲圖"
    assert page["figures"][0]["title_verification_state"] == "verified"
    assert page["figures"][0]["region_verification_state"] == "inferred"
    assert result["evaluation_status"] == "not_evaluated"
    assert result["statistics"]["transcription_reviewed_pages"] == 1
    first_bytes = kwargs["output_path"].read_bytes()
    assert convert_ppocrlabel_annotations(**kwargs) == result
    assert kwargs["output_path"].read_bytes() == first_bytes


def test_partial_review_does_not_promote_a_whole_page(review_workspace) -> None:
    kwargs, overrides, path = review_workspace
    overrides["records"] = overrides["records"][:1]
    overrides["page_reviews"] = []
    _write_json(path, overrides)
    result = convert_ppocrlabel_annotations(**kwargs)
    page = result["pages"]["source-a-p0001"]
    assert page["text_layers"]["corrected_text"] is None
    assert page["text_layers"]["correction_state"] == "partial"
    assert len(page["text_layers"]["corrected_lines"]) == 1
    assert result["statistics"]["transcription_reviewed_pages"] == 0
    assert result["review_import"]["caption_ground_truth_verified"] == 0


def test_missing_caption_creates_independent_ground_truth_region(review_workspace) -> None:
    kwargs, overrides, path = review_workspace
    candidate_path = kwargs["review_candidate_path"]
    candidate = json.loads(candidate_path.read_text(encoding="utf-8"))
    figure = candidate["pages"][0]["figures"][0]
    figure["caption_box_id"] = None
    figure["candidate_title_bbox"] = {"x": 0.3, "y": 0.2, "width": 0.1, "height": 0.2}
    _write_json(candidate_path, candidate)
    overrides["source_candidate_sha256"] = hashlib.sha256(candidate_path.read_bytes()).hexdigest()
    title = {
        **overrides["records"][1],
        "box_or_figure_id": "source-a-p0001-f01-title",
        "kind": "caption",
        "reading_order": None,
    }
    overrides["records"] = [title]
    overrides["page_reviews"] = []
    _write_json(path, overrides)
    result = convert_ppocrlabel_annotations(**kwargs)
    page = result["pages"]["source-a-p0001"]
    assert page["figures"][0]["title"] == "治絲圖"
    assert page["layout"]["regions"][-1]["region_id"] == "source-a-p0001-f01-title"
    assert page["layout"]["regions"][-1]["category"] == "caption"
    assert page["text_layers"]["corrected_text"] is None
    assert result["review_import"]["caption_ground_truth_verified"] == 1


def test_review_cannot_be_reused_after_label_changes(review_workspace) -> None:
    kwargs, overrides, path = review_workspace
    _write_json(path, overrides)
    source = kwargs["processed_root"] / "source-a" / "Label.txt"
    source.write_text(
        source.read_text(encoding="utf-8").replace("机器正文", "新文本"), encoding="utf-8"
    )
    with pytest.raises(ConversionError, match="label_sha256"):
        convert_ppocrlabel_annotations(**kwargs)


@pytest.mark.parametrize(
    "fault", ["model", "hash", "unknown", "duplicate", "bbox", "order", "timestamp"]
)
def test_invalid_reviews_leave_previous_output_untouched(review_workspace, fault: str) -> None:
    kwargs, overrides, path = review_workspace
    _write_json(path, overrides)
    convert_ppocrlabel_annotations(**kwargs)
    previous = kwargs["output_path"].read_bytes()
    if fault == "model":
        overrides["records"][0]["verification_state"] = "inferred"
    elif fault == "hash":
        overrides["source_candidate_sha256"] = "0" * 64
    elif fault == "unknown":
        overrides["records"][0]["box_or_figure_id"] = "missing"
    elif fault == "duplicate":
        overrides["records"].append(overrides["records"][0])
    elif fault == "bbox":
        overrides["records"][0]["bbox"]["width"] = float("nan")
    elif fault == "order":
        overrides["records"][1]["reading_order"] = 2
    elif fault == "timestamp":
        overrides["records"][0]["reviewed_at"] = "2026-10-02"
    _write_json(path, overrides)
    with pytest.raises(ConversionError):
        convert_ppocrlabel_annotations(**kwargs)
    assert kwargs["output_path"].read_bytes() == previous


@pytest.mark.parametrize("fault", ["ai_kind", "ai_origin", "record_origin", "pending_confirmation"])
def test_ai_review_is_never_human_truth_even_when_relabelled(review_workspace, fault: str) -> None:
    kwargs, overrides, path = review_workspace
    _write_json(path, overrides)
    convert_ppocrlabel_annotations(**kwargs)
    previous = kwargs["output_path"].read_bytes()
    if fault == "ai_kind":
        overrides["dataset_kind"] = "ai_assisted_review_overrides"
    elif fault == "ai_origin":
        overrides["review_origin"] = "ai_assisted"
    elif fault == "record_origin":
        overrides["records"][0]["review_origin"] = "ai_assisted"
    else:
        overrides["records"][0]["requires_human_confirmation"] = True
    _write_json(path, overrides)
    with pytest.raises(ConversionError):
        convert_ppocrlabel_annotations(**kwargs)
    assert kwargs["output_path"].read_bytes() == previous
