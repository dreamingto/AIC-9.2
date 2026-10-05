from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

import pytest

from scripts.audit_ppocrlabel_annotations import (
    _edit_distance,
    audit_ppocrlabel_annotations,
)

SOURCE_ID = "source-a"
PAGE_KEY = f"{SOURCE_ID}/page-0001.png"


def _box(text: str, x: int = 10) -> dict[str, Any]:
    return {
        "transcription": text,
        "points": [[x, 20], [x + 20, 20], [x + 20, 60], [x, 60]],
        "difficult": False,
    }


def _write_tsv(path: Path, rows: list[tuple[str, Any]]) -> None:
    path.write_text(
        "".join(f"{key}\t{json.dumps(value, ensure_ascii=False)}\n" for key, value in rows),
        encoding="utf-8",
    )


def _workspace(tmp_path: Path) -> tuple[Path, Path, Path, Path]:
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
    (source_dir / "fileState.txt").write_text(f"{PAGE_KEY}\t1\n", encoding="utf-8")
    return processed_root, source_dir, inventory_path, tmp_path / "audit.json"


def test_edit_distance_boundaries() -> None:
    assert _edit_distance([], []) == 0
    assert _edit_distance(list("甲乙"), list("甲丙")) == 1
    assert _edit_distance(list("甲"), list("甲乙")) == 1


def test_audit_blocks_corrupt_transcription_and_known_noise(tmp_path: Path) -> None:
    processed_root, source_dir, inventory_path, output_path = _workspace(tmp_path)
    _write_tsv(source_dir / "Cache.cach", [(PAGE_KEY, [_box("原文"), _box("噪声", 40)])])
    _write_tsv(
        source_dir / "Label.txt",
        [(PAGE_KEY, [_box("损坏�"), _box("National Archives of Japan", 40)])],
    )

    report = audit_ppocrlabel_annotations(
        source_id=SOURCE_ID,
        inventory_path=inventory_path,
        output_path=output_path,
        project_root=tmp_path,
        processed_root=processed_root,
    )

    assert report["layout_snapshot_ready"] is True
    assert report["transcription_evaluation_ready"] is False
    assert report["evaluation_status"] == "not_evaluated"
    assert report["summary"]["replacement_character_pages"] == ["source-a-p0001"]
    assert report["summary"]["known_noise_pages"] == ["source-a-p0001"]
    assert report["metrics"]["cer"]["value"] is None
    assert output_path.is_file()


def test_audit_calculates_text_metrics_only_after_explicit_acceptance(tmp_path: Path) -> None:
    processed_root, source_dir, inventory_path, output_path = _workspace(tmp_path)
    _write_tsv(source_dir / "Cache.cach", [(PAGE_KEY, [_box("甲乙")])])
    _write_tsv(source_dir / "Label.txt", [(PAGE_KEY, [_box("甲丙")])])

    report = audit_ppocrlabel_annotations(
        source_id=SOURCE_ID,
        inventory_path=inventory_path,
        output_path=output_path,
        project_root=tmp_path,
        processed_root=processed_root,
        accept_transcription_review=True,
    )

    assert report["transcription_evaluation_ready"] is True
    assert report["metrics"]["cer"]["value"] == pytest.approx(0.5)
    assert report["metrics"]["wer_mixed_cjk_tokens"]["value"] == pytest.approx(0.5)
    assert report["metrics"]["figure_title_recall"]["value"] is None
    assert report["evaluation_set_freeze_ready"] is False
