"""Build a focused, local-only review queue from inferred OCR candidates.

The generated HTML can export human decisions, but this script never changes
raw OCR, corrected text, or verification state in the dataset.
"""

# ruff: noqa: E501

from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
import shutil
from difflib import SequenceMatcher
from pathlib import Path
from typing import Any, cast

from PIL import Image

from scripts.apply_historical_review_overrides import _bbox
from scripts.convert_ppocrlabel_annotations import (
    PROJECT_ROOT,
    ConversionError,
    _read_json_object,
    _write_json_atomic,
)
from scripts.generate_historical_review_candidates import (
    CJK_PATTERN,
)
from scripts.generate_historical_review_candidates import (
    OUTPUT_PATH as CANDIDATE_PATH,
)

OUTPUT_PATH = PROJECT_ROOT / "backend" / "data" / "real_pilot" / "model_review_queue.html"
MANIFEST_PATH = PROJECT_ROOT / "backend" / "data" / "real_pilot" / "model_review_queue.json"
ASSET_DIR = PROJECT_ROOT / "backend" / "data" / "real_pilot" / "model_review_assets"
PIPELINE_VERSION = "historical-review-queue-v1"
TEMPLATE_PATH = Path(__file__).parent / "templates" / "historical_review.html"


def _cjk(value: str) -> str:
    return "".join(CJK_PATTERN.findall(value))


def _similarity(left: str, right: str) -> float:
    left_cjk = _cjk(left)
    right_cjk = _cjk(right)
    if not left_cjk and not right_cjk:
        return 1.0
    return SequenceMatcher(a=left_cjk, b=right_cjk, autojunk=False).ratio()


def _box_review_reasons(record: dict[str, Any]) -> list[str]:
    reasons: list[str] = []
    category = record.get("category_candidate")
    role = record.get("role_candidate")
    if category == "caption":
        reasons.append("figure_title_or_component_label")
    if role == "section_heading":
        reasons.append("section_heading")
    if role == "recognition_fragment":
        reasons.append("recognition_fragment")
    if float(record.get("category_confidence", 0.0)) < 0.8:
        reasons.append("low_category_confidence")

    raw = str(record.get("raw_text", ""))
    server_raw = record.get("server_ocr")
    reference_raw = record.get("reference_candidate")
    server = cast(dict[str, Any], server_raw) if isinstance(server_raw, dict) else None
    reference = cast(dict[str, Any], reference_raw) if isinstance(reference_raw, dict) else None
    server_text = str(server.get("text", "")) if server else ""
    reference_text = str(reference.get("text", "")) if reference else ""
    if category in {"text", "caption"} and server and float(server.get("confidence", 0.0)) < 0.6:
        reasons.append("low_server_confidence")
    if reference and float(reference.get("alignment_confidence", 0.0)) < 0.5:
        reasons.append("low_reference_alignment")

    candidates = [value for value in (raw, server_text, reference_text) if _cjk(value)]
    if len(candidates) >= 2:
        pair_scores = [
            _similarity(candidates[left], candidates[right])
            for left in range(len(candidates))
            for right in range(left + 1, len(candidates))
        ]
        best_pair = max(pair_scores, default=0.0)
        if len(candidates) >= 3 and best_pair < 0.9:
            reasons.append("three_way_text_conflict")
        elif best_pair < 0.82:
            reasons.append("no_high_agreement_pair")
    elif category in {"text", "caption"}:
        reasons.append("missing_secondary_candidate")
    return reasons


def _priority(reasons: list[str]) -> str:
    critical = {
        "three_way_text_conflict",
        "low_server_confidence",
        "low_reference_alignment",
        "section_heading",
    }
    return "critical" if critical.intersection(reasons) else "review"


def _crop(*, image_path: Path, bbox: dict[str, Any], output_path: Path, padding: int = 12) -> None:
    with Image.open(image_path) as image:
        x = float(bbox["x"])
        y = float(bbox["y"])
        width = float(bbox["width"])
        height = float(bbox["height"])
        values = (x, y, width, height)
        if not all(math.isfinite(value) for value in values):
            raise ConversionError("review bbox contains a non-finite value")
        if x < 0 or y < 0 or width <= 0 or height <= 0 or x + width > 1 or y + height > 1:
            raise ConversionError("review bbox is outside the normalized image")
        left = max(0, math.floor(x * image.width) - padding)
        top = max(0, math.floor(y * image.height) - padding)
        right = min(image.width, math.ceil((x + width) * image.width) + padding)
        bottom = min(image.height, math.ceil((y + height) * image.height) + padding)
        crop = image.crop((left, top, right, bottom)).convert("RGB")
        crop.thumbnail((900, 900), Image.Resampling.LANCZOS)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        crop.save(output_path, "JPEG", quality=90, optimize=True)


def _render_html(payload: dict[str, Any]) -> str:
    embedded = json.dumps(payload, ensure_ascii=False).replace("</", "<\\/")
    return TEMPLATE_PATH.read_text(encoding="utf-8").replace("__REVIEW_DATA__", embedded)


def build_review_queue(
    *,
    candidate_path: Path = CANDIDATE_PATH,
    output_path: Path = OUTPUT_PATH,
    manifest_path: Path = MANIFEST_PATH,
    asset_dir: Path = ASSET_DIR,
    project_root: Path = PROJECT_ROOT,
    scope_path: Path | None = None,
    review_origin: str = "human",
    ai_review_path: Path | None = None,
) -> dict[str, Any]:
    if review_origin not in {"human", "ai_assisted"}:
        raise ConversionError("unsupported review origin")
    try:
        candidate_bytes = candidate_path.read_bytes()
        candidate = json.loads(candidate_bytes.decode("utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ConversionError(f"unable to read candidate file: {candidate_path}") from exc
    if not isinstance(candidate, dict) or candidate.get("evaluation_status") != "not_evaluated":
        raise ConversionError("candidate artifact must remain not_evaluated")

    source_hash = hashlib.sha256(candidate_bytes).hexdigest()
    scope_pages: list[str] = []
    if scope_path is not None:
        try:
            scope = json.loads(scope_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise ConversionError("unable to read competition scope") from exc
        if (
            not isinstance(scope, dict)
            or scope.get("source_candidate_sha256") != source_hash
            or scope.get("dataset_kind") != "competition_evaluation_scope"
        ):
            raise ConversionError("competition scope is stale or invalid")
        scope_pages = [p["page_id"] for p in scope["pages"]]
        if not set(scope_pages).issubset({p["page_id"] for p in candidate["pages"]}):
            raise ConversionError("competition scope contains unknown pages")
    asset_root = asset_dir.resolve()
    if project_root.resolve() not in asset_root.parents:
        raise ConversionError("review assets must stay inside the project root")
    asset_root = asset_root / source_hash[:16]
    asset_root.mkdir(parents=True, exist_ok=True)
    asset_prefix = Path(asset_root.relative_to(output_path.parent.resolve())).as_posix()
    items: list[dict[str, Any]] = []
    total_boxes = 0
    focused_boxes = 0
    for page_raw in cast(list[Any], candidate.get("pages", [])):
        if not isinstance(page_raw, dict):
            continue
        page = cast(dict[str, Any], page_raw)
        page_id = str(page["page_id"])
        if not re.fullmatch(r"[A-Za-z0-9._-]+", page_id):
            raise ConversionError("unsafe review page identifier")
        image_path = (project_root / str(page["image_path"])).resolve()
        if project_root.resolve() not in image_path.parents:
            raise ConversionError("candidate image escapes the project root")
        if not image_path.is_file():
            raise ConversionError("candidate image does not exist")
        if (
            page.get("image_sha256")
            and hashlib.sha256(image_path.read_bytes()).hexdigest() != page["image_sha256"]
        ):
            raise ConversionError("candidate image hash mismatch")
        page_asset = asset_root / f"{page_id}.png"
        if not page_asset.exists():
            shutil.copyfile(image_path, page_asset)
        for record_raw in cast(list[Any], page.get("boxes", [])):
            if not isinstance(record_raw, dict):
                continue
            total_boxes += 1
            record = cast(dict[str, Any], record_raw)
            if record.get("verification_state") != "inferred":
                raise ConversionError("candidate box is not inferred")
            reasons = _box_review_reasons(record)
            focused_boxes += int(bool(reasons))
            item_id = str(record["box_id"])
            if not re.fullmatch(re.escape(page_id) + r"-b\d{3}", item_id):
                raise ConversionError("unsafe review box identifier")
            crop_name = f"{item_id}.jpg"
            _crop(
                image_path=image_path,
                bbox=cast(dict[str, Any], record["bbox"]),
                output_path=asset_root / crop_name,
            )
            items.append(
                {
                    **record,
                    "id": item_id,
                    "kind": "box",
                    "page_id": page_id,
                    "crop_path": f"{asset_prefix}/{crop_name}",
                    "page_image_path": f"{asset_prefix}/{page_asset.name}",
                    "reasons": reasons,
                    "priority": _priority(reasons) if reasons else "deferred",
                }
            )
        for figure_raw in cast(list[Any], page.get("figures", [])):
            if not isinstance(figure_raw, dict):
                continue
            figure = cast(dict[str, Any], figure_raw)
            if figure.get("verification_state") != "inferred":
                raise ConversionError("candidate figure is not inferred")
            item_id = str(figure["figure_id"])
            if not re.fullmatch(re.escape(page_id) + r"-f\d{2}", item_id):
                raise ConversionError("unsafe review figure identifier")
            crop_name = f"{item_id}.jpg"
            _crop(
                image_path=image_path,
                bbox=cast(dict[str, Any], figure["bbox"]),
                output_path=asset_root / crop_name,
            )
            items.append(
                {
                    **figure,
                    "id": item_id,
                    "kind": "figure",
                    "page_id": page_id,
                    "crop_path": f"{asset_prefix}/{crop_name}",
                    "page_image_path": f"{asset_prefix}/{page_asset.name}",
                    "raw_text": None,
                    "server_ocr": None,
                    "reference_candidate": None,
                    "reading_order": None,
                    "role_candidate": "technical_figure",
                    "reasons": ["technical_figure_region"],
                    "priority": "review",
                }
            )
            title_bbox = figure.get("candidate_title_bbox")
            if isinstance(title_bbox, dict) and figure.get("caption_box_id") is None:
                title_id = f"{item_id}-title"
                _crop(
                    image_path=image_path,
                    bbox=title_bbox,
                    output_path=asset_root / f"{title_id}.jpg",
                )
                items.append(
                    {
                        "id": title_id,
                        "kind": "caption",
                        "figure_id": item_id,
                        "page_id": page_id,
                        "bbox": title_bbox,
                        "crop_path": f"{asset_prefix}/{title_id}.jpg",
                        "page_image_path": f"{asset_prefix}/{page_asset.name}",
                        "category_candidate": "caption",
                        "role_candidate": "figure_title",
                        "normalized_candidate": figure["candidate_title"],
                        "raw_text": None,
                        "reading_order": None,
                        "verification_state": "inferred",
                        "reasons": ["missing_caption_box"],
                        "priority": "critical",
                        "ai_review_hint": figure.get("title_ai_review_hint"),
                    }
                )

    ai_seed = candidate.get("ai_review_seed", []) if review_origin == "ai_assisted" else []
    if ai_review_path is not None:
        hints = _read_json_object(ai_review_path)
        if (
            hints.get("dataset_kind") != "ai_assisted_review_overrides"
            or hints.get("source_candidate_sha256") != source_hash
            or hints.get("review_origin") != "ai_assisted"
            or hints.get("input_hashes") != candidate.get("input_hashes", {})
        ):
            raise ConversionError("AI hint export is stale or has an invalid origin")
        by_id = {item["id"]: item for item in items}
        seen: set[str] = set()
        for hint in hints.get("records", []):
            item_id = hint.get("box_or_figure_id")
            if (
                item_id not in by_id
                or item_id in seen
                or hint.get("kind") != by_id[item_id]["kind"]
                or hint.get("page_id") != by_id[item_id]["page_id"]
                or hint.get("review_origin") != "ai_assisted"
                or hint.get("verification_state") != "inferred"
                or hint.get("requires_human_confirmation") is not True
            ):
                raise ConversionError("AI hint cannot create a human confirmation")
            _bbox(hint)
            by_id[item_id]["ai_review_hint"] = hint
            seen.add(item_id)
        if review_origin == "ai_assisted":
            # Restore the actual export, rather than stale pre-review migration
            # seeds. Human queues keep an empty seed and never inherit checks.
            ai_seed = hints.get("records", [])
    items.sort(key=lambda item: (item["page_id"], item.get("reading_order") or 10_000, item["id"]))
    payload: dict[str, Any] = {
        "schema_version": "1.0",
        "review_origin": review_origin,
        "core_page_ids": scope_pages,
        "dataset_kind": "real_pilot_ai_assisted_review_queue" if review_origin == "ai_assisted" else "real_pilot_focused_human_review_queue",
        "evaluation_status": "not_evaluated",
        "pipeline_version": PIPELINE_VERSION,
        "source_id": candidate.get("source_id"),
        "input_hashes": candidate.get("input_hashes", {}),
        "source_candidate_sha256": source_hash,
        "ai_hint_export_sha256": hashlib.sha256(ai_review_path.read_bytes()).hexdigest() if ai_review_path else None,
        "revision": candidate.get("revision"),
        "ai_review_seed": ai_seed,
        "statistics": {
            "total_boxes": total_boxes,
            "focused_boxes": focused_boxes,
            "figure_regions": sum(item["kind"] == "figure" for item in items),
            "queue_items": sum(item["priority"] != "deferred" for item in items),
            "all_items": len(items),
            "missing_caption_candidates": sum(item["kind"] == "caption" for item in items),
            "critical_items": sum(item["priority"] == "critical" for item in items),
            "deferred_candidates": total_boxes - focused_boxes,
            "human_verified": 0,
        },
        "items": items,
        "disclaimer": (
            "Queue entries are inferred until a reviewer compares each crop with the "
            "scan and exports an explicit override. Deferred consensus is not verified."
        ),
    }
    item_ids = {item["id"] for item in items}
    for seed in payload["ai_review_seed"]:
        if (
            seed.get("box_or_figure_id") not in item_ids
            or seed.get("review_origin") != "ai_assisted"
            or seed.get("verification_state") != "inferred"
            or seed.get("requires_human_confirmation") is not True
        ):
            raise ConversionError("review seed must remain AI-assisted and pending human review")
    _write_json_atomic(manifest_path, payload)
    output_path.write_text(_render_html(payload), encoding="utf-8", newline="\n")
    return payload


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--scope", type=Path)
    parser.add_argument("--ai-assisted", action="store_true")
    parser.add_argument("--candidate", type=Path, default=CANDIDATE_PATH)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--manifest", type=Path)
    parser.add_argument("--assets", type=Path, default=ASSET_DIR)
    parser.add_argument("--ai-review", type=Path)
    args = parser.parse_args()
    try:
        payload = build_review_queue(
            candidate_path=args.candidate,
            scope_path=args.scope,
            ai_review_path=args.ai_review,
            asset_dir=args.assets,
            review_origin="ai_assisted" if args.ai_assisted else "human",
            output_path=args.output or (OUTPUT_PATH.with_name("model_review_queue.ai.html") if args.ai_assisted else OUTPUT_PATH),
            manifest_path=args.manifest or (MANIFEST_PATH.with_name("model_review_queue.ai.json") if args.ai_assisted else MANIFEST_PATH),
        )
    except ConversionError as exc:
        parser.error(str(exc))
    print(json.dumps(payload["statistics"], ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
