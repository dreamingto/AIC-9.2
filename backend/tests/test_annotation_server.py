from __future__ import annotations

from typing import Any

import pytest

from scripts.annotation_server import AnnotationError, _validate_annotation, _validate_bbox


def _annotation(**text_overrides: Any) -> dict[str, Any]:
    text_layers: dict[str, Any] = {
        "corrected_text": "天工開物",
        "reviewer": "researcher-01",
        "change_log": [],
    }
    text_layers.update(text_overrides)
    return {
        "layout": {
            "orientation": "vertical_columns",
            "regions": [
                {
                    "region_id": "page-a-r001",
                    "category": "text",
                    "bbox": {"x": 0.1, "y": 0.1, "width": 0.3, "height": 0.7},
                    "reading_order": 1,
                }
            ],
            "reading_order": ["page-a-r001"],
        },
        "text_layers": text_layers,
    }


def test_annotation_keeps_raw_and_corrected_layers_separate() -> None:
    result = _validate_annotation("page-a", _annotation(), "天工开物")

    assert result["text_layers"]["raw_ocr"] == "天工开物"
    assert result["text_layers"]["corrected_text"] == "天工開物"
    assert result["text_layers"]["correction_state"] == "reviewed"
    assert result["layout"]["status"] == "reviewed"


@pytest.mark.parametrize(
    "bbox",
    [
        {"x": -0.1, "y": 0.0, "width": 0.2, "height": 0.2},
        {"x": 0.9, "y": 0.0, "width": 0.2, "height": 0.2},
        {"x": 0.1, "y": 0.1, "width": 0.0, "height": 0.2},
        {"x": float("nan"), "y": 0.1, "width": 0.2, "height": 0.2},
        {"x": True, "y": 0.1, "width": 0.2, "height": 0.2},
    ],
)
def test_annotation_rejects_invalid_bbox(bbox: dict[str, float]) -> None:
    with pytest.raises(AnnotationError):
        _validate_bbox(bbox)


def test_annotation_rejects_unknown_category() -> None:
    payload = _annotation()
    payload["layout"]["regions"][0]["category"] = "table"

    with pytest.raises(AnnotationError, match="category"):
        _validate_annotation("page-a", payload, "raw")
