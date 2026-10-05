from __future__ import annotations

import zipfile
from pathlib import Path

import pytest

from scripts.release_bundle import digest, restore, safe_target


@pytest.mark.parametrize("path", [
    "../.env", "backend/data/../../.env", "backend/data/.git/config", "C:/secret",
    "backend\\data\\assets\\x", "backend/data/assets/../../../outside",
])
def test_bundle_path_cannot_escape_or_touch_secrets(tmp_path: Path, path: str) -> None:
    with pytest.raises(ValueError):
        safe_target(tmp_path, path)


def test_restore_preflights_all_files_before_writing(tmp_path: Path) -> None:
    archive = tmp_path / "bundle.zip"
    good, bad = "backend/data/assets/new.png", "backend/data/assets/existing.png"
    existing = safe_target(tmp_path, bad)
    existing.parent.mkdir(parents=True)
    existing.write_bytes(b"keep")
    with zipfile.ZipFile(archive, "w") as bundle:
        bundle.writestr(good, b"new")
        bundle.writestr(bad, b"replacement")
    lock = {"archive_sha256": digest(archive.read_bytes()), "files": [
        {"path": good, "size": 3, "sha256": digest(b"new")},
        {"path": bad, "size": 11, "sha256": digest(b"replacement")},
    ]}
    with pytest.raises(ValueError, match="overwrite"):
        restore(tmp_path, archive, lock)
    assert existing.read_bytes() == b"keep" and not safe_target(tmp_path, good).exists()


def test_bundle_corruption_is_rejected_before_extraction(tmp_path: Path) -> None:
    archive = tmp_path / "bundle.zip"
    archive.write_bytes(b"tampered")
    with pytest.raises(ValueError, match="SHA256"):
        restore(tmp_path, archive, {"archive_sha256": "0" * 64})
