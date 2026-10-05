from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

import pytest
from PIL import Image

from scripts.convert_ppocrlabel_annotations import ConversionError, convert_ppocrlabel_annotations
from scripts.evaluate_competition_ocr import (
    edit_distance,
    evaluate_scope,
    recognition_metrics,
    title_localization_counts,
    verify_frozen_snapshot,
    word_tokens,
)
from scripts.prepare_competition_scope import prepare_scope
from scripts.prepare_historical_review_revision import prepare_revision


def write_json(path: Path, data: dict[str, Any]) -> None:
    path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


@pytest.fixture
def core_workspace(tmp_path: Path) -> dict[str, Any]:
    source_id = "sample-source"
    data = tmp_path / "backend/data/real_pilot"
    processed = tmp_path / "backend/data/processed/real_pilot_v1"
    source = processed / source_id
    assets = tmp_path / "backend/data/assets/real_pilot_v1"
    for directory in (data, source, assets):
        directory.mkdir(parents=True)
    pdf = assets / "sample.pdf"
    pdf.write_bytes(b"%PDF-1.6\nSynthetic test input, never research data")
    inventory_pages, candidates, records, page_reviews, inventory_reviews = [], [], [], [], []
    cache_lines = []
    for n in (1, 2):
        page_id = f"{source_id}-p{n:04d}"
        image = source / f"page-{n:04d}.png"
        Image.new("RGB", (100, 100), "white").save(image)
        polygon = [[10, 10], [90, 10], [90, 30], [10, 30]]
        box_id = f"{page_id}-b001"
        bbox = {"x": 0.1, "y": 0.1, "width": 0.8, "height": 0.2}
        cache_lines.append(
            f"{source_id}/{image.name}\t"
            + json.dumps(
                [{"transcription": "冶絲圖", "points": polygon, "difficult": False}],
                ensure_ascii=False,
            )
        )
        inventory_pages.append(
            {
                "page_id": page_id,
                "source_id": source_id,
                "image_path": image.relative_to(tmp_path).as_posix(),
                "sha256": digest(image),
                "width": 100,
                "height": 100,
                "provenance": {"pdf_filename": pdf.name, "pdf_sha256": digest(pdf)},
            }
        )
        candidates.append(
            {
                "page_id": page_id,
                "image_path": image.relative_to(tmp_path).as_posix(),
                "image_sha256": digest(image),
                "boxes": [
                    {
                        "box_id": box_id,
                        "original_box_index": 1,
                        "reading_order": 1,
                        "raw_text": "冶絲圖",
                        "polygon": polygon,
                        "bbox": bbox,
                        "verification_state": "inferred",
                        "server_ocr": {"text": "治絲圖", "confidence": 0.9},
                    }
                ],
                "figures": [],
            }
        )
        review = {
            "confirmed": True,
            "reviewer": "test-reviewer",
            "reviewed_at": "2026-10-03T10:00:00+08:00",
        }
        records.append(
            {
                **review,
                "box_or_figure_id": box_id,
                "page_id": page_id,
                "kind": "box",
                "corrected_text": "治絲圖",
                "category": "caption",
                "role": "figure_title",
                "bbox": bbox,
                "reading_order": 1,
                "verification_state": "verified",
                "evidence": "scan_level_human_review",
            }
        )
        page_reviews.append({**review, "page_id": page_id})
        inventory_reviews.append(
            {
                **review,
                "page_id": page_id,
                "text_complete": True,
                "captions_complete": True,
                "caption_ids": [box_id],
            }
        )
    for name in ("Label.txt", "Cache.cach"):
        (source / name).write_text("\n".join(cache_lines) + "\n", encoding="utf-8")
    (source / "fileState.txt").write_text(
        "\n".join(f"{source_id}/page-{n:04d}.png\t1" for n in (1, 2)) + "\n",
        encoding="utf-8",
    )
    inventory_path = data / "inventory.json"
    write_json(
        inventory_path,
        {
            "dataset_kind": "real_pilot_page_inventory",
            "evaluation_status": "not_evaluated",
            "pages": inventory_pages,
        },
    )
    hashes = {
        "inventory_sha256": digest(inventory_path),
        "label_sha256": digest(source / "Label.txt"),
    }
    candidate_path = data / "candidates.json"
    write_json(
        candidate_path,
        {
            "dataset_kind": "real_pilot_model_assisted_review_candidates",
            "source_id": source_id,
            "evaluation_status": "not_evaluated",
            "input_hashes": hashes,
            "pages": candidates,
        },
    )
    selection_path = data / "selection.json"
    write_json(
        selection_path,
        {
            "dataset_kind": "competition_review_selection",
            "source_id": source_id,
            "page_numbers": [1, 2],
        },
    )
    scope_path = data / "scope.json"
    prepare_scope(
        selection_path=selection_path,
        candidate_path=candidate_path,
        inventory_path=inventory_path,
        project_root=tmp_path,
        output_path=scope_path,
    )
    override_path = data / "overrides.json"
    overrides = {
        "dataset_kind": "human_review_overrides",
        "schema_version": "1.0",
        "source_id": source_id,
        "source_candidate_sha256": digest(candidate_path),
        "input_hashes": hashes,
        "records": records,
        "page_reviews": page_reviews,
        "page_inventory_reviews": inventory_reviews,
    }
    write_json(override_path, overrides)
    annotation_path = data / "human.json"
    conversion_args = {
        "source_id": source_id,
        "inventory_path": inventory_path,
        "output_path": annotation_path,
        "project_root": tmp_path,
        "processed_root": processed,
        "reviewer": "test-reviewer",
        "accept_file_state": True,
        "review_override_path": override_path,
        "review_candidate_path": candidate_path,
    }
    return {
        "args": {
            "scope_path": scope_path,
            "selection_path": selection_path,
            "candidate_path": candidate_path,
            "inventory_path": inventory_path,
            "annotation_path": annotation_path,
            "override_path": override_path,
            "report_path": data / "report.json",
            "project_root": tmp_path,
            "freeze_root": data / "frozen",
        },
        "conversion_args": conversion_args,
        "overrides": overrides,
        "source": source,
        "pdf": pdf,
    }


def accept_truth(workspace: dict[str, Any]) -> None:
    write_json(workspace["args"]["override_path"], workspace["overrides"])
    convert_ppocrlabel_annotations(**workspace["conversion_args"])


@pytest.fixture
def revision_workspace(core_workspace) -> dict[str, Any]:
    args = core_workspace["args"]
    data = args["candidate_path"].parent
    ai = json.loads(json.dumps(core_workspace["overrides"]))
    ai.update({"dataset_kind": "ai_assisted_review_overrides", "review_origin": "ai_assisted"})
    for record in ai["records"]:
        record.update(
            {
                "review_origin": "ai_assisted",
                "verification_state": "inferred",
                "evidence": "scan_level_ai_review",
                "requires_human_confirmation": True,
                "review_note": "isolated test scan suggestion, not research truth",
            }
        )
    ai_path = data / "ai.json"
    write_json(ai_path, ai)
    proposal = {
        "dataset_kind": "ai_supplemental_region_proposals",
        "revision_id": "test-v2",
        "source_id": "sample-source",
        "source_candidate_sha256": digest(args["candidate_path"]),
        "verification_state": "inferred",
        "requires_human_confirmation": True,
        "regions": [
            {
                "page_id": "sample-source-p0001",
                "box_id": "sample-source-p0001-b002",
                "bbox": {"x": 0.1, "y": 0.6, "width": 0.2, "height": 0.2},
                "category": "text",
                "role": "body_text",
                "insert_after": "sample-source-p0001-b001",
                "note": "new diagnostic region, raw prediction absent",
            }
        ],
    }
    proposal_path = data / "supplements.json"
    write_json(proposal_path, proposal)
    return {
        "core": core_workspace,
        "ai": ai,
        "proposal": proposal,
        "args": {
            "proposal_path": proposal_path,
            "ai_path": ai_path,
            "candidate_path": args["candidate_path"],
            "selection_path": args["selection_path"],
            "inventory_path": args["inventory_path"],
            "output_root": data / "revisions",
            "project_root": args["project_root"],
        },
    }


def test_supplement_revision_preserves_raw_hashes_and_separates_human_seeds(
    revision_workspace,
) -> None:
    workspace = revision_workspace
    core = workspace["core"]
    originals = [
        workspace["args"]["candidate_path"],
        workspace["args"]["ai_path"],
        core["source"] / "Label.txt",
        core["source"] / "Cache.cach",
        core["args"]["scope_path"],
    ]
    old_bytes = {p: p.read_bytes() for p in originals}
    report = prepare_revision(**workspace["args"])
    directory = Path(report["revision_path"])
    candidate = json.loads((directory / "annotations.candidates.json").read_text(encoding="utf-8"))
    addition = candidate["pages"][0]["boxes"][1]
    assert addition["raw_text"] is None
    assert addition["original_box_index"] is None
    assert addition["server_ocr"] is None
    assert [b["reading_order"] for b in candidate["pages"][0]["boxes"]] == [1, 2]
    assert report["scope_statistics"]["retained_boxes"] == 2
    assert report["scope_statistics"]["supplemental_region_candidates"] == 1
    assert report["migrated_prior_suggestions"] == 2
    human = json.loads((directory / "model_review_queue.json").read_text(encoding="utf-8"))
    ai = json.loads((directory / "model_review_queue.ai.json").read_text(encoding="utf-8"))
    assert human["ai_review_seed"] == []
    assert len(ai["ai_review_seed"]) == 3
    assert all(r["requires_human_confirmation"] for r in ai["ai_review_seed"])
    assert all(r["verification_state"] == "inferred" for r in ai["ai_review_seed"])
    assert all(p.read_bytes() == before for p, before in old_bytes.items())
    files = {p: p.read_bytes() for p in directory.rglob("*") if p.is_file()}
    assert prepare_revision(**workspace["args"]) == report
    assert all(p.read_bytes() == before for p, before in files.items())


@pytest.mark.parametrize("invalid", ["hash", "human", "nan", "duplicate", "anchor"])
def test_revision_rejects_stale_or_invalid_supplements_before_writing(
    revision_workspace, invalid: str
) -> None:
    workspace = revision_workspace
    if invalid == "hash":
        workspace["ai"]["source_candidate_sha256"] = "0" * 64
    elif invalid == "human":
        workspace["ai"]["records"][0]["review_origin"] = "human"
    elif invalid == "nan":
        workspace["proposal"]["regions"][0]["bbox"]["x"] = float("nan")
    elif invalid == "duplicate":
        workspace["proposal"]["regions"][0]["box_id"] = "sample-source-p0001-b001"
    else:
        workspace["proposal"]["regions"][0]["insert_after"] = "missing-anchor"
    write_json(workspace["args"]["ai_path"], workspace["ai"])
    write_json(workspace["args"]["proposal_path"], workspace["proposal"])
    with pytest.raises(ConversionError):
        prepare_revision(**workspace["args"])
    assert not workspace["args"]["output_root"].exists()


def test_supplement_is_required_for_inventory_and_never_fabricates_raw_metrics(
    revision_workspace,
) -> None:
    workspace = revision_workspace
    core = workspace["core"]
    report = prepare_revision(**workspace["args"])
    directory = Path(report["revision_path"])
    core["args"].update(
        {
            "candidate_path": directory / "annotations.candidates.json",
            "scope_path": directory / "competition_scope.json",
        }
    )
    core["conversion_args"]["review_candidate_path"] = core["args"]["candidate_path"]
    core["overrides"]["source_candidate_sha256"] = digest(core["args"]["candidate_path"])
    with pytest.raises(ConversionError, match="unreviewed text/title"):
        accept_truth(core)
    core["overrides"]["records"].append(
        {
            **core["overrides"]["records"][0],
            "box_or_figure_id": "sample-source-p0001-b002",
            "bbox": workspace["proposal"]["regions"][0]["bbox"],
            "reading_order": 2,
            "category": "text",
            "role": "body_text",
            "corrected_text": "补框文字",
        }
    )
    accept_truth(core)
    annotation = json.loads(core["args"]["annotation_path"].read_text(encoding="utf-8"))
    page = annotation["pages"]["sample-source-p0001"]
    assert page["text_layers"]["raw_ocr"] == "冶絲圖"
    assert len(page["ocr"]["lines"]) == 1
    assert page["text_layers"]["corrected_text"] == "治絲圖\n补框文字"
    assert page["text_layers"]["change_log"][-1]["from"] is None
    result = evaluate_scope(**core["args"], freeze=True)
    assert result["freeze_status"] == "frozen_verified"
    assert result["metrics"]["raw_retained_box_recognition"]["boxes"] == 2
    assert result["metrics"]["raw_retained_box_recognition"]["cer"] == pytest.approx(1 / 3)
    assert result["metrics"]["supplemental_regions_excluded_from_retained_recognition"] == 1


def test_revision_keeps_prior_ai_order_instead_of_reverting_to_model_order(
    revision_workspace,
) -> None:
    workspace = revision_workspace
    core = workspace["core"]
    candidate = json.loads(workspace["args"]["candidate_path"].read_text(encoding="utf-8"))
    first = candidate["pages"][0]["boxes"][0]
    second = {
        **first,
        "box_id": "sample-source-p0001-b002",
        "original_box_index": 2,
        "reading_order": 2,
        "bbox": {"x": 0.5, "y": 0.1, "width": 0.3, "height": 0.2},
        "polygon": [[50, 10], [80, 10], [80, 30], [50, 30]],
    }
    candidate["pages"][0]["boxes"].append(second)
    for name in ("Cache.cach", "Label.txt"):
        path = core["source"] / name
        rows = path.read_text(encoding="utf-8").splitlines()
        key, payload = rows[0].split("\t")
        boxes = json.loads(payload)
        boxes.append({**boxes[0], "points": second["polygon"]})
        rows[0] = key + "\t" + json.dumps(boxes, ensure_ascii=False)
        path.write_text("\n".join(rows) + "\n", encoding="utf-8")
    candidate["input_hashes"]["label_sha256"] = digest(core["source"] / "Label.txt")
    write_json(workspace["args"]["candidate_path"], candidate)
    workspace["ai"]["records"][0]["reading_order"] = 2
    workspace["ai"]["records"].append(
        {
            **workspace["ai"]["records"][0],
            "box_or_figure_id": second["box_id"],
            "reading_order": 1,
            "bbox": second["bbox"],
        }
    )
    workspace["ai"]["input_hashes"] = candidate["input_hashes"]
    workspace["ai"]["source_candidate_sha256"] = digest(workspace["args"]["candidate_path"])
    workspace["proposal"]["source_candidate_sha256"] = workspace["ai"]["source_candidate_sha256"]
    workspace["proposal"]["regions"][0]["box_id"] = "sample-source-p0001-b003"
    write_json(workspace["args"]["ai_path"], workspace["ai"])
    write_json(workspace["args"]["proposal_path"], workspace["proposal"])
    report = prepare_revision(**workspace["args"])
    path = Path(report["revision_path"]) / "annotations.candidates.json"
    revised = json.loads(path.read_text(encoding="utf-8"))
    assert [b["box_id"] for b in revised["pages"][0]["boxes"]] == [
        "sample-source-p0001-b002",
        "sample-source-p0001-b001",
        "sample-source-p0001-b003",
    ]
    assert report["reading_order_rechecks"] == 0


def test_no_human_truth_never_emits_scores_or_snapshot(core_workspace) -> None:
    result = evaluate_scope(**core_workspace["args"], freeze=True)
    assert result["evaluation_status"] == "not_evaluated"
    assert result["metrics"] is None
    assert result["freeze_status"] == "blocked_pending_human_truth"
    assert all(not p["ready"] for p in result["readiness"])
    assert not core_workspace["args"]["freeze_root"].exists()


def test_fixed_scope_does_not_score_only_easy_confirmed_pages(core_workspace) -> None:
    core_workspace["overrides"]["records"] = core_workspace["overrides"]["records"][:1]
    core_workspace["overrides"]["page_reviews"] = core_workspace["overrides"]["page_reviews"][:1]
    core_workspace["overrides"]["page_inventory_reviews"] = core_workspace["overrides"][
        "page_inventory_reviews"
    ][:1]
    accept_truth(core_workspace)
    result = evaluate_scope(**core_workspace["args"])
    assert [p["ready"] for p in result["readiness"]] == [True, False]
    assert result["metrics"] is None


def test_corrected_truth_is_compared_to_unchanged_raw_predictions(core_workspace) -> None:
    accept_truth(core_workspace)
    result = evaluate_scope(**core_workspace["args"])
    metrics = result["metrics"]
    assert result["evaluation_status"] == "evaluated"
    assert metrics["raw_retained_box_recognition"]["cer"] == pytest.approx(1 / 3)
    assert metrics["raw_retained_box_recognition"]["character_edit_distance"] == 2
    assert metrics["server_retained_box_recognition"]["cer"] == 0
    assert metrics["raw_title_localization"]["recall"] == 1
    assert metrics["whole_page_cer"] is None


def test_transcription_and_order_do_not_imply_complete_title_inventory(core_workspace) -> None:
    core_workspace["overrides"]["page_inventory_reviews"] = []
    accept_truth(core_workspace)
    result = evaluate_scope(**core_workspace["args"])
    assert all(p["reading_order_confirmed"] for p in result["readiness"])
    assert result["metrics"] is None


@pytest.mark.parametrize("name", ["Label.txt", "Cache.cach", "page-0001.png", "pdf"])
def test_stale_input_is_rejected_before_scoring(core_workspace, name) -> None:
    accept_truth(core_workspace)
    path = core_workspace["pdf"] if name == "pdf" else core_workspace["source"] / name
    path.write_bytes(path.read_bytes() + b" changed")
    with pytest.raises(ConversionError):
        evaluate_scope(**core_workspace["args"])


def test_editing_imported_truth_without_human_export_is_rejected(core_workspace) -> None:
    accept_truth(core_workspace)
    path = core_workspace["args"]["annotation_path"]
    payload = json.loads(path.read_text(encoding="utf-8"))
    payload["pages"]["sample-source-p0001"]["text_layers"]["corrected_lines"][0]["text"] = "作弊"
    write_json(path, payload)
    with pytest.raises(ConversionError, match="confirmation export"):
        evaluate_scope(**core_workspace["args"])


def test_inventory_cannot_hide_unreviewed_title_or_forge_caption_ids(core_workspace) -> None:
    core_workspace["overrides"]["page_inventory_reviews"][0]["caption_ids"] = []
    with pytest.raises(ConversionError, match="caption_ids"):
        accept_truth(core_workspace)


def test_snapshot_copies_inputs_reuses_id_and_detects_tampering(core_workspace) -> None:
    accept_truth(core_workspace)
    first = evaluate_scope(**core_workspace["args"], freeze=True)
    second = evaluate_scope(**core_workspace["args"], freeze=True)
    assert first["snapshot_path"] == second["snapshot_path"]
    target = Path(first["snapshot_path"])
    manifest = verify_frozen_snapshot(target)
    assert len([name for name in manifest["files"] if name.startswith("images/")]) == 2
    (target / "Label.txt").write_bytes(b"tampered")
    with pytest.raises(ConversionError, match="hash mismatch"):
        evaluate_scope(**core_workspace["args"], freeze=True)


def test_error_rates_are_micro_averaged_and_may_exceed_one() -> None:
    metrics = recognition_metrics([("中", "中國中國"), ("文書", "文書")])
    assert metrics["cer"] == 1
    assert recognition_metrics([("中", "中國中國")])["cer"] == 3
    assert recognition_metrics([])["cer"] is None
    assert edit_distance("", "ab") == 2


def test_chinese_word_error_token_protocol_is_explicit() -> None:
    assert word_tokens("治絲圖 PP-OCR 5") == ["治", "絲", "圖", "PP", "-", "OCR", "5"]
    assert recognition_metrics([("治 絲圖", "治絲圖")])["cer"] == 0
    assert recognition_metrics([("絲", "丝")])["cer"] == 1


def test_title_recall_cannot_reuse_one_detection_for_two_titles() -> None:
    box = {"x": 0.1, "y": 0.1, "width": 0.2, "height": 0.2}
    assert title_localization_counts([box, box], [box]) == (1, 2)
    assert title_localization_counts([], [box]) == (0, 0)


def test_undetected_human_added_title_remains_in_recall_denominator(core_workspace) -> None:
    args = core_workspace["args"]
    candidates = json.loads(args["candidate_path"].read_text(encoding="utf-8"))
    page_id = "sample-source-p0001"
    title_id = page_id + "-f01-title"
    bbox = {"x": 0.1, "y": 0.6, "width": 0.3, "height": 0.2}
    candidates["pages"][0]["figures"] = [
        {
            "figure_id": page_id + "-f01",
            "caption_box_id": None,
            "bbox": bbox,
            "candidate_title_bbox": bbox,
            "verification_state": "inferred",
        }
    ]
    write_json(args["candidate_path"], candidates)
    overrides = core_workspace["overrides"]
    overrides["source_candidate_sha256"] = digest(args["candidate_path"])
    overrides["records"].append(
        {
            **overrides["records"][0],
            "box_or_figure_id": title_id,
            "kind": "caption",
            "bbox": bbox,
            "reading_order": None,
        }
    )
    overrides["page_inventory_reviews"][0]["caption_ids"].append(title_id)
    prepare_scope(
        selection_path=args["selection_path"],
        candidate_path=args["candidate_path"],
        inventory_path=args["inventory_path"],
        project_root=args["project_root"],
        output_path=args["scope_path"],
    )
    accept_truth(core_workspace)
    result = evaluate_scope(**args)
    assert result["metrics"]["raw_title_localization"]["ground_truth_titles"] == 3
    assert result["metrics"]["raw_title_localization"]["recall"] == pytest.approx(2 / 3)


def test_frozen_manifest_cannot_drop_failed_file_checks(core_workspace) -> None:
    accept_truth(core_workspace)
    result = evaluate_scope(**core_workspace["args"], freeze=True)
    target = Path(result["snapshot_path"])
    manifest = json.loads((target / "manifest.json").read_text(encoding="utf-8"))
    del manifest["files"]["Cache.cach"]
    write_json(target / "manifest.json", manifest)
    with pytest.raises(ConversionError, match="content ID"):
        verify_frozen_snapshot(target)


def test_scope_preparation_is_deterministic_and_rejects_missing_pages(core_workspace) -> None:
    args = core_workspace["args"]
    path = args["scope_path"]
    before = path.read_bytes()
    prepare_scope(
        selection_path=args["selection_path"],
        candidate_path=args["candidate_path"],
        inventory_path=args["inventory_path"],
        project_root=args["project_root"],
        output_path=path,
    )
    assert path.read_bytes() == before
    selection = json.loads(args["selection_path"].read_text(encoding="utf-8"))
    selection["page_numbers"] = [3]
    write_json(args["selection_path"], selection)
    with pytest.raises(ConversionError, match="selected page is missing"):
        prepare_scope(
            selection_path=args["selection_path"],
            candidate_path=args["candidate_path"],
            inventory_path=args["inventory_path"],
            project_root=args["project_root"],
            output_path=path,
        )
    assert path.read_bytes() == before
