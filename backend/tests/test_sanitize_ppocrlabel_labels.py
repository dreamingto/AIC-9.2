from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

import pytest

from scripts.convert_ppocrlabel_annotations import ConversionError
from scripts.sanitize_ppocrlabel_labels import sanitize_labels

SOURCE_ID = "commons-najda-tiangong-kaiwu-2"
PAGE_ID = f"{SOURCE_ID}-p0008"
PAGE_KEY = f"{SOURCE_ID}/page-0008.png"


def _box(text: str, *, x: int, y: int) -> dict[str, Any]:
    return {
        "transcription": text,
        "points": [[x, y], [x + 100, y], [x + 100, y + 20], [x, y + 20]],
        "difficult": False,
    }


def _workspace(tmp_path: Path) -> tuple[Path, Path, Path, Path]:
    processed_root = tmp_path / "processed"
    source_dir = processed_root / SOURCE_ID
    source_dir.mkdir(parents=True)
    image_path = source_dir / "page-0008.png"
    image_path.write_bytes(b"registered-page")
    inventory_path = tmp_path / "derived_pages.json"
    inventory_path.write_text(
        json.dumps(
            {
                "dataset_kind": "real_pilot_page_inventory",
                "evaluation_status": "not_evaluated",
                "pages": [
                    {
                        "page_id": PAGE_ID,
                        "source_id": SOURCE_ID,
                        "image_path": f"processed/{PAGE_KEY}",
                        "width": 1000,
                        "height": 1000,
                        "sha256": hashlib.sha256(image_path.read_bytes()).hexdigest(),
                        "provenance": {},
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    label_path = source_dir / "Label.txt"
    boxes = [
        _box("正文", x=100, y=100),
        _box("国立公文書館", x=860, y=910),
        _box("National Archives of Japan", x=870, y=940),
    ]
    label_path.write_text(
        f"{PAGE_KEY}\t{json.dumps(boxes, ensure_ascii=False)}\n", encoding="utf-8"
    )
    return processed_root, inventory_path, label_path, tmp_path / "audit.json"


def test_sanitizer_removes_only_registered_watermarks(tmp_path: Path) -> None:
    processed_root, inventory_path, label_path, audit_path = _workspace(tmp_path)

    result = sanitize_labels(
        inventory_path=inventory_path,
        processed_root=processed_root,
        project_root=tmp_path,
        audit_output_path=audit_path,
    )

    _, raw_json = label_path.read_text(encoding="utf-8").strip().split("\t", 1)
    assert [box["transcription"] for box in json.loads(raw_json)] == ["正文"]
    assert result["removed_count"] == 2
    assert result["label_sha256_before"] != result["label_sha256_after"]
    assert result["transcription_review_state"] == "unreviewed"


def test_sanitizer_is_idempotent_after_safe_removal(tmp_path: Path) -> None:
    processed_root, inventory_path, label_path, audit_path = _workspace(tmp_path)
    sanitize_labels(
        inventory_path=inventory_path,
        processed_root=processed_root,
        project_root=tmp_path,
        audit_output_path=audit_path,
    )
    first = label_path.read_bytes()

    second = sanitize_labels(
        inventory_path=inventory_path,
        processed_root=processed_root,
        project_root=tmp_path,
        audit_output_path=audit_path,
    )

    assert label_path.read_bytes() == first
    assert second["removed_count"] == 0
    assert second["label_sha256_before"] == second["label_sha256_after"]


def test_sanitizer_rejects_same_text_outside_safe_area(tmp_path: Path) -> None:
    processed_root, inventory_path, label_path, audit_path = _workspace(tmp_path)
    _, raw_json = label_path.read_text(encoding="utf-8").strip().split("\t", 1)
    boxes = json.loads(raw_json)
    boxes[1] = _box("国立公文書館", x=100, y=100)
    label_path.write_text(
        f"{PAGE_KEY}\t{json.dumps(boxes, ensure_ascii=False)}\n", encoding="utf-8"
    )

    with pytest.raises(ConversionError, match="outside the safe area"):
        sanitize_labels(
            inventory_path=inventory_path,
            processed_root=processed_root,
            project_root=tmp_path,
            audit_output_path=audit_path,
        )
