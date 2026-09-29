"""Tests for the controlled real-book pilot downloader."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from scripts.download_real_pilot import (
    RealSourceError,
    SourceSpec,
    load_sources,
    materialize_source,
)

PDF_BYTES = b"%PDF-1.4\n1 0 obj\n<<>>\nendobj\n%%EOF\n"


def _source_payload(**overrides: object) -> dict[str, object]:
    payload: dict[str, object] = {
        "source_id": "commons-test",
        "download_url": "https://upload.wikimedia.org/test.pdf",
        "local_filename": "test.pdf",
        "mime_type": "application/pdf",
        "expected_bytes": len(PDF_BYTES),
        "expected_sha1": hashlib.sha1(PDF_BYTES).hexdigest(),
        "sha256": hashlib.sha256(PDF_BYTES).hexdigest(),
    }
    payload.update(overrides)
    return payload


def test_registry_rejects_unapproved_download_host(tmp_path: Path) -> None:
    registry = tmp_path / "sources.json"
    registry.write_text(
        json.dumps(
            {
                "schema_version": "1.0",
                "sources": [_source_payload(download_url="https://example.invalid/book.pdf")],
            }
        ),
        encoding="utf-8",
    )

    with pytest.raises(RealSourceError, match="approved Wikimedia host"):
        load_sources(registry)


def test_existing_file_is_verified_without_network(tmp_path: Path) -> None:
    source = SourceSpec.from_mapping(_source_payload())
    destination = tmp_path / source.local_filename
    destination.write_bytes(PDF_BYTES)

    result = materialize_source(source, tmp_path)

    assert result["status"] == "existing_verified"
    assert result["bytes"] == len(PDF_BYTES)
    assert result["sha256"] == hashlib.sha256(PDF_BYTES).hexdigest()


def test_existing_mismatch_requires_force(tmp_path: Path) -> None:
    source = SourceSpec.from_mapping(_source_payload())
    (tmp_path / source.local_filename).write_bytes(b"not a pdf")

    with pytest.raises(RealSourceError, match="--force"):
        materialize_source(source, tmp_path)
