"""Keep figure context out of a local query unless its location is demonstrated."""

from __future__ import annotations

import json
from collections.abc import Mapping
from typing import Any

from app.db.models import Figure
from app.ingestion.contracts import NormalizedBBox
from app.services.ingestion_service import stable_id


def contained(inner: Mapping[str, Any], outer: Mapping[str, Any]) -> bool:
    try:
        a = NormalizedBBox.model_validate(dict(inner))
        b = NormalizedBBox.model_validate(dict(outer))
    except (ValueError, TypeError):
        return False
    return (
        a.x >= b.x - 1e-9 and a.y >= b.y - 1e-9
        and a.x + a.width <= b.x + b.width + 1e-9
        and a.y + a.height <= b.y + b.height + 1e-9
    )


def _decode(pointer: str | None) -> dict[str, Any]:
    try:
        value = json.loads(pointer or "null")
        return value if isinstance(value, dict) else {}
    except (ValueError, TypeError):
        return {}


def _located(pointer: str | None, figure: Figure, crop: Mapping[str, Any]) -> bool:
    value = _decode(pointer)
    if not value and pointer:
        audit = (figure.provenance or {}).get("ai_review", {})
        reviewed = (figure.provenance or {}).get("human_review", {})
        traces = audit.get("text_traces", []) + reviewed.get("transcriptions", [])
        value = next((t for t in traces if t.get("text_id") == pointer), {})
    if value.get("page_id") and str(value["page_id"]) not in {
        str(figure.page_id), str((figure.provenance or {}).get("page_key", "")),
    }:
        # AI trace uses logical page keys; resolve them with the same UUID policy.
        if str(stable_id("page", str(value["page_id"]))) != str(figure.page_id):
            return False
    supports = value.get("supports")
    if isinstance(supports, list):
        return bool(supports) and all(
            isinstance(s, dict) and isinstance(s.get("bbox"), dict)
            and contained(s["bbox"], crop) for s in supports
        )
    bbox = value.get("bbox")
    if isinstance(bbox, dict):
        return contained(bbox, crop)
    # Plain legacy pointers have no spatial scope; never infer a location.
    return False


def scoped_region_context(
    figure: Figure, crop: Mapping[str, Any],
) -> tuple[str, list[dict[str, Any]], list[dict[str, Any]]]:
    texts = [
        c.corrected_text or c.text for c in figure.text_chunks
        if _located(c.source_pointer, figure, crop)
    ]
    assertions = [
        {"slot": a.slot, "concept": a.concept, "confidence": a.confidence, "status": a.state}
        for a in figure.assertions if _located(a.evidence_pointer, figure, crop)
    ]
    # Relation has no evidence/location column. It may enter a whole-figure query
    # only; a local crop must not inherit its endpoints from figure context.
    figure_box = {
        "x": figure.bbox_x, "y": figure.bbox_y,
        "width": figure.bbox_width, "height": figure.bbox_height,
    }
    relations = [
        {"subject": r.subject, "predicate": r.predicate, "object": r.object,
         "confidence": r.confidence}
        for r in figure.relations
    ] if contained(figure_box, crop) else []
    return " ".join(texts), assertions, relations
