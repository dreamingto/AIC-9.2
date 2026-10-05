"""Audit PPOCRLabel manual work and gate real-pilot OCR evaluation.

The audit deliberately separates layout/box review from transcription review.
It can calculate CER and a documented mixed-CJK token error rate only after an
operator explicitly accepts transcription review and all quality gates pass.
Figure-title recall remains unavailable until caption regions are annotated.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from collections.abc import Sequence
from pathlib import Path
from typing import Any

from scripts.convert_ppocrlabel_annotations import (
    DEFAULT_SOURCE_ID,
    INVENTORY_PATH,
    PROCESSED_ROOT,
    PROJECT_ROOT,
    ConversionError,
    LabelBox,
    PageRecord,
    _load_inventory,
    _parse_annotation_file,
    _parse_file_state,
    _resolve_source_dir,
    _write_json_atomic,
)

OUTPUT_PATH = (
    PROJECT_ROOT / "backend" / "data" / "real_pilot" / "ppocrlabel_quality_audit.json"
)
PIPELINE_VERSION = "ppocrlabel-quality-audit-v1"
REPLACEMENT_CHARACTER = "\ufffd"
KNOWN_NOISE_TERMS = (
    "kodak",
    "gray scale",
    "national archives",
    "国立公文書館",
    "内閣文庫",
    "番號",
    "冊數",
    "函號",
)
TOKEN_PATTERN = re.compile(r"[\u3400-\u4dbf\u4e00-\u9fff]|[A-Za-z0-9]+|[^\s]")


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _edit_distance(reference: Sequence[str], hypothesis: Sequence[str]) -> int:
    previous = list(range(len(hypothesis) + 1))
    for ref_index, ref_item in enumerate(reference, start=1):
        current = [ref_index]
        for hyp_index, hyp_item in enumerate(hypothesis, start=1):
            current.append(
                min(
                    current[-1] + 1,
                    previous[hyp_index] + 1,
                    previous[hyp_index - 1] + (ref_item != hyp_item),
                )
            )
        previous = current
    return previous[-1]


def _characters(boxes: list[LabelBox]) -> list[str]:
    return [
        character
        for box in boxes
        for character in box.transcription
        if not character.isspace()
    ]


def _tokens(boxes: list[LabelBox]) -> list[str]:
    return [token for box in boxes for token in TOKEN_PATTERN.findall(box.transcription)]


def _points(box: LabelBox) -> tuple[tuple[float, float], ...]:
    return box.points


def _page_audit(
    page: PageRecord,
    cache_boxes: list[LabelBox],
    label_boxes: list[LabelBox],
) -> dict[str, Any]:
    cache_by_points: dict[tuple[tuple[float, float], ...], list[tuple[int, LabelBox]]] = {}
    for index, box in enumerate(cache_boxes):
        cache_by_points.setdefault(_points(box), []).append((index, box))

    exact_retained = 0
    text_changed_same_geometry = 0
    new_or_moved_geometry = 0
    retained_indices: list[int] = []
    replacement_texts: list[str] = []
    residual_noise: list[str] = []
    for label_box in label_boxes:
        point_matches = cache_by_points.get(_points(label_box), [])
        if point_matches:
            index, cache_box = point_matches[0]
            retained_indices.append(index)
            if cache_box.transcription == label_box.transcription:
                exact_retained += 1
            else:
                text_changed_same_geometry += 1
        else:
            new_or_moved_geometry += 1
        if REPLACEMENT_CHARACTER in label_box.transcription:
            replacement_texts.append(label_box.transcription)
        folded = label_box.transcription.casefold()
        if any(term.casefold() in folded for term in KNOWN_NOISE_TERMS):
            residual_noise.append(label_box.transcription)

    return {
        "page_id": page.page_id,
        "image_key": page.image_key,
        "cache_boxes": len(cache_boxes),
        "label_boxes": len(label_boxes),
        "net_removed_boxes": len(cache_boxes) - len(label_boxes),
        "changed": cache_boxes != label_boxes,
        "exact_retained_boxes": exact_retained,
        "text_changed_same_geometry": text_changed_same_geometry,
        "new_or_moved_geometry": new_or_moved_geometry,
        "reading_order_changed": retained_indices != sorted(retained_indices),
        "replacement_texts": replacement_texts,
        "residual_noise": residual_noise,
    }


def _metric_record(value: float | None, reason: str | None = None) -> dict[str, Any]:
    return {
        "status": "evaluated" if value is not None else "not_evaluated",
        "value": value,
        "reason": reason,
    }


def audit_ppocrlabel_annotations(
    *,
    source_id: str = DEFAULT_SOURCE_ID,
    inventory_path: Path = INVENTORY_PATH,
    output_path: Path = OUTPUT_PATH,
    project_root: Path = PROJECT_ROOT,
    processed_root: Path = PROCESSED_ROOT,
    accept_transcription_review: bool = False,
) -> dict[str, Any]:
    """Audit registered PPOCRLabel files and atomically save a deterministic report."""

    source_dir = _resolve_source_dir(processed_root, source_id)
    pages = _load_inventory(
        inventory_path=inventory_path,
        project_root=project_root,
        processed_root=processed_root,
        source_id=source_id,
    )
    pages_by_key = {page.image_key: page for page in pages}
    cache_path = source_dir / "Cache.cach"
    label_path = source_dir / "Label.txt"
    state_path = source_dir / "fileState.txt"
    cache = _parse_annotation_file(cache_path, pages_by_key)
    labels = _parse_annotation_file(label_path, pages_by_key)
    confirmed = _parse_file_state(state_path, pages_by_key)

    page_reports = [
        _page_audit(page, cache.get(page.image_key, []), labels.get(page.image_key, []))
        for page in pages
    ]
    all_pages_confirmed = set(pages_by_key) == confirmed
    changed_pages = sum(bool(report["changed"]) for report in page_reports)
    replacement_pages = [
        report["page_id"] for report in page_reports if report["replacement_texts"]
    ]
    noise_pages = [report["page_id"] for report in page_reports if report["residual_noise"]]
    quality_gates = {
        "all_pages_have_file_state": all_pages_confirmed,
        "manual_layout_changes_present": changed_pages > 0,
        "no_unicode_replacement_characters": not replacement_pages,
        "no_known_digitization_noise": not noise_pages,
        "transcription_review_explicitly_accepted": accept_transcription_review,
        "caption_ground_truth_available": False,
    }
    transcription_ready = all(
        quality_gates[key]
        for key in (
            "all_pages_have_file_state",
            "no_unicode_replacement_characters",
            "no_known_digitization_noise",
            "transcription_review_explicitly_accepted",
        )
    )

    if transcription_ready:
        reference_characters = [
            character
            for page in pages
            for character in _characters(labels.get(page.image_key, []))
        ]
        hypothesis_characters = [
            character
            for page in pages
            for character in _characters(cache.get(page.image_key, []))
        ]
        reference_tokens = [
            token for page in pages for token in _tokens(labels.get(page.image_key, []))
        ]
        hypothesis_tokens = [
            token for page in pages for token in _tokens(cache.get(page.image_key, []))
        ]
        if not reference_characters or not reference_tokens:
            raise ConversionError("accepted transcription reference is empty")
        cer = _edit_distance(reference_characters, hypothesis_characters) / len(
            reference_characters
        )
        wer = _edit_distance(reference_tokens, hypothesis_tokens) / len(reference_tokens)
        cer_record = _metric_record(cer)
        wer_record = _metric_record(wer)
    else:
        reasons: list[str] = []
        if not all_pages_confirmed:
            reasons.append("not all inventory pages are confirmed in fileState.txt")
        if replacement_pages:
            reasons.append("Unicode replacement characters remain in manual labels")
        if noise_pages:
            reasons.append("known digitization noise remains in manual labels")
        if not accept_transcription_review:
            reasons.append("transcription review was not explicitly accepted")
        reason = "; ".join(reasons)
        cer_record = _metric_record(None, reason)
        wer_record = _metric_record(None, reason)

    report: dict[str, Any] = {
        "schema_version": "1.0",
        "dataset_id": "real-pilot-v1-ppocrlabel-quality-audit",
        "dataset_kind": "real_pilot_annotation_quality_audit",
        "evaluation_status": "not_evaluated",
        "pipeline_version": PIPELINE_VERSION,
        "source_id": source_id,
        "input_hashes": {
            "inventory_sha256": _sha256(inventory_path),
            "cache_sha256": _sha256(cache_path),
            "label_sha256": _sha256(label_path),
            "file_state_sha256": _sha256(state_path),
        },
        "summary": {
            "total_pages": len(pages),
            "tool_confirmed_pages": len(confirmed),
            "changed_pages": changed_pages,
            "cache_boxes": sum(len(boxes) for boxes in cache.values()),
            "label_boxes": sum(len(boxes) for boxes in labels.values()),
            "net_removed_boxes": sum(len(boxes) for boxes in cache.values())
            - sum(len(boxes) for boxes in labels.values()),
            "exact_retained_boxes": sum(
                int(report["exact_retained_boxes"]) for report in page_reports
            ),
            "text_changed_same_geometry": sum(
                int(report["text_changed_same_geometry"]) for report in page_reports
            ),
            "new_or_moved_geometry": sum(
                int(report["new_or_moved_geometry"]) for report in page_reports
            ),
            "reading_order_changed_pages": sum(
                bool(report["reading_order_changed"]) for report in page_reports
            ),
            "replacement_character_pages": replacement_pages,
            "known_noise_pages": noise_pages,
        },
        "quality_gates": quality_gates,
        "layout_snapshot_ready": all_pages_confirmed and changed_pages > 0,
        "transcription_evaluation_ready": transcription_ready,
        "evaluation_set_freeze_ready": transcription_ready
        and quality_gates["caption_ground_truth_available"],
        "metrics": {
            "cer": cer_record,
            "wer_mixed_cjk_tokens": {
                **wer_record,
                "tokenization": (
                    "each CJK ideograph is one token; contiguous ASCII alphanumerics "
                    "form one token; other non-whitespace symbols are individual tokens"
                ),
            },
            "figure_title_recall": _metric_record(
                None,
                "PPOCRLabel output has no caption-region ground-truth categories",
            ),
        },
        "pages": page_reports,
    }
    _write_json_atomic(output_path, report)
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-id", default=DEFAULT_SOURCE_ID)
    parser.add_argument(
        "--accept-transcription-review",
        action="store_true",
        help="Calculate CER/WER only after every retained transcription was reviewed.",
    )
    args = parser.parse_args()
    try:
        report = audit_ppocrlabel_annotations(
            source_id=args.source_id,
            accept_transcription_review=args.accept_transcription_review,
        )
    except ConversionError as exc:
        parser.error(str(exc))
    print(
        json.dumps(
            {
                "evaluation_status": report["evaluation_status"],
                "summary": report["summary"],
                "quality_gates": report["quality_gates"],
                "layout_snapshot_ready": report["layout_snapshot_ready"],
                "transcription_evaluation_ready": report[
                    "transcription_evaluation_ready"
                ],
                "evaluation_set_freeze_ready": report["evaluation_set_freeze_ready"],
                "metrics": report["metrics"],
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
