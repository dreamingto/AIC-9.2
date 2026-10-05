"""Remove narrowly-scoped digitization watermarks from PPOCRLabel labels.

The operation is intentionally conservative: only exact text matches on the
registered page and inside the expected bottom-right watermark area are
removed.  A content-hash audit record is written next to the local real-pilot
artifacts.  The original layout snapshot remains available for recovery.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import tempfile
from pathlib import Path
from typing import Any, cast

from scripts.convert_ppocrlabel_annotations import (
    DEFAULT_SOURCE_ID,
    INVENTORY_PATH,
    PROCESSED_ROOT,
    PROJECT_ROOT,
    ConversionError,
    _load_inventory,
    _resolve_source_dir,
    _write_json_atomic,
)

AUDIT_OUTPUT_PATH = (
    PROJECT_ROOT / "backend" / "data" / "real_pilot" / "label_sanitization_audit.json"
)
PIPELINE_VERSION = "ppocrlabel-label-sanitizer-v1"
TARGET_PAGE_ID = f"{DEFAULT_SOURCE_ID}-p0008"
TARGET_TEXTS = frozenset({"国立公文書館", "National Archives of Japan"})


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _box_bounds(box: dict[str, Any]) -> tuple[float, float, float, float]:
    raw_points = box.get("points")
    if not isinstance(raw_points, list) or len(raw_points) != 4:
        raise ConversionError("watermark candidate has invalid points")
    try:
        xs = [float(point[0]) for point in raw_points]
        ys = [float(point[1]) for point in raw_points]
    except (TypeError, ValueError, IndexError) as exc:
        raise ConversionError("watermark candidate has invalid points") from exc
    return min(xs), min(ys), max(xs), max(ys)


def _is_target_watermark(
    box: dict[str, Any], *, page_width: int, page_height: int
) -> bool:
    if box.get("transcription") not in TARGET_TEXTS:
        return False
    x_min, y_min, x_max, y_max = _box_bounds(box)
    return (
        x_min >= page_width * 0.85
        and y_min >= page_height * 0.9
        and x_max <= page_width
        and y_max <= page_height
    )


def _write_text_atomic(path: Path, content: str) -> None:
    temporary_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            dir=path.parent,
            delete=False,
            suffix=".part",
            newline="\n",
        ) as temporary:
            temporary.write(content)
            temporary.flush()
            os.fsync(temporary.fileno())
            temporary_path = Path(temporary.name)
        temporary_path.replace(path)
        temporary_path = None
    finally:
        if temporary_path is not None:
            temporary_path.unlink(missing_ok=True)


def sanitize_labels(
    *,
    source_id: str = DEFAULT_SOURCE_ID,
    inventory_path: Path = INVENTORY_PATH,
    processed_root: Path = PROCESSED_ROOT,
    project_root: Path = PROJECT_ROOT,
    audit_output_path: Path = AUDIT_OUTPUT_PATH,
) -> dict[str, Any]:
    """Remove the registered watermark boxes and return the audit record."""

    if source_id != DEFAULT_SOURCE_ID:
        raise ConversionError("no watermark sanitation rule is registered for this source")
    pages = _load_inventory(
        inventory_path=inventory_path,
        project_root=project_root,
        processed_root=processed_root,
        source_id=source_id,
    )
    page = next((item for item in pages if item.page_id == TARGET_PAGE_ID), None)
    if page is None:
        raise ConversionError(f"registered watermark page is missing: {TARGET_PAGE_ID}")

    source_dir = _resolve_source_dir(processed_root, source_id)
    label_path = source_dir / "Label.txt"
    try:
        original = label_path.read_text(encoding="utf-8")
    except OSError as exc:
        raise ConversionError("unable to read PPOCRLabel Label.txt") from exc
    before_hash = _sha256(label_path)

    output_lines: list[str] = []
    removed: list[dict[str, Any]] = []
    target_row_found = False
    for line_number, line in enumerate(original.splitlines(), start=1):
        if not line.strip():
            continue
        if line.count("\t") != 1:
            raise ConversionError(f"Label.txt:{line_number} must contain path and labels")
        key, raw_json = line.split("\t", 1)
        try:
            raw_boxes = json.loads(raw_json)
        except json.JSONDecodeError as exc:
            raise ConversionError(f"Label.txt:{line_number} contains invalid JSON") from exc
        if not isinstance(raw_boxes, list):
            raise ConversionError(f"Label.txt:{line_number} labels must be an array")
        if key.replace("\\", "/") == page.image_key:
            target_row_found = True
            retained: list[Any] = []
            for raw_box in raw_boxes:
                if not isinstance(raw_box, dict):
                    raise ConversionError(
                        f"Label.txt:{line_number} watermark candidate must be an object"
                    )
                box = cast(dict[str, Any], raw_box)
                if _is_target_watermark(
                    box, page_width=page.width, page_height=page.height
                ):
                    removed.append(box)
                else:
                    retained.append(box)
            raw_boxes = retained
        output_lines.append(
            f"{key}\t{json.dumps(raw_boxes, ensure_ascii=False, separators=(',', ':'))}"
        )

    if not target_row_found:
        raise ConversionError(f"Label.txt does not contain target page: {page.image_key}")
    retained_target_texts = {
        str(box.get("transcription"))
        for line in output_lines
        for box in json.loads(line.split("\t", 1)[1])
        if isinstance(box, dict) and box.get("transcription") in TARGET_TEXTS
    }
    if retained_target_texts:
        raise ConversionError("registered watermark text remains outside the safe area")
    removed_texts = {str(box.get("transcription")) for box in removed}
    if removed and removed_texts != TARGET_TEXTS:
        raise ConversionError("watermark sanitation matched an unexpected subset")
    updated = "\n".join(output_lines) + "\n"
    if updated != original:
        _write_text_atomic(label_path, updated)
    after_hash = _sha256(label_path)
    audit: dict[str, Any] = {
        "schema_version": "1.0",
        "dataset_kind": "real_pilot_label_sanitization_audit",
        "evaluation_status": "not_evaluated",
        "pipeline_version": PIPELINE_VERSION,
        "source_id": source_id,
        "page_id": page.page_id,
        "label_sha256_before": before_hash,
        "label_sha256_after": after_hash,
        "removed_count": len(removed),
        "removed": [
            {
                "transcription": box["transcription"],
                "points": box["points"],
                "reason": "known_repository_digitization_watermark",
            }
            for box in removed
        ],
        "transcription_review_state": "unreviewed",
        "disclaimer": (
            "Removing registered digitization watermarks is layout sanitation only; "
            "it does not verify any retained transcription."
        ),
    }
    _write_json_atomic(audit_output_path, audit)
    return audit


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-id", default=DEFAULT_SOURCE_ID)
    args = parser.parse_args()
    try:
        result = sanitize_labels(source_id=args.source_id)
    except ConversionError as exc:
        parser.error(str(exc))
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
