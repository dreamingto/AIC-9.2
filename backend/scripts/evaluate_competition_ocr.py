"""Evaluate original predictions only after the fixed scope has human truth.

Recognition is measured on retained text/caption/annotation boxes. It is not whole-page
OCR accuracy. Title recall measures raw detection localization, not historical
interpretation or title transcription. Incomplete scope returns null metrics.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
import tempfile
import unicodedata
from collections.abc import Sequence
from pathlib import Path
from typing import Any

from scripts.convert_ppocrlabel_annotations import (
    INVENTORY_PATH,
    PROJECT_ROOT,
    ConversionError,
    _read_json_object,
    _sha256,
    _write_json_atomic,
    convert_ppocrlabel_annotations,
)
from scripts.generate_historical_review_candidates import OUTPUT_PATH as CANDIDATE_PATH
from scripts.prepare_competition_scope import SCOPE_PATH, SELECTION_PATH, prepare_scope

DATA_ROOT = PROJECT_ROOT / "backend/data/real_pilot"
ANNOTATION_PATH = DATA_ROOT / "annotations.human-reviewed.json"
OVERRIDE_PATH = DATA_ROOT / "historical-review-overrides.json"
REPORT_PATH = DATA_ROOT / "competition_evaluation.json"
PIPELINE_VERSION = "competition-human-truth-evaluation-v1"
TOKEN_PATTERN = re.compile(r"[\u3400-\u9fff\U00020000-\U0003134f]|[A-Za-z0-9]+|[^\s]")


def normalize_text(text: str) -> str:
    return "".join(unicodedata.normalize("NFC", text).split())


def word_tokens(text: str) -> list[str]:
    """Explicit CJK character / Latin-word tokenization, not lexical Chinese WER."""
    return TOKEN_PATTERN.findall(unicodedata.normalize("NFC", text))


def edit_distance(reference: Sequence[str], prediction: Sequence[str]) -> int:
    previous = list(range(len(prediction) + 1))
    for i, expected in enumerate(reference, 1):
        current = [i]
        for j, actual in enumerate(prediction, 1):
            current.append(
                min(
                    current[-1] + 1,
                    previous[j] + 1,
                    previous[j - 1] + (expected != actual),
                )
            )
        previous = current
    return previous[-1]


def recognition_metrics(pairs: list[tuple[str, str]]) -> dict[str, Any]:
    characters = character_errors = tokens = token_errors = 0
    for truth, prediction in pairs:
        ref_chars, pred_chars = normalize_text(truth), normalize_text(prediction)
        ref_words, pred_words = word_tokens(truth), word_tokens(prediction)
        characters += len(ref_chars)
        character_errors += edit_distance(ref_chars, pred_chars)
        tokens += len(ref_words)
        token_errors += edit_distance(ref_words, pred_words)
    return {
        "cer": character_errors / characters if characters else None,
        "wer_cjk_character_latin_word": token_errors / tokens if tokens else None,
        "reference_characters": characters,
        "character_edit_distance": character_errors,
        "reference_tokens": tokens,
        "token_edit_distance": token_errors,
        "boxes": len(pairs),
    }


def bbox_iou(left: dict[str, Any], right: dict[str, Any]) -> float:
    x = max(left["x"], right["x"])
    y = max(left["y"], right["y"])
    r = min(left["x"] + left["width"], right["x"] + right["width"])
    b = min(left["y"] + left["height"], right["y"] + right["height"])
    intersection = max(0.0, r - x) * max(0.0, b - y)
    union = left["width"] * left["height"] + right["width"] * right["height"] - intersection
    return float(intersection / union) if union > 0 else 0.0


def title_localization_counts(
    truth: list[dict[str, Any]],
    predictions: list[dict[str, Any]],
    threshold: float = 0.5,
) -> tuple[int, int]:
    """Maximum one-to-one matching prevents a single box recalling two titles."""
    edges = [
        [j for j, box in enumerate(predictions) if bbox_iou(title, box) >= threshold]
        for title in truth
    ]
    assigned: dict[int, int] = {}

    def match(index: int, visited: set[int]) -> bool:
        for target in edges[index]:
            if target in visited:
                continue
            visited.add(target)
            if target not in assigned or match(assigned[target], visited):
                assigned[target] = index
                return True
        return False

    return sum(match(i, set()) for i in range(len(truth))), len(truth)


def _safe_file(project_root: Path, relative: str) -> Path:
    target = (project_root / relative).resolve()
    if project_root.resolve() not in target.parents or not target.is_file():
        raise ConversionError("evaluation input is missing or outside the project")
    return target


def _validate_scope(
    *,
    scope_path: Path,
    selection_path: Path,
    candidate_path: Path,
    inventory_path: Path,
    project_root: Path,
) -> dict[str, Any]:
    scope = _read_json_object(scope_path)
    with tempfile.TemporaryDirectory(prefix="jitu-scope-check-") as directory:
        expected = prepare_scope(
            selection_path=selection_path,
            candidate_path=candidate_path,
            inventory_path=inventory_path,
            project_root=project_root,
            output_path=Path(directory) / "scope.json",
        )
    if scope != expected:
        raise ConversionError("scope differs from the fixed selection/current input hashes")
    for page in scope["pages"]:
        pdf = _safe_file(project_root, "backend/data/assets/real_pilot_v1/" + page["pdf_filename"])
        if _sha256(pdf) != page["pdf_sha256"]:
            raise ConversionError("source PDF hash mismatch")
    return scope


def _validated_truth(
    *,
    annotation_path: Path,
    override_path: Path,
    candidate_path: Path,
    inventory_path: Path,
    project_root: Path,
    source_id: str,
) -> dict[str, Any]:
    annotation = _read_json_object(annotation_path)
    if (
        annotation.get("source_id") != source_id
        or annotation.get("dataset_kind") != "real_pilot_ppocrlabel_annotations"
        or not isinstance(annotation.get("review_import"), dict)
    ):
        raise ConversionError("annotations must come from explicit human review import")
    if annotation["review_import"].get("override_sha256") != _sha256(override_path):
        raise ConversionError("human confirmation export hash mismatch")
    try:
        operator = next(iter(annotation["pages"].values()))["provenance"]["layout_reviewer"]
    except (KeyError, StopIteration, TypeError) as exc:
        raise ConversionError("human annotation lacks accepted layout provenance") from exc
    if not isinstance(operator, str) or not operator:
        raise ConversionError("human annotation lacks layout reviewer")
    with tempfile.TemporaryDirectory(prefix="jitu-truth-check-") as directory:
        expected = convert_ppocrlabel_annotations(
            source_id=source_id,
            inventory_path=inventory_path,
            output_path=Path(directory) / "revalidated.json",
            project_root=project_root,
            processed_root=project_root / "backend/data/processed/real_pilot_v1",
            reviewer=operator,
            accept_file_state=True,
            review_override_path=override_path,
            review_candidate_path=candidate_path,
        )
    if expected != annotation:
        raise ConversionError("human annotations differ from the original confirmation export")
    return annotation


def _readiness(scope: dict[str, Any], annotation: dict[str, Any] | None) -> list[dict[str, Any]]:
    readiness = []
    for selected in scope["pages"]:
        page_id = selected["page_id"]
        page = annotation.get("pages", {}).get(page_id, {}) if annotation else {}
        regions = {
            r.get("box_id") or r["region_id"]: r for r in page.get("layout", {}).get("regions", [])
        }
        missing = [
            item_id
            for item_id in selected["box_ids"] + selected["missing_caption_ids"]
            if regions.get(item_id, {}).get("verification_state") != "verified"
        ]
        order = page.get("layout", {}).get("reading_order_review", {}).get("confirmed") is True
        inventory = page.get("layout", {}).get("content_inventory_review", {})
        complete = (
            inventory.get("confirmed") is True
            and inventory.get("text_complete") is True
            and inventory.get("captions_complete") is True
        )
        readiness.append(
            {
                "page_id": page_id,
                "pending_items": missing,
                "reading_order_confirmed": order,
                "content_inventory_confirmed": complete,
                "ready": not missing and order and complete,
            }
        )
    return readiness


def _metrics(
    scope: dict[str, Any], annotation: dict[str, Any], candidate: dict[str, Any]
) -> dict[str, Any]:
    candidate_pages = {p["page_id"]: p for p in candidate["pages"]}
    raw_pairs: list[tuple[str, str]] = []
    server_pairs: list[tuple[str, str]] = []
    raw_missing = server_missing = title_matched = title_total = supplemental_count = 0
    for selected in scope["pages"]:
        page_id = selected["page_id"]
        page, original = annotation["pages"][page_id], candidate_pages[page_id]
        corrected = {line["line_id"]: line for line in page["text_layers"]["corrected_lines"]}
        region_categories = {
            r.get("box_id") or r["region_id"]: r["category"] for r in page["layout"]["regions"]
        }
        raw = page["ocr"]["lines"]
        for box in original["boxes"]:
            if box.get("original_box_index") is None:
                supplemental_count += 1
                continue  # Added regions are not retained original OCR predictions.
            truth = corrected.get(box["box_id"])
            if truth is None or region_categories[box["box_id"]] not in {
                "text",
                "caption",
                "annotation",
            }:
                continue  # Human-classified non-text regions are outside recognition scope.
            matches = [line for line in raw if line["polygon"] == box["polygon"]]
            if len(matches) > 1:
                raise ConversionError("ambiguous retained-box match in original raw OCR")
            raw_missing += int(not matches)
            raw_pairs.append((truth["text"], matches[0]["text"] if matches else ""))
            server = box.get("server_ocr")
            if not isinstance(server, dict) or not isinstance(server.get("text"), str):
                server_missing += 1
            else:
                server_pairs.append((truth["text"], server["text"]))
        inventory = page["layout"]["content_inventory_review"]
        regions = {r.get("box_id") or r["region_id"]: r for r in page["layout"]["regions"]}
        titles = [regions[title_id]["bbox"] for title_id in inventory["caption_ids"]]
        raw_bboxes = [
            {
                "x": line["bbox"][0] / page["width"],
                "y": line["bbox"][1] / page["height"],
                "width": (line["bbox"][2] - line["bbox"][0]) / page["width"],
                "height": (line["bbox"][3] - line["bbox"][1]) / page["height"],
            }
            for line in raw
        ]
        matched, total = title_localization_counts(titles, raw_bboxes)
        title_matched += matched
        title_total += total
    return {
        "raw_retained_box_recognition": {
            **recognition_metrics(raw_pairs),
            "missing_raw_boxes": raw_missing,
        },
        "server_retained_box_recognition": recognition_metrics(server_pairs)
        if not server_missing
        else None,
        "missing_server_predictions": server_missing,
        "supplemental_regions_excluded_from_retained_recognition": supplemental_count,
        "raw_title_localization": {
            "recall": title_matched / title_total if title_total else None,
            "matched_titles": title_matched,
            "ground_truth_titles": title_total,
            "iou_threshold": 0.5,
            "precision": None,
            "precision_status": "not_defined_for_unclassified_all_text_detections",
        },
        "whole_page_cer": None,
        "whole_page_status": "not_evaluated_requires_independent_complete_text_and_order_protocol",
    }


def verify_frozen_snapshot(target: Path, *, verify_id: bool = True) -> dict[str, Any]:
    manifest = _read_json_object(target / "manifest.json")
    if (
        manifest.get("dataset_kind") != "frozen_human_reviewed_ocr_subset"
        or manifest.get("schema_version") != "1.0"
        or not isinstance(manifest.get("files"), dict)
        or not manifest["files"]
    ):
        raise ConversionError("invalid frozen manifest")
    fingerprint = hashlib.sha256(json.dumps(manifest, sort_keys=True).encode()).hexdigest()[:16]
    if verify_id and not target.name.endswith("-core-" + fingerprint):
        raise ConversionError("frozen manifest content ID mismatch")
    for name, digest in manifest["files"].items():
        file = _safe_file(target, name)
        if _sha256(file) != digest:
            raise ConversionError(f"frozen input hash mismatch: {name}")
    return manifest


def _freeze(
    *,
    scope: dict[str, Any],
    report: dict[str, Any],
    project_root: Path,
    scope_path: Path,
    candidate_path: Path,
    annotation_path: Path,
    override_path: Path,
    inventory_path: Path,
    freeze_root: Path,
) -> Path:
    source_dir = project_root / "backend/data/processed/real_pilot_v1" / scope["source_id"]
    files = {
        "scope.json": scope_path,
        "candidates.json": candidate_path,
        "annotations.json": annotation_path,
        "human-overrides.json": override_path,
        "inventory.json": inventory_path,
        "Cache.cach": source_dir / "Cache.cach",
        "Label.txt": source_dir / "Label.txt",
        "fileState.txt": source_dir / "fileState.txt",
    }
    for page in scope["pages"]:
        files[f"images/{page['page_id']}.png"] = _safe_file(project_root, page["image_path"])
        files[f"pdf/{page['pdf_filename']}"] = _safe_file(
            project_root,
            "backend/data/assets/real_pilot_v1/" + page["pdf_filename"],
        )
    reference = project_root / "backend/data/real_pilot/naifu_wikisource_reference.json"
    if scope["input_hashes"].get("reference_sha256"):
        files["reference.json"] = reference
    manifest = {
        "schema_version": "1.0",
        "dataset_kind": "frozen_human_reviewed_ocr_subset",
        "pipeline_version": PIPELINE_VERSION,
        "files": {name: _sha256(path) for name, path in files.items()},
        "evaluation": report,
    }
    fingerprint = hashlib.sha256(json.dumps(manifest, sort_keys=True).encode()).hexdigest()[:16]
    target = freeze_root / f"{scope['source_id']}-core-{fingerprint}"
    freeze_root.mkdir(parents=True, exist_ok=True)
    if target.exists():
        if verify_frozen_snapshot(target) != manifest:
            raise ConversionError("frozen snapshot ID collision")
        return target
    with tempfile.TemporaryDirectory(prefix="core-freeze-", dir=freeze_root) as directory:
        staging = Path(directory)
        for name, original in files.items():
            output = staging / name
            output.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(original, output)
        _write_json_atomic(staging / "manifest.json", manifest)
        verify_frozen_snapshot(staging, verify_id=False)
        # The fully verified directory becomes immutable by convention; never overwrite it.
        staging.rename(target)
    return target


def evaluate_scope(
    *,
    scope_path: Path = SCOPE_PATH,
    selection_path: Path = SELECTION_PATH,
    candidate_path: Path = CANDIDATE_PATH,
    inventory_path: Path = INVENTORY_PATH,
    annotation_path: Path = ANNOTATION_PATH,
    override_path: Path = OVERRIDE_PATH,
    report_path: Path = REPORT_PATH,
    project_root: Path = PROJECT_ROOT,
    freeze: bool = False,
    freeze_root: Path = DATA_ROOT / "frozen",
) -> dict[str, Any]:
    scope = _validate_scope(
        scope_path=scope_path,
        selection_path=selection_path,
        candidate_path=candidate_path,
        inventory_path=inventory_path,
        project_root=project_root,
    )
    annotation = (
        _validated_truth(
            annotation_path=annotation_path,
            override_path=override_path,
            candidate_path=candidate_path,
            inventory_path=inventory_path,
            project_root=project_root,
            source_id=scope["source_id"],
        )
        if annotation_path.is_file()
        else None
    )
    readiness = _readiness(scope, annotation)
    ready = all(p["ready"] for p in readiness)
    report: dict[str, Any] = {
        "schema_version": "1.0",
        "dataset_kind": "competition_ocr_evaluation_report",
        "pipeline_version": PIPELINE_VERSION,
        "source_id": scope["source_id"],
        "scope_sha256": _sha256(scope_path),
        "evaluation_status": "evaluated" if ready else "not_evaluated",
        "sample_statistics": scope["statistics"],
        "protocol": scope["metric_protocol"],
        "readiness": readiness,
        "metrics": _metrics(scope, annotation, _read_json_object(candidate_path))
        if ready and annotation
        else None,
        "blockers": []
        if ready
        else ["固定范围尚缺逐框人工确认、阅读顺序或完整文字/图题清单；禁止输出研究分数。"],
    }
    if freeze:
        if not ready:
            report["freeze_status"] = "blocked_pending_human_truth"
        else:
            report["snapshot_path"] = str(
                _freeze(
                    scope=scope,
                    report=dict(report),
                    project_root=project_root,
                    scope_path=scope_path,
                    candidate_path=candidate_path,
                    annotation_path=annotation_path,
                    override_path=override_path,
                    inventory_path=inventory_path,
                    freeze_root=freeze_root,
                )
            )
            report["freeze_status"] = "frozen_verified"
    _write_json_atomic(report_path, report)
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--freeze", action="store_true")
    parser.add_argument("--report", type=Path, default=REPORT_PATH)
    parser.add_argument("--verify-snapshot", type=Path)
    parser.add_argument("--candidate", type=Path, default=CANDIDATE_PATH)
    parser.add_argument("--scope", type=Path, default=SCOPE_PATH)
    parser.add_argument("--annotation", type=Path, default=ANNOTATION_PATH)
    parser.add_argument("--overrides", type=Path, default=OVERRIDE_PATH)
    args = parser.parse_args()
    try:
        if args.verify_snapshot:
            verify_frozen_snapshot(args.verify_snapshot.resolve())
            print("frozen snapshot hashes verified")
            return 0
        report = evaluate_scope(
            freeze=args.freeze,
            report_path=args.report,
            candidate_path=args.candidate,
            scope_path=args.scope,
            annotation_path=args.annotation,
            override_path=args.overrides,
        )
    except (ConversionError, OSError, KeyError, TypeError) as exc:
        parser.error(str(exc))
    print(
        json.dumps(
            {
                "evaluation_status": report["evaluation_status"],
                "ready_pages": sum(p["ready"] for p in report["readiness"]),
                "selected_pages": len(report["readiness"]),
                "metrics": report["metrics"],
                "blockers": report["blockers"],
                "freeze_status": report.get("freeze_status"),
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0 if report["evaluation_status"] == "evaluated" else 2


if __name__ == "__main__":
    raise SystemExit(main())
