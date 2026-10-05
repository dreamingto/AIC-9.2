from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

import pytest

from scripts.convert_ppocrlabel_annotations import (
    ConversionError,
    convert_ppocrlabel_annotations,
)

SOURCE_ID = "source-a"
PAGE_KEY = f"{SOURCE_ID}/page-0001.png"


def _box(
    text: str = "天工開物", points: list[list[float]] | None = None
) -> dict[str, Any]:
    return {
        "transcription": text,
        "points": points or [[10, 20], [30, 20], [30, 60], [10, 60]],
        "difficult": False,
    }


def _write_workspace(tmp_path: Path) -> tuple[Path, Path, Path, Path]:
    processed_root = tmp_path / "processed"
    source_dir = processed_root / SOURCE_ID
    source_dir.mkdir(parents=True)
    image_path = source_dir / "page-0001.png"
    image_path.write_bytes(b"controlled-page-bytes")
    digest = hashlib.sha256(image_path.read_bytes()).hexdigest()
    inventory = {
        "schema_version": "1.0",
        "dataset_kind": "real_pilot_page_inventory",
        "evaluation_status": "not_evaluated",
        "pages": [
            {
                "page_id": "source-a-p0001",
                "source_id": SOURCE_ID,
                "image_path": "processed/source-a/page-0001.png",
                "width": 100,
                "height": 200,
                "sha256": digest,
                "provenance": {
                    "source_url": "https://example.test/source",
                    "pipeline_version": "test-pages-v1",
                },
            }
        ],
    }
    inventory_path = tmp_path / "derived_pages.json"
    inventory_path.write_text(json.dumps(inventory), encoding="utf-8")
    (source_dir / "Cache.cach").write_text("", encoding="utf-8")
    (source_dir / "Label.txt").write_text("", encoding="utf-8")
    (source_dir / "fileState.txt").write_text("", encoding="utf-8")
    output_path = tmp_path / "annotations.json"
    return processed_root, source_dir, inventory_path, output_path


def _write_tsv(path: Path, rows: list[tuple[str, Any]]) -> None:
    path.write_text(
        "".join(f"{key}\t{json.dumps(value, ensure_ascii=False)}\n" for key, value in rows),
        encoding="utf-8",
    )


def _convert(tmp_path: Path) -> tuple[dict[str, Any], Path, Path]:
    processed_root, source_dir, inventory_path, output_path = _write_workspace(tmp_path)
    _write_tsv(source_dir / "Cache.cach", [(PAGE_KEY, [_box()])])
    result = convert_ppocrlabel_annotations(
        source_id=SOURCE_ID,
        inventory_path=inventory_path,
        output_path=output_path,
        project_root=tmp_path,
        processed_root=processed_root,
    )
    return result, source_dir, output_path


def test_cache_import_stays_unreviewed_and_preserves_geometry(tmp_path: Path) -> None:
    result, _, _ = _convert(tmp_path)

    page = result["pages"]["source-a-p0001"]
    assert result["evaluation_status"] == "not_evaluated"
    assert result["statistics"] == {
        "total_pages": 1,
        "imported_pages": 1,
        "total_boxes": 1,
        "tool_confirmed_pages": 0,
        "layout_reviewed_pages": 0,
        "transcription_reviewed_pages": 0,
        "unreviewed_layout_pages": 1,
        "unreviewed_transcription_pages": 1,
        "skipped_pages": 0,
        "errors": [],
    }
    assert page["layout"]["status"] == "pending_review"
    assert page["layout"]["regions"][0]["review_state"] == "unreviewed"
    assert page["layout"]["regions"][0]["polygon"] == [
        [10.0, 20.0],
        [30.0, 20.0],
        [30.0, 60.0],
        [10.0, 60.0],
    ]
    assert page["layout"]["regions"][0]["bbox"] == {
        "x": 0.1,
        "y": 0.1,
        "width": 0.2,
        "height": 0.2,
    }
    assert page["text_layers"]["raw_ocr"] == "天工開物"
    assert page["text_layers"]["corrected_text"] is None
    assert page["text_layers"]["change_log"] == []
    assert page["provenance"]["source_kind"] == "ppocrlabel_cache"


def test_label_requires_file_state_before_becoming_corrected(tmp_path: Path) -> None:
    processed_root, source_dir, inventory_path, output_path = _write_workspace(tmp_path)
    _write_tsv(source_dir / "Cache.cach", [(PAGE_KEY, [_box("机器字")])])
    _write_tsv(source_dir / "Label.txt", [(PAGE_KEY, [_box("人工字")])])

    result = convert_ppocrlabel_annotations(
        source_id=SOURCE_ID,
        inventory_path=inventory_path,
        output_path=output_path,
        project_root=tmp_path,
        processed_root=processed_root,
    )

    page = result["pages"]["source-a-p0001"]
    assert page["text_layers"]["raw_ocr"] == "机器字"
    assert page["text_layers"]["corrected_text"] is None
    assert page["text_layers"]["correction_state"] == "unreviewed"
    assert result["statistics"]["transcription_reviewed_pages"] == 0


def test_file_state_acceptance_reviews_layout_but_not_transcription(tmp_path: Path) -> None:
    processed_root, source_dir, inventory_path, output_path = _write_workspace(tmp_path)
    _write_tsv(source_dir / "Cache.cach", [(PAGE_KEY, [_box("机器字")])])
    _write_tsv(source_dir / "Label.txt", [(PAGE_KEY, [_box("人工字")])])
    (source_dir / "fileState.txt").write_text(f"{PAGE_KEY}\t1\n", encoding="utf-8")

    result = convert_ppocrlabel_annotations(
        source_id=SOURCE_ID,
        inventory_path=inventory_path,
        output_path=output_path,
        project_root=tmp_path,
        processed_root=processed_root,
        reviewer="reviewer-01",
        accept_file_state=True,
    )

    page = result["pages"]["source-a-p0001"]
    assert page["layout"]["status"] == "reviewed"
    assert page["ocr"]["lines"][0]["text"] == "机器字"
    assert page["ocr"]["lines"][0]["review_state"] == "unreviewed"
    assert page["text_layers"]["corrected_text"] is None
    assert page["text_layers"]["corrected_lines"] == []
    assert page["text_layers"]["reviewer"] is None
    assert page["provenance"]["layout_reviewer"] == "reviewer-01"
    assert result["statistics"]["layout_reviewed_pages"] == 1
    assert result["statistics"]["transcription_reviewed_pages"] == 0


def test_transcription_review_is_a_separate_explicit_gate(tmp_path: Path) -> None:
    processed_root, source_dir, inventory_path, output_path = _write_workspace(tmp_path)
    _write_tsv(source_dir / "Cache.cach", [(PAGE_KEY, [_box("机器字")])])
    _write_tsv(source_dir / "Label.txt", [(PAGE_KEY, [_box("人工字")])])
    (source_dir / "fileState.txt").write_text(f"{PAGE_KEY}\t1\n", encoding="utf-8")

    result = convert_ppocrlabel_annotations(
        source_id=SOURCE_ID,
        inventory_path=inventory_path,
        output_path=output_path,
        project_root=tmp_path,
        processed_root=processed_root,
        reviewer="reviewer-01",
        accept_file_state=True,
        accept_transcription_review=True,
    )

    page = result["pages"]["source-a-p0001"]
    assert page["text_layers"]["corrected_text"] == "人工字"
    assert page["text_layers"]["corrected_lines"][0]["review_state"] == "reviewed"
    assert page["text_layers"]["reviewer"] == "reviewer-01"
    assert page["text_layers"]["change_log"][0]["from"] == "机器字"
    assert page["text_layers"]["change_log"][0]["to"] == "人工字"
    assert result["statistics"]["transcription_reviewed_pages"] == 1


def test_file_state_is_not_human_review_without_explicit_acceptance(tmp_path: Path) -> None:
    processed_root, source_dir, inventory_path, output_path = _write_workspace(tmp_path)
    _write_tsv(source_dir / "Cache.cach", [(PAGE_KEY, [_box("机器字")])])
    _write_tsv(source_dir / "Label.txt", [(PAGE_KEY, [_box("机器字")])])
    (source_dir / "fileState.txt").write_text(f"{PAGE_KEY}\t1\n", encoding="utf-8")

    result = convert_ppocrlabel_annotations(
        source_id=SOURCE_ID,
        inventory_path=inventory_path,
        output_path=output_path,
        project_root=tmp_path,
        processed_root=processed_root,
    )

    page = result["pages"]["source-a-p0001"]
    assert page["layout"]["status"] == "pending_review"
    assert page["text_layers"]["corrected_text"] is None
    assert page["provenance"]["ppocrlabel_file_state"] is True
    assert page["provenance"]["file_state_accepted_as_layout_review"] is False
    assert page["provenance"]["file_state_accepted_as_transcription_review"] is False
    assert result["statistics"]["tool_confirmed_pages"] == 1
    assert result["statistics"]["layout_reviewed_pages"] == 0
    assert result["statistics"]["transcription_reviewed_pages"] == 0


def test_accept_file_state_requires_reviewer(tmp_path: Path) -> None:
    processed_root, source_dir, inventory_path, output_path = _write_workspace(tmp_path)
    _write_tsv(source_dir / "Cache.cach", [(PAGE_KEY, [_box()])])

    with pytest.raises(ConversionError, match="reviewer"):
        convert_ppocrlabel_annotations(
            source_id=SOURCE_ID,
            inventory_path=inventory_path,
            output_path=output_path,
            project_root=tmp_path,
            processed_root=processed_root,
            accept_file_state=True,
        )


def test_transcription_review_requires_layout_review(tmp_path: Path) -> None:
    processed_root, source_dir, inventory_path, output_path = _write_workspace(tmp_path)
    _write_tsv(source_dir / "Cache.cach", [(PAGE_KEY, [_box()])])

    with pytest.raises(ConversionError, match="requires accept_file_state"):
        convert_ppocrlabel_annotations(
            source_id=SOURCE_ID,
            inventory_path=inventory_path,
            output_path=output_path,
            project_root=tmp_path,
            processed_root=processed_root,
            reviewer="reviewer-01",
            accept_transcription_review=True,
        )


def test_transcription_review_rejects_replacement_characters(tmp_path: Path) -> None:
    processed_root, source_dir, inventory_path, output_path = _write_workspace(tmp_path)
    _write_tsv(source_dir / "Cache.cach", [(PAGE_KEY, [_box("机器字")])])
    _write_tsv(source_dir / "Label.txt", [(PAGE_KEY, [_box("损坏�")])])
    (source_dir / "fileState.txt").write_text(f"{PAGE_KEY}\t1\n", encoding="utf-8")

    with pytest.raises(ConversionError, match="replacement"):
        convert_ppocrlabel_annotations(
            source_id=SOURCE_ID,
            inventory_path=inventory_path,
            output_path=output_path,
            project_root=tmp_path,
            processed_root=processed_root,
            reviewer="reviewer-01",
            accept_file_state=True,
            accept_transcription_review=True,
        )


@pytest.mark.parametrize(
    "points",
    [
        [[-1, 20], [30, 20], [30, 60], [10, 60]],
        [[10, 20], [101, 20], [30, 60], [10, 60]],
        [[10, 20], [30, 20], [float("nan"), 60], [10, 60]],
        [[10, 20], [30, 20], [float("inf"), 60], [10, 60]],
    ],
)
def test_rejects_out_of_bounds_and_non_finite_points(
    tmp_path: Path, points: list[list[float]]
) -> None:
    processed_root, source_dir, inventory_path, output_path = _write_workspace(tmp_path)
    _write_tsv(source_dir / "Cache.cach", [(PAGE_KEY, [_box(points=points)])])

    with pytest.raises(ConversionError):
        convert_ppocrlabel_annotations(
            source_id=SOURCE_ID,
            inventory_path=inventory_path,
            output_path=output_path,
            project_root=tmp_path,
            processed_root=processed_root,
        )


def test_rejects_invalid_json(tmp_path: Path) -> None:
    processed_root, source_dir, inventory_path, output_path = _write_workspace(tmp_path)
    (source_dir / "Cache.cach").write_text(f"{PAGE_KEY}\t[invalid]\n", encoding="utf-8")

    with pytest.raises(ConversionError, match="invalid JSON"):
        convert_ppocrlabel_annotations(
            source_id=SOURCE_ID,
            inventory_path=inventory_path,
            output_path=output_path,
            project_root=tmp_path,
            processed_root=processed_root,
        )


@pytest.mark.parametrize("key", ["source-a/missing.png", "../source-a/page-0001.png"])
def test_rejects_unknown_or_traversing_page_paths(tmp_path: Path, key: str) -> None:
    processed_root, source_dir, inventory_path, output_path = _write_workspace(tmp_path)
    _write_tsv(source_dir / "Cache.cach", [(key, [_box()])])

    with pytest.raises(ConversionError):
        convert_ppocrlabel_annotations(
            source_id=SOURCE_ID,
            inventory_path=inventory_path,
            output_path=output_path,
            project_root=tmp_path,
            processed_root=processed_root,
        )


def test_rejects_duplicate_page_rows(tmp_path: Path) -> None:
    processed_root, source_dir, inventory_path, output_path = _write_workspace(tmp_path)
    _write_tsv(
        source_dir / "Cache.cach",
        [(PAGE_KEY, [_box("一")]), (PAGE_KEY, [_box("二")])],
    )

    with pytest.raises(ConversionError, match="duplicates page"):
        convert_ppocrlabel_annotations(
            source_id=SOURCE_ID,
            inventory_path=inventory_path,
            output_path=output_path,
            project_root=tmp_path,
            processed_root=processed_root,
        )


def test_conversion_is_idempotent_and_atomic_on_validation_failure(tmp_path: Path) -> None:
    result, source_dir, output_path = _convert(tmp_path)
    first_bytes = output_path.read_bytes()
    processed_root = tmp_path / "processed"
    inventory_path = tmp_path / "derived_pages.json"

    second = convert_ppocrlabel_annotations(
        source_id=SOURCE_ID,
        inventory_path=inventory_path,
        output_path=output_path,
        project_root=tmp_path,
        processed_root=processed_root,
    )
    assert second == result
    assert output_path.read_bytes() == first_bytes
    assert not list(output_path.parent.glob("*.part"))

    (source_dir / "Cache.cach").write_text(f"{PAGE_KEY}\tbroken\n", encoding="utf-8")
    with pytest.raises(ConversionError):
        convert_ppocrlabel_annotations(
            source_id=SOURCE_ID,
            inventory_path=inventory_path,
            output_path=output_path,
            project_root=tmp_path,
            processed_root=processed_root,
        )
    assert output_path.read_bytes() == first_bytes
    assert not list(output_path.parent.glob("*.part"))
