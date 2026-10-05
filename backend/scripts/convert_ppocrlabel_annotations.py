"""Convert PPOCRLabel files into the real-pilot annotation schema.

PPOCRLabel's ``Cache.cach`` is machine-generated working data.  It must not be
treated as human truth.  ``fileState.txt`` can also be written by a mechanical
save workflow, so it is only promoted to human review when the operator uses
``--accept-file-state`` together with an explicit reviewer identifier.  This
only accepts the page layout and box selection.  Transcription correction is a
separate gate because deleting OCR noise is not the same as checking every
character.  Even then, the original cache remains in the raw OCR layer.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import re
import tempfile
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Any, NoReturn, cast

from scripts.annotation_errors import ConversionError as ConversionError

PROJECT_ROOT = Path(__file__).resolve().parents[2]
INVENTORY_PATH = PROJECT_ROOT / "backend" / "data" / "real_pilot" / "derived_pages.json"
OUTPUT_PATH = PROJECT_ROOT / "backend" / "data" / "real_pilot" / "annotations.ppocrlabel-draft.json"
PROCESSED_ROOT = (PROJECT_ROOT / "backend" / "data" / "processed" / "real_pilot_v1").resolve()
DEFAULT_SOURCE_ID = "commons-najda-tiangong-kaiwu-2"
PIPELINE_VERSION = "ppocrlabel-annotation-converter-v1"
PPOCRLABEL_VERSION = "3.1.6"
OCR_ENGINE = {
    "provider": "paddleocr",
    "model": "PP-OCRv5_mobile",
    "version": "3.0.3",
    "preprocessing_hash": None,
}

Point = tuple[float, float]


@dataclass(frozen=True)
class PageRecord:
    page_id: str
    source_id: str
    image_path: str
    image_key: str
    width: int
    height: int
    sha256: str
    provenance: dict[str, Any]


@dataclass(frozen=True)
class LabelBox:
    transcription: str
    points: tuple[Point, ...]
    difficult: bool


def _reject_json_constant(value: str) -> NoReturn:
    raise ConversionError(f"non-finite JSON number is not allowed: {value}")


def _read_json_object(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"), parse_constant=_reject_json_constant)
    except OSError as exc:
        raise ConversionError(f"unable to read JSON file: {path}") from exc
    except json.JSONDecodeError as exc:
        raise ConversionError(f"invalid JSON file: {path}") from exc
    if not isinstance(payload, dict):
        raise ConversionError(f"JSON root must be an object: {path}")
    return cast(dict[str, Any], payload)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _validate_source_id(source_id: str) -> str:
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]{0,127}", source_id):
        raise ConversionError("source_id contains unsupported path characters")
    return source_id


def _resolve_source_dir(processed_root: Path, source_id: str) -> Path:
    safe_root = processed_root.resolve()
    source_dir = (safe_root / _validate_source_id(source_id)).resolve()
    try:
        source_dir.relative_to(safe_root)
    except ValueError as exc:
        raise ConversionError("annotation directory escapes the processed data root") from exc
    if not source_dir.is_dir():
        raise ConversionError(f"annotation directory does not exist: {source_id}")
    return source_dir


def _require_string(item: dict[str, Any], field: str) -> str:
    value = item.get(field)
    if not isinstance(value, str) or not value:
        raise ConversionError(f"inventory field {field} must be a non-empty string")
    return value


def _require_positive_int(item: dict[str, Any], field: str) -> int:
    value = item.get(field)
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise ConversionError(f"inventory field {field} must be a positive integer")
    return value


def _load_inventory(
    *,
    inventory_path: Path,
    project_root: Path,
    processed_root: Path,
    source_id: str,
) -> list[PageRecord]:
    payload = _read_json_object(inventory_path)
    if payload.get("dataset_kind") != "real_pilot_page_inventory":
        raise ConversionError("inventory is not a real pilot page inventory")
    if payload.get("evaluation_status") != "not_evaluated":
        raise ConversionError("real pilot inventory must remain not_evaluated")
    raw_pages = payload.get("pages")
    if not isinstance(raw_pages, list):
        raise ConversionError("inventory pages must be an array")

    root = project_root.resolve()
    safe_processed_root = processed_root.resolve()
    pages: list[PageRecord] = []
    page_ids: set[str] = set()
    image_keys: set[str] = set()
    for raw_page in raw_pages:
        if not isinstance(raw_page, dict):
            raise ConversionError("each inventory page must be an object")
        page = cast(dict[str, Any], raw_page)
        if page.get("source_id") != source_id:
            continue
        page_id = _require_string(page, "page_id")
        image_path = _require_string(page, "image_path")
        sha256 = _require_string(page, "sha256").lower()
        width = _require_positive_int(page, "width")
        height = _require_positive_int(page, "height")
        if page_id in page_ids:
            raise ConversionError(f"duplicate page_id in inventory: {page_id}")
        if Path(image_path).is_absolute():
            raise ConversionError(f"inventory image_path must be relative: {image_path}")
        resolved_image = (root / image_path).resolve()
        try:
            relative_image = resolved_image.relative_to(safe_processed_root)
        except ValueError as exc:
            raise ConversionError(f"inventory image escapes processed root: {image_path}") from exc
        if len(relative_image.parts) != 2 or relative_image.parts[0] != source_id:
            raise ConversionError(f"inventory image is outside source directory: {image_path}")
        if resolved_image.suffix.lower() != ".png" or not resolved_image.is_file():
            raise ConversionError(f"inventory PNG is missing: {image_path}")
        if not re.fullmatch(r"[0-9a-f]{64}", sha256):
            raise ConversionError(f"inventory sha256 is invalid: {page_id}")
        if _sha256(resolved_image) != sha256:
            raise ConversionError(f"inventory sha256 mismatch: {page_id}")
        image_key = relative_image.as_posix()
        if image_key in image_keys:
            raise ConversionError(f"duplicate image path in inventory: {image_key}")
        raw_provenance = page.get("provenance", {})
        if not isinstance(raw_provenance, dict) or not all(
            isinstance(key, str) for key in raw_provenance
        ):
            raise ConversionError(f"inventory provenance is invalid: {page_id}")
        pages.append(
            PageRecord(
                page_id=page_id,
                source_id=source_id,
                image_path=image_path,
                image_key=image_key,
                width=width,
                height=height,
                sha256=sha256,
                provenance=dict(raw_provenance),
            )
        )
        page_ids.add(page_id)
        image_keys.add(image_key)
    if not pages:
        raise ConversionError(f"inventory contains no pages for source: {source_id}")
    return pages


def _normalize_annotation_key(value: str) -> str:
    normalized = value.replace("\\", "/")
    parts = normalized.split("/")
    if (
        not normalized
        or normalized.startswith("/")
        or any(part in {"", ".", ".."} for part in parts)
        or ":" in parts[0]
    ):
        raise ConversionError(f"unsafe annotation path: {value}")
    return PurePosixPath(*parts).as_posix()


def _finite_number(value: Any, *, context: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ConversionError(f"{context} must be a number")
    number = float(value)
    if not math.isfinite(number):
        raise ConversionError(f"{context} must be finite")
    return number


def _parse_box(raw_box: Any, *, page: PageRecord, context: str) -> LabelBox:
    if not isinstance(raw_box, dict):
        raise ConversionError(f"{context} must be an object")
    box = cast(dict[str, Any], raw_box)
    transcription = box.get("transcription")
    difficult = box.get("difficult")
    raw_points = box.get("points")
    if not isinstance(transcription, str):
        raise ConversionError(f"{context}.transcription must be a string")
    if not isinstance(difficult, bool):
        raise ConversionError(f"{context}.difficult must be a boolean")
    if not isinstance(raw_points, list) or len(raw_points) != 4:
        raise ConversionError(f"{context}.points must contain exactly four points")

    points: list[Point] = []
    for point_index, raw_point in enumerate(raw_points, start=1):
        if not isinstance(raw_point, list) or len(raw_point) != 2:
            raise ConversionError(f"{context}.points[{point_index}] must be [x, y]")
        x = _finite_number(raw_point[0], context=f"{context}.points[{point_index}].x")
        y = _finite_number(raw_point[1], context=f"{context}.points[{point_index}].y")
        if x < 0 or x > page.width or y < 0 or y > page.height:
            raise ConversionError(f"{context}.points[{point_index}] is outside page bounds")
        points.append((x, y))
    area_twice = abs(
        sum(
            points[index][0] * points[(index + 1) % 4][1]
            - points[(index + 1) % 4][0] * points[index][1]
            for index in range(4)
        )
    )
    if area_twice <= 1e-9:
        raise ConversionError(f"{context}.points form a zero-area polygon")
    return LabelBox(transcription=transcription, points=tuple(points), difficult=difficult)


def _parse_annotation_file(
    path: Path, pages_by_key: dict[str, PageRecord]
) -> dict[str, list[LabelBox]]:
    if not path.exists():
        return {}
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError as exc:
        raise ConversionError(f"unable to read PPOCRLabel file: {path.name}") from exc
    result: dict[str, list[LabelBox]] = {}
    for line_number, line in enumerate(lines, start=1):
        if not line.strip():
            continue
        if line.count("\t") != 1:
            raise ConversionError(f"{path.name}:{line_number} must contain path and JSON")
        raw_key, raw_json = line.split("\t", 1)
        key = _normalize_annotation_key(raw_key)
        if key not in pages_by_key:
            raise ConversionError(f"{path.name}:{line_number} references unknown page: {key}")
        if key in result:
            raise ConversionError(f"{path.name}:{line_number} duplicates page: {key}")
        try:
            raw_boxes = json.loads(raw_json, parse_constant=_reject_json_constant)
        except json.JSONDecodeError as exc:
            raise ConversionError(f"{path.name}:{line_number} contains invalid JSON") from exc
        if not isinstance(raw_boxes, list):
            raise ConversionError(f"{path.name}:{line_number} labels must be an array")
        page = pages_by_key[key]
        result[key] = [
            _parse_box(
                raw_box,
                page=page,
                context=f"{path.name}:{line_number}:box[{box_index}]",
            )
            for box_index, raw_box in enumerate(raw_boxes, start=1)
        ]
    return result


def _parse_file_state(path: Path, pages_by_key: dict[str, PageRecord]) -> set[str]:
    if not path.exists():
        return set()
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError as exc:
        raise ConversionError("unable to read PPOCRLabel fileState.txt") from exc
    confirmed: set[str] = set()
    for line_number, line in enumerate(lines, start=1):
        if not line.strip():
            continue
        if line.count("\t") != 1:
            raise ConversionError(f"fileState.txt:{line_number} must contain path and state")
        raw_key, state = line.split("\t", 1)
        key = _normalize_annotation_key(raw_key)
        if key not in pages_by_key:
            raise ConversionError(f"fileState.txt:{line_number} references unknown page: {key}")
        if state.strip() != "1":
            raise ConversionError(f"fileState.txt:{line_number} has unsupported state")
        if key in confirmed:
            raise ConversionError(f"fileState.txt:{line_number} duplicates page: {key}")
        confirmed.add(key)
    return confirmed


def _box_geometry(box: LabelBox, page: PageRecord) -> tuple[list[float], dict[str, float]]:
    xs = [point[0] for point in box.points]
    ys = [point[1] for point in box.points]
    x_min, x_max = min(xs), max(xs)
    y_min, y_max = min(ys), max(ys)
    pixel_bbox = [x_min, y_min, x_max, y_max]
    normalized_bbox = {
        "x": x_min / page.width,
        "y": y_min / page.height,
        "width": (x_max - x_min) / page.width,
        "height": (y_max - y_min) / page.height,
    }
    return pixel_bbox, normalized_bbox


def _line_record(
    box: LabelBox, *, page: PageRecord, line_id: str, order: int, review_state: str
) -> dict[str, Any]:
    pixel_bbox, normalized_bbox = _box_geometry(box, page)
    return {
        "line_id": line_id,
        "text": box.transcription,
        "polygon": [[x, y] for x, y in box.points],
        "bbox": pixel_bbox,
        "normalized_bbox": normalized_bbox,
        "confidence": None,
        "candidates": [],
        "difficult": box.difficult,
        "reading_order": order,
        "review_state": review_state,
    }


def _page_annotation(
    *,
    page: PageRecord,
    cache_boxes: list[LabelBox] | None,
    label_boxes: list[LabelBox] | None,
    tool_confirmed: bool,
    layout_confirmed: bool,
    transcription_confirmed: bool,
    reviewer: str | None,
) -> tuple[dict[str, Any], int]:
    if layout_confirmed:
        effective_boxes = label_boxes or []
        source_kind = "ppocrlabel_label"
        review_state = "reviewed"
    elif cache_boxes is not None:
        effective_boxes = cache_boxes
        source_kind = "ppocrlabel_cache"
        review_state = "unreviewed"
    else:
        effective_boxes = label_boxes or []
        source_kind = "ppocrlabel_label_unconfirmed"
        review_state = "unreviewed"
    raw_boxes = cache_boxes if cache_boxes is not None else effective_boxes
    raw_text = "\n".join(box.transcription for box in raw_boxes)
    corrected_text = (
        "\n".join(box.transcription for box in (label_boxes or []))
        if transcription_confirmed
        else None
    )

    regions: list[dict[str, Any]] = []
    reading_order: list[str] = []
    for order, box in enumerate(effective_boxes, start=1):
        region_id = f"{page.page_id}-r{order:03d}"
        _, normalized_bbox = _box_geometry(box, page)
        regions.append(
            {
                "region_id": region_id,
                "category": "unknown",
                "polygon": [[x, y] for x, y in box.points],
                "bbox": normalized_bbox,
                "reading_order": order,
                "review_state": review_state,
            }
        )
        reading_order.append(region_id)

    raw_lines = [
        _line_record(
            box,
            page=page,
            line_id=f"{page.page_id}-l{order:03d}",
            order=order,
            review_state="unreviewed",
        )
        for order, box in enumerate(raw_boxes, start=1)
    ]
    corrected_lines = (
        [
            _line_record(
                box,
                page=page,
                line_id=f"{page.page_id}-c{order:03d}",
                order=order,
                review_state="reviewed",
            )
            for order, box in enumerate(label_boxes or [], start=1)
        ]
        if transcription_confirmed
        else []
    )
    change_log: list[dict[str, Any]] = []
    if transcription_confirmed and corrected_text != raw_text:
        change_log.append(
            {
                "from": raw_text,
                "to": corrected_text,
                "reviewer": reviewer,
                "changed_at": None,
                "reason": "ppocrlabel_manual_review",
                "source": "Label.txt+fileState.txt",
            }
        )

    provenance = dict(page.provenance)
    provenance.update(
        {
            "input_sha256": page.sha256,
            "source_kind": source_kind,
            "annotation_tool": {"name": "PPOCRLabel", "version": PPOCRLABEL_VERSION},
            "annotation_pipeline_version": PIPELINE_VERSION,
            "ppocrlabel_file_state": tool_confirmed,
            "file_state_accepted_as_layout_review": layout_confirmed,
            "file_state_accepted_as_transcription_review": transcription_confirmed,
            "layout_reviewer": reviewer if layout_confirmed else None,
        }
    )
    return (
        {
            "page_id": page.page_id,
            "source_id": page.source_id,
            "image_path": page.image_path,
            "width": page.width,
            "height": page.height,
            "layout": {
                "status": "reviewed" if layout_confirmed else "pending_review",
                "orientation": "unknown",
                "regions": regions,
                "reading_order": reading_order,
            },
            "ocr": {
                "status": "inferred",
                **OCR_ENGINE,
                "input_sha256": page.sha256,
                "lines": raw_lines,
            },
            "text_layers": {
                "raw_ocr": raw_text,
                "corrected_text": corrected_text,
                "corrected_lines": corrected_lines,
                "correction_state": ("reviewed" if transcription_confirmed else "unreviewed"),
                "reviewer": reviewer if transcription_confirmed else None,
                "reviewed_at": None,
                "change_log": change_log,
            },
            "provenance": provenance,
        },
        len(effective_boxes),
    )


def _write_json_atomic(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
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
            temporary.write(json.dumps(payload, ensure_ascii=False, indent=2) + "\n")
            temporary.flush()
            os.fsync(temporary.fileno())
            temporary_path = Path(temporary.name)
        temporary_path.replace(path)
        temporary_path = None
    finally:
        if temporary_path is not None:
            temporary_path.unlink(missing_ok=True)


def convert_ppocrlabel_annotations(
    *,
    source_id: str = DEFAULT_SOURCE_ID,
    inventory_path: Path = INVENTORY_PATH,
    output_path: Path = OUTPUT_PATH,
    project_root: Path = PROJECT_ROOT,
    processed_root: Path = PROCESSED_ROOT,
    reviewer: str | None = None,
    accept_file_state: bool = False,
    accept_transcription_review: bool = False,
    review_override_path: Path | None = None,
    review_candidate_path: Path | None = None,
) -> dict[str, Any]:
    """Convert the registered source's PPOCRLabel files and atomically save a draft."""

    if reviewer is not None:
        reviewer = reviewer.strip()
        if not reviewer or len(reviewer) > 200:
            raise ConversionError("reviewer must contain 1-200 non-whitespace characters")
    if accept_file_state and reviewer is None:
        raise ConversionError("accept_file_state requires an explicit reviewer")
    if accept_transcription_review and not accept_file_state:
        raise ConversionError("accept_transcription_review requires accept_file_state")
    if review_override_path is not None and (
        not accept_file_state or accept_transcription_review or review_candidate_path is None
    ):
        raise ConversionError(
            "review overrides require layout acceptance and candidates, without blanket "
            "transcription acceptance"
        )
    source_dir = _resolve_source_dir(processed_root, source_id)
    pages = _load_inventory(
        inventory_path=inventory_path,
        project_root=project_root,
        processed_root=processed_root,
        source_id=source_id,
    )
    pages_by_key = {page.image_key: page for page in pages}
    cache = _parse_annotation_file(source_dir / "Cache.cach", pages_by_key)
    labels = _parse_annotation_file(source_dir / "Label.txt", pages_by_key)
    tool_confirmed = _parse_file_state(source_dir / "fileState.txt", pages_by_key)
    if accept_transcription_review:
        replacement_pages = sorted(
            key
            for key, boxes in labels.items()
            if any("\ufffd" in box.transcription for box in boxes)
        )
        if replacement_pages:
            raise ConversionError(
                "transcription review contains Unicode replacement characters: "
                + ", ".join(replacement_pages)
            )

    imported_keys = set(cache) | set(labels) | tool_confirmed
    page_annotations: dict[str, Any] = {}
    total_boxes = 0
    layout_reviewed_pages = 0
    transcription_reviewed_pages = 0
    for page in pages:
        if page.image_key not in imported_keys:
            continue
        has_tool_confirmation = page.image_key in tool_confirmed
        layout_confirmed = accept_file_state and has_tool_confirmation
        transcription_confirmed = accept_transcription_review and layout_confirmed
        annotation, box_count = _page_annotation(
            page=page,
            cache_boxes=cache.get(page.image_key),
            label_boxes=labels.get(page.image_key),
            tool_confirmed=has_tool_confirmation,
            layout_confirmed=layout_confirmed,
            transcription_confirmed=transcription_confirmed,
            reviewer=reviewer,
        )
        page_annotations[page.page_id] = annotation
        total_boxes += box_count
        layout_reviewed_pages += int(layout_confirmed)
        transcription_reviewed_pages += int(transcription_confirmed)

    imported_pages = len(page_annotations)
    output: dict[str, Any] = {
        "schema_version": "1.0",
        "dataset_id": "real-pilot-v1-ppocrlabel-draft",
        "dataset_kind": "real_pilot_ppocrlabel_annotations",
        "evaluation_status": "not_evaluated",
        "pipeline_version": PIPELINE_VERSION,
        "source_id": source_id,
        "tool": {"name": "PPOCRLabel", "version": PPOCRLABEL_VERSION},
        "statistics": {
            "total_pages": len(pages),
            "imported_pages": imported_pages,
            "total_boxes": total_boxes,
            "tool_confirmed_pages": len(tool_confirmed),
            "layout_reviewed_pages": layout_reviewed_pages,
            "transcription_reviewed_pages": transcription_reviewed_pages,
            "unreviewed_layout_pages": imported_pages - layout_reviewed_pages,
            "unreviewed_transcription_pages": (imported_pages - transcription_reviewed_pages),
            "skipped_pages": len(pages) - imported_pages,
            "errors": [],
        },
        "pages": page_annotations,
        "disclaimer": (
            "Cache.cach and unaccepted PPOCRLabel file-state entries are draft data. "
            "Layout review requires an explicit reviewer and accept_file_state; "
            "transcription review is a separate explicit gate. This dataset is not "
            "evaluated."
        ),
    }
    if review_override_path is not None and review_candidate_path is not None:
        from scripts.apply_historical_review_overrides import apply_review_overrides

        apply_review_overrides(
            output,
            override_path=review_override_path,
            candidate_path=review_candidate_path,
            input_hashes={
                "inventory_sha256": _sha256(inventory_path),
                "label_sha256": _sha256(source_dir / "Label.txt"),
            },
        )
    _write_json_atomic(output_path, output)
    return output


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-id", default=DEFAULT_SOURCE_ID)
    parser.add_argument(
        "--reviewer",
        help="Reviewer identifier; required when --accept-file-state is used.",
    )
    parser.add_argument(
        "--accept-file-state",
        action="store_true",
        help="Accept fileState.txt pages as manually reviewed layout/box selections.",
    )
    parser.add_argument(
        "--accept-transcription-review",
        action="store_true",
        help="Also accept every retained transcription as manually corrected.",
    )
    parser.add_argument(
        "--review-overrides",
        type=Path,
        help="Import an explicitly confirmed export from the model review queue.",
    )
    parser.add_argument("--candidate", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    try:
        output = convert_ppocrlabel_annotations(
            source_id=args.source_id,
            reviewer=args.reviewer,
            accept_file_state=args.accept_file_state,
            accept_transcription_review=args.accept_transcription_review,
            review_override_path=args.review_overrides,
            review_candidate_path=(
                args.candidate
                or PROJECT_ROOT
                / "backend/data/real_pilot/annotations.model-assisted-candidates.json"
                if args.review_overrides
                else None
            ),
            output_path=args.output or (
                OUTPUT_PATH.with_name("annotations.human-reviewed.json")
                if args.review_overrides
                else OUTPUT_PATH
            ),
        )
    except ConversionError as exc:
        parser.error(str(exc))
    print(json.dumps(output["statistics"], ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
