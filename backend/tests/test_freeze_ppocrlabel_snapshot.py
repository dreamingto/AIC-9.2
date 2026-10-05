from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

import pytest

from scripts.convert_ppocrlabel_annotations import ConversionError
from scripts.freeze_ppocrlabel_snapshot import freeze_layout_snapshot

SOURCE_ID = "source-a"
PAGE_KEY = f"{SOURCE_ID}/page-0001.png"


def _box(text: str) -> dict[str, Any]:
    return {
        "transcription": text,
        "points": [[10, 20], [30, 20], [30, 60], [10, 60]],
        "difficult": False,
    }


def _write_tsv(path: Path, rows: list[tuple[str, Any]]) -> None:
    path.write_text(
        "".join(f"{key}\t{json.dumps(value, ensure_ascii=False)}\n" for key, value in rows),
        encoding="utf-8",
    )


def _workspace(tmp_path: Path, *, confirmed: bool = True) -> dict[str, Path]:
    processed_root = tmp_path / "processed"
    source_dir = processed_root / SOURCE_ID
    source_dir.mkdir(parents=True)
    image_path = source_dir / "page-0001.png"
    image_path.write_bytes(b"controlled-page-bytes")
    inventory_path = tmp_path / "derived_pages.json"
    inventory_path.write_text(
        json.dumps(
            {
                "dataset_kind": "real_pilot_page_inventory",
                "evaluation_status": "not_evaluated",
                "pages": [
                    {
                        "page_id": "source-a-p0001",
                        "source_id": SOURCE_ID,
                        "image_path": "processed/source-a/page-0001.png",
                        "width": 100,
                        "height": 200,
                        "sha256": hashlib.sha256(image_path.read_bytes()).hexdigest(),
                        "provenance": {"source_name": "test"},
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    _write_tsv(source_dir / "Cache.cach", [(PAGE_KEY, [_box("机器字")])])
    _write_tsv(source_dir / "Label.txt", [(PAGE_KEY, [_box("人工字")])])
    (source_dir / "fileState.txt").write_text(
        f"{PAGE_KEY}\t1\n" if confirmed else "", encoding="utf-8"
    )
    return {
        "processed_root": processed_root,
        "inventory_path": inventory_path,
        "annotation_path": tmp_path / "annotations.json",
        "audit_path": tmp_path / "audit.json",
        "freeze_root": tmp_path / "frozen",
    }


def test_freeze_layout_snapshot_is_content_addressed_and_idempotent(tmp_path: Path) -> None:
    paths = _workspace(tmp_path)
    manifest = freeze_layout_snapshot(
        reviewer="reviewer-01",
        source_id=SOURCE_ID,
        inventory_path=paths["inventory_path"],
        annotation_output_path=paths["annotation_path"],
        audit_output_path=paths["audit_path"],
        project_root=tmp_path,
        processed_root=paths["processed_root"],
        freeze_root=paths["freeze_root"],
    )

    target = paths["freeze_root"] / manifest["snapshot_id"]
    assert manifest["snapshot_scope"] == "layout_review_only"
    assert manifest["layout_reviewed_pages"] == 1
    assert manifest["transcription_reviewed_pages"] == 0
    assert target.is_dir()
    assert (target / "manifest.json").is_file()
    assert (target / "Label.txt").is_file()

    repeated = freeze_layout_snapshot(
        reviewer="reviewer-01",
        source_id=SOURCE_ID,
        inventory_path=paths["inventory_path"],
        annotation_output_path=paths["annotation_path"],
        audit_output_path=paths["audit_path"],
        project_root=tmp_path,
        processed_root=paths["processed_root"],
        freeze_root=paths["freeze_root"],
    )
    assert repeated == manifest
    assert len(list(paths["freeze_root"].iterdir())) == 1


def test_freeze_rejects_incomplete_file_state(tmp_path: Path) -> None:
    paths = _workspace(tmp_path, confirmed=False)

    with pytest.raises(ConversionError, match="quality gate"):
        freeze_layout_snapshot(
            reviewer="reviewer-01",
            source_id=SOURCE_ID,
            inventory_path=paths["inventory_path"],
            annotation_output_path=paths["annotation_path"],
            audit_output_path=paths["audit_path"],
            project_root=tmp_path,
            processed_root=paths["processed_root"],
            freeze_root=paths["freeze_root"],
        )
