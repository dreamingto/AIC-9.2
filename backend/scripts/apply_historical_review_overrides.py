"""Validate explicit human review against the exact model-candidate inputs."""

from __future__ import annotations

import hashlib
import json
import math
from datetime import datetime
from pathlib import Path
from typing import Any

from scripts.annotation_errors import ConversionError


def _object_file(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ConversionError(f"unable to read review file: {path.name}") from exc
    if not isinstance(value, dict):
        raise ConversionError("review file must contain an object")
    return value


def _review_identity(record: dict[str, Any]) -> None:
    reviewer = record.get("reviewer")
    if not isinstance(reviewer, str) or not reviewer.strip() or len(reviewer) > 200:
        raise ConversionError("human review requires a reviewer")
    try:
        reviewed_at = datetime.fromisoformat(str(record.get("reviewed_at")))
    except ValueError as exc:
        raise ConversionError("human review requires an ISO reviewed_at") from exc
    if reviewed_at.tzinfo is None:
        raise ConversionError("reviewed_at requires a timezone")
    if record.get("confirmed") is not True:
        raise ConversionError("human review must be explicitly confirmed")


def _bbox(record: dict[str, Any]) -> dict[str, float]:
    raw = record.get("bbox")
    if not isinstance(raw, dict):
        raise ConversionError("review bbox is required")
    result: dict[str, float] = {}
    for field in ("x", "y", "width", "height"):
        value = raw.get(field)
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise ConversionError("review bbox values must be finite numbers")
        result[field] = float(value)
    x, y, w, h = (result[field] for field in ("x", "y", "width", "height"))
    if not all(math.isfinite(v) for v in (x, y, w, h)):
        raise ConversionError("review bbox values must be finite")
    if x < 0 or y < 0 or w <= 0 or h <= 0 or x + w > 1 or y + h > 1:
        raise ConversionError("review bbox is outside the page")
    return result


def apply_review_overrides(
    annotation: dict[str, Any],
    *,
    override_path: Path,
    candidate_path: Path,
    input_hashes: dict[str, str],
) -> None:
    """Apply a cumulative export after every record has passed validation."""

    overrides = _object_file(override_path)
    candidate = _object_file(candidate_path)
    candidate_hash = hashlib.sha256(candidate_path.read_bytes()).hexdigest()
    if (
        overrides.get("dataset_kind") != "human_review_overrides"
        or overrides.get("schema_version") != "1.0"
        or candidate.get("dataset_kind") != "real_pilot_model_assisted_review_candidates"
        or candidate.get("evaluation_status") != "not_evaluated"
    ):
        raise ConversionError("review artifact kind or state is invalid")
    if (
        overrides.get("review_origin", "human") != "human"
        or overrides.get("requires_human_confirmation") is True
    ):
        raise ConversionError("AI-assisted review cannot be accepted as human truth")
    if overrides.get("source_candidate_sha256") != candidate_hash:
        raise ConversionError("review candidate hash mismatch; reopen the matching queue")
    source_id = annotation["source_id"]
    if overrides.get("source_id") != source_id or candidate.get("source_id") != source_id:
        raise ConversionError("review source_id mismatch")
    for name, digest in input_hashes.items():
        if candidate.get("input_hashes", {}).get(name) != digest:
            raise ConversionError(f"candidate {name} differs from the current input")
        if overrides.get("input_hashes", {}).get(name) != digest:
            raise ConversionError(f"review {name} differs from the current input")

    items: dict[str, tuple[str, str, dict[str, Any]]] = {}
    page_candidates: dict[str, dict[str, Any]] = {}
    for page in candidate.get("pages", []):
        page_id = page["page_id"]
        if page_id not in annotation["pages"]:
            raise ConversionError("candidate contains a page outside the annotations")
        page_candidates[page_id] = page
        for box in page.get("boxes", []):
            if box.get("original_box_index") is None:
                if box.get("origin") != "ai_supplemental_region" or box.get("raw_text") is not None:
                    raise ConversionError("supplemental region must not fabricate raw OCR")
                _bbox(box)
            items[box["box_id"]] = (page_id, "box", box)
        for figure in page.get("figures", []):
            items[figure["figure_id"]] = (page_id, "figure", figure)
            if figure.get("caption_box_id") is None and figure.get("candidate_title_bbox"):
                items[figure["figure_id"] + "-title"] = (page_id, "caption", figure)

    records = overrides.get("records")
    if not isinstance(records, list):
        raise ConversionError("review records must be an array")
    accepted: dict[str, dict[str, Any]] = {}
    for record in records:
        if not isinstance(record, dict):
            raise ConversionError("review record must be an object")
        item_id = record.get("box_or_figure_id")
        if not isinstance(item_id, str) or item_id not in items or item_id in accepted:
            raise ConversionError("review contains an unknown or duplicate item")
        page_id, kind, original = items[item_id]
        if record.get("page_id") != page_id or record.get("kind") != kind:
            raise ConversionError("review item page or kind mismatch")
        if (
            record.get("verification_state") != "verified"
            or record.get("evidence") != "scan_level_human_review"
            or record.get("review_origin", "human") != "human"
            or record.get("requires_human_confirmation") is True
        ):
            raise ConversionError("model candidates cannot be accepted as human review")
        _review_identity(record)
        bbox = _bbox(record)
        category = record.get("category")
        if category not in {"text", "caption", "figure", "annotation", "unknown"}:
            raise ConversionError("review category is unsupported")
        role = record.get("role")
        if role is not None and (not isinstance(role, str) or len(role) > 120):
            raise ConversionError("review role is invalid")
        text = record.get("corrected_text")
        if text is not None and (
            not isinstance(text, str) or not text.strip() or len(text) > 2000 or "\ufffd" in text
        ):
            raise ConversionError("corrected text is empty, damaged, or too long")
        if category in {"text", "caption"} and text is None:
            raise ConversionError("confirmed text/caption requires corrected text")
        order = record.get("reading_order")
        if kind == "box" and (
            isinstance(order, bool)
            or not isinstance(order, int)
            or order < 1
            or order > len(page_candidates[page_id]["boxes"])
        ):
            raise ConversionError("review reading_order is outside the page")
        if original.get("verification_state") != "inferred":
            raise ConversionError("source item must be an inferred candidate")
        accepted[item_id] = {**record, "bbox": bbox}

    page_reviews: dict[str, dict[str, Any]] = {}
    for review in overrides.get("page_reviews", []):
        if not isinstance(review, dict):
            raise ConversionError("page review must be an object")
        _review_identity(review)
        page_id = review.get("page_id")
        if (
            not isinstance(page_id, str)
            or page_id not in page_candidates
            or page_id in page_reviews
        ):
            raise ConversionError("unknown or duplicate page review")
        orders = [
            accepted.get(box["box_id"], {}).get("reading_order", box["reading_order"])
            for box in page_candidates[page_id]["boxes"]
        ]
        if sorted(orders) != list(range(1, len(orders) + 1)):
            raise ConversionError("reviewed page reading_order must be a complete permutation")
        page_reviews[page_id] = review

    inventories: dict[str, dict[str, Any]] = {}
    for review in overrides.get("page_inventory_reviews", []):
        if not isinstance(review, dict):
            raise ConversionError("page inventory review must be an object")
        _review_identity(review)
        page_id = review.get("page_id")
        if not isinstance(page_id, str) or page_id not in page_candidates or page_id in inventories:
            raise ConversionError("unknown or duplicate page inventory review")
        if review.get("text_complete") is not True or review.get("captions_complete") is not True:
            raise ConversionError("page inventory requires explicit completeness confirmation")
        if page_id not in page_reviews:
            raise ConversionError("page inventory requires reviewed reading order")
        required_ids = {b["box_id"] for b in page_candidates[page_id]["boxes"]}
        required_ids.update(
            f["figure_id"] + "-title"
            for f in page_candidates[page_id].get("figures", [])
            if f.get("caption_box_id") is None and f.get("candidate_title_bbox")
        )
        if not required_ids.issubset(accepted):
            raise ConversionError("page inventory cannot confirm unreviewed text/title items")
        actual_captions = sorted(
            item_id
            for item_id, decision in accepted.items()
            if items[item_id][0] == page_id
            and decision["category"] == "caption"
            and decision["role"] == "figure_title"
        )
        if review.get("caption_ids") != actual_captions:
            raise ConversionError("page inventory caption_ids differ from confirmed titles")
        inventories[page_id] = review

    reviewed_text_boxes = 0
    for page_id, candidate_page in page_candidates.items():
        page = annotation["pages"][page_id]
        lines: list[dict[str, Any]] = []
        for box in candidate_page["boxes"]:
            item_id = box["box_id"]
            decision = accepted.get(item_id)
            index = box["original_box_index"]
            if index is None:
                region = {
                    "region_id": item_id,
                    "category": box["category_candidate"],
                    "role": box["role_candidate"],
                    "bbox": box["bbox"],
                    "polygon": box["polygon"],
                    "reading_order": box["reading_order"],
                    "review_state": "unreviewed",
                    "verification_state": "inferred",
                    "origin": "ai_supplemental_region",
                }
                page["layout"]["regions"].append(region)
            else:
                region = page["layout"]["regions"][index - 1]
            region["box_id"] = item_id
            if decision:
                region.update(
                    {
                        "category": decision["category"],
                        "role": decision["role"],
                        "bbox": decision["bbox"],
                        "reading_order": decision["reading_order"],
                        "verification_state": "verified",
                        "review_state": "reviewed",
                        "reviewer": decision["reviewer"],
                        "reviewed_at": decision["reviewed_at"],
                    }
                )
                b = decision["bbox"]
                x, y = b["x"] * page["width"], b["y"] * page["height"]
                w, h = b["width"] * page["width"], b["height"] * page["height"]
                region["polygon"] = [[x, y], [x + w, y], [x + w, y + h], [x, y + h]]
                if decision["corrected_text"] is not None:
                    reviewed_text_boxes += 1
                    lines.append(
                        {
                            "line_id": item_id,
                            "text": decision["corrected_text"],
                            "reading_order": decision["reading_order"],
                            "review_state": "reviewed",
                            "reviewer": decision["reviewer"],
                            "reviewed_at": decision["reviewed_at"],
                            "bbox": decision["bbox"],
                            "polygon": region["polygon"],
                        }
                    )
                page["text_layers"]["change_log"].append(
                    {
                        "box_id": item_id,
                        "from": box["raw_text"],
                        "to": decision["corrected_text"],
                        "category": decision["category"],
                        "reading_order": decision["reading_order"],
                        "reviewer": decision["reviewer"],
                        "changed_at": decision["reviewed_at"],
                        "reason": "scan_level_human_review",
                        "source_candidate_sha256": candidate_hash,
                    }
                )
            elif page_id in page_reviews:
                region["reading_order"] = box["reading_order"]

        if page_id in page_reviews:
            page["layout"]["orientation"] = "vertical_right_to_left"
            page["layout"]["reading_order"] = [
                r["region_id"]
                for r in sorted(page["layout"]["regions"], key=lambda r: r["reading_order"])
            ]
            page["layout"]["reading_order_review"] = page_reviews[page_id]
        lines.sort(key=lambda line: line["reading_order"])
        complete = (
            bool(candidate_page["boxes"])
            and all(box["box_id"] in accepted for box in candidate_page["boxes"])
            and page_id in page_reviews
        )
        page["text_layers"].update(
            {
                "corrected_lines": lines,
                "corrected_text": "\n".join(line["text"] for line in lines) if complete else None,
                "correction_state": "reviewed"
                if complete
                else "partial"
                if lines
                else "unreviewed",
                "reviewer": page_reviews[page_id]["reviewer"] if complete else None,
                "reviewed_at": page_reviews[page_id]["reviewed_at"] if complete else None,
            }
        )
        figures: list[dict[str, Any]] = []
        for figure in candidate_page.get("figures", []):
            figure_id = figure["figure_id"]
            decision = accepted.get(figure_id)
            title_id = figure.get("caption_box_id") or figure_id + "-title"
            title = accepted.get(title_id)
            title_verified = bool(
                title
                and title["category"] == "caption"
                and title["role"] == "figure_title"
                and title["corrected_text"]
            )
            figures.append(
                {
                    "figure_id": figure_id,
                    "bbox": decision["bbox"] if decision else figure["bbox"],
                    "region_verification_state": "verified"
                    if decision and decision["category"] == "figure"
                    else "inferred",
                    "title": title["corrected_text"] if title_verified and title else None,
                    "title_verification_state": "verified" if title_verified else "inferred",
                    "title_box_id": title_id,
                    "title_review": title if title_verified else None,
                }
            )
        page["figures"] = figures
        for item_id, decision in accepted.items():
            decision_page, kind, _ = items[item_id]
            if decision_page != page_id or kind == "box":
                continue
            region_order = len(page["layout"]["regions"]) + 1
            page["layout"]["regions"].append(
                {
                    "region_id": item_id,
                    "category": decision["category"],
                    "role": decision["role"],
                    "bbox": decision["bbox"],
                    "reading_order": region_order,
                    "review_state": "reviewed",
                    "verification_state": "verified",
                    "reviewer": decision["reviewer"],
                    "reviewed_at": decision["reviewed_at"],
                }
            )
            page["layout"]["reading_order"].append(item_id)
        page["provenance"]["review_candidate_sha256"] = candidate_hash
        if page_id in inventories:
            page["layout"]["content_inventory_review"] = inventories[page_id]

    annotation["review_import"] = {
        "source_candidate_sha256": candidate_hash,
        "override_sha256": hashlib.sha256(override_path.read_bytes()).hexdigest(),
        "accepted_records": len(accepted),
        "reviewed_text_boxes": reviewed_text_boxes,
        "reading_order_reviewed_pages": len(page_reviews),
        "content_inventory_reviewed_pages": len(inventories),
        "caption_ground_truth_verified": sum(
            f["title_verification_state"] == "verified"
            for page in annotation["pages"].values()
            for f in page.get("figures", [])
        ),
    }
    annotation["statistics"]["transcription_reviewed_pages"] = sum(
        page["text_layers"]["correction_state"] == "reviewed"
        for page in annotation["pages"].values()
    )
    annotation["statistics"]["unreviewed_transcription_pages"] = (
        annotation["statistics"]["imported_pages"]
        - annotation["statistics"]["transcription_reviewed_pages"]
    )
