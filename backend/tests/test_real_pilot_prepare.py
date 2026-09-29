from __future__ import annotations

from pathlib import Path

import pytest
from PIL import Image

import scripts.prepare_real_pilot as prepare_module
from app.core.errors import DomainError
from app.retrieval.providers.ocr import UnavailableOCRProvider, _box_from_points
from scripts.prepare_real_pilot import (
    RealPilotPreparationError,
    _load_sources,
    _page_record,
    _safe_output_dir,
)


def test_real_source_manifest_contains_verified_hashes() -> None:
    sources = _load_sources()
    assert len(sources) == 2
    assert all(len(source["sha256"]) == 64 for source in sources)
    assert sources[0]["sha256"] != sources[1]["sha256"]


def test_page_record_keeps_ocr_and_layout_pending(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(prepare_module, "PROJECT_ROOT", tmp_path)
    image_path = tmp_path / "page.png"
    Image.new("RGB", (40, 60), "white").save(image_path, format="PNG")
    source = {
        "source_id": "source-a",
        "book_title": "天工開物",
        "volume": "2",
        "source_url": "https://example.invalid/source",
        "source_name": "test",
        "license_status": "public_domain",
        "allow_training": True,
        "allow_redistribution": True,
        "local_filename": "book.pdf",
        "sha256": "a" * 64,
    }
    record = _page_record(source, 1, image_path)
    assert record["ocr"]["status"] == "pending_provider"
    assert record["ocr"]["raw_text"] is None
    assert record["layout"]["status"] == "pending_review"
    assert record["width"] == 40 and record["height"] == 60


def test_output_path_rejects_escape() -> None:
    with pytest.raises(RealPilotPreparationError):
        _safe_output_dir(Path(".") / "tmp", "../outside")


def test_unavailable_ocr_is_explicit() -> None:
    provider = UnavailableOCRProvider()
    assert provider.health().available is False
    with pytest.raises(DomainError) as error:
        provider.recognize(b"not-an-image")
    assert error.value.code == "MODEL_UNAVAILABLE"


def test_paddle_boxes_normalize_to_xyxy() -> None:
    assert _box_from_points([[5, 8], [1, 8], [1, 2], [5, 2]]) == (1.0, 2.0, 5.0, 8.0)
