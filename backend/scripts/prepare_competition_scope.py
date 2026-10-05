"""Pin a small, scan-hashed review scope without modifying model candidates."""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

from scripts.convert_ppocrlabel_annotations import (
    INVENTORY_PATH,
    PROJECT_ROOT,
    ConversionError,
    _read_json_object,
    _sha256,
    _write_json_atomic,
)
from scripts.generate_historical_review_candidates import OUTPUT_PATH as CANDIDATE_PATH

DATA_ROOT = PROJECT_ROOT / "backend/data/real_pilot"
SELECTION_PATH = DATA_ROOT / "competition_core_selection.json"
SCOPE_PATH = DATA_ROOT / "competition_scope.json"


def prepare_scope(
    *,
    selection_path: Path = SELECTION_PATH,
    candidate_path: Path = CANDIDATE_PATH,
    inventory_path: Path = INVENTORY_PATH,
    output_path: Path = SCOPE_PATH,
    project_root: Path = PROJECT_ROOT,
) -> dict[str, Any]:
    selection = _read_json_object(selection_path)
    candidate = _read_json_object(candidate_path)
    inventory = _read_json_object(inventory_path)
    if selection.get("dataset_kind") != "competition_review_selection":
        raise ConversionError("not a competition review selection")
    source_id = selection["source_id"]
    if candidate.get("source_id") != source_id:
        raise ConversionError("selection/candidate source mismatch")
    numbers = selection.get("page_numbers")
    if (
        not isinstance(numbers, list)
        or not numbers
        or any(isinstance(n, bool) or not isinstance(n, int) or n < 1 for n in numbers)
        or len(set(numbers)) != len(numbers)
    ):
        raise ConversionError("selection requires unique positive page numbers")
    if candidate["input_hashes"]["inventory_sha256"] != _sha256(inventory_path):
        raise ConversionError("candidate inventory is stale")
    source_dir = project_root / "backend/data/processed/real_pilot_v1" / source_id
    if candidate["input_hashes"]["label_sha256"] != _sha256(source_dir / "Label.txt"):
        raise ConversionError("candidate Label is stale")
    reference_hash = candidate["input_hashes"].get("reference_sha256")
    if reference_hash and reference_hash != _sha256(
        project_root / "backend/data/real_pilot/naifu_wikisource_reference.json"
    ):
        raise ConversionError("candidate reference is stale")
    inventory_pages = {p["page_id"]: p for p in inventory["pages"]}
    candidate_pages = {p["page_id"]: p for p in candidate["pages"]}
    pages = []
    for number in numbers:
        page_id = f"{source_id}-p{number:04d}"
        if page_id not in inventory_pages or page_id not in candidate_pages:
            raise ConversionError(f"selected page is missing: {page_id}")
        page, candidates = inventory_pages[page_id], candidate_pages[page_id]
        image = (project_root / page["image_path"]).resolve()
        if project_root.resolve() not in image.parents or _sha256(image) != page["sha256"]:
            raise ConversionError(f"scan path/hash mismatch: {page_id}")
        pages.append(
            {
                "page_id": page_id,
                "pdf_page": number,
                "image_path": page["image_path"],
                "image_sha256": page["sha256"],
                "pdf_filename": page["provenance"]["pdf_filename"],
                "pdf_sha256": page["provenance"]["pdf_sha256"],
                "box_ids": [b["box_id"] for b in candidates["boxes"]],
                "figure_ids": [f["figure_id"] for f in candidates.get("figures", [])],
                "missing_caption_ids": [
                    f["figure_id"] + "-title"
                    for f in candidates.get("figures", [])
                    if f.get("caption_box_id") is None and f.get("candidate_title_bbox")
                ],
                "selection_basis": selection.get("selection_basis", {}).get(str(number)),
            }
        )
    scope = {
        "schema_version": "1.0",
        "dataset_kind": "competition_evaluation_scope",
        "source_id": source_id,
        "evaluation_status": "not_evaluated",
        "truth_status": "pending_scan_level_human_review",
        "source_candidate_sha256": _sha256(candidate_path),
        "selection_sha256": _sha256(selection_path),
        "input_hashes": {
            **candidate["input_hashes"],
            "cache_sha256": _sha256(
                project_root / "backend/data/processed/real_pilot_v1" / source_id / "Cache.cach"
            ),
        },
        "pages": pages,
        "statistics": {
            "pages": len(pages),
            "retained_boxes": sum(len(p["box_ids"]) for p in pages),
            "figure_candidates": sum(len(p["figure_ids"]) for p in pages),
            "missing_caption_candidates": sum(len(p["missing_caption_ids"]) for p in pages),
        },
        "metric_protocol": {
            "cer": "micro Levenshtein / reference characters; NFC, whitespace removed",
            "wer": "micro Levenshtein / CJK-character + Latin-word + punctuation tokens",
            "recognition_scope": (
                "retained original boxes human-transcribed as text/caption/annotation"
            ),
            "title_recall": "raw OCR box localization, one-to-one IoU >= 0.5",
            "title_inventory": "requires explicit full-page caption inventory confirmation",
            "sampling": "purposive diagnostic subset; not population accuracy",
            "normalization": "no traditional/simplified conversion or reference substitution",
        },
    }
    supplemental_count = sum(
        box.get("original_box_index") is None
        for page in candidate["pages"]
        if page["page_id"] in {p["page_id"] for p in pages}
        for box in page["boxes"]
    )
    if supplemental_count:
        scope["statistics"]["retained_boxes"] -= supplemental_count
        scope["statistics"]["supplemental_region_candidates"] = supplemental_count
        scope["metric_protocol"]["supplemental_regions"] = (
            "required for full-page review; excluded from retained-original-box CER/WER; "
            "no synthetic raw prediction is created"
        )
    _write_json_atomic(output_path, scope)
    return scope


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=SCOPE_PATH)
    args = parser.parse_args()
    try:
        scope = prepare_scope(output_path=args.output)
    except (ConversionError, OSError, KeyError) as exc:
        parser.error(str(exc))
    print(scope["statistics"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
