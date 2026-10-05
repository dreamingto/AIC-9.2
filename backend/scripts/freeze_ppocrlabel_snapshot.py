"""Freeze a content-addressed PPOCRLabel layout-review snapshot.

The snapshot is local and Git-ignored because it contains real page labels.
It does not promote transcription or research metrics to evaluated status.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import tempfile
from pathlib import Path
from typing import Any, cast

from scripts.audit_ppocrlabel_annotations import (
    OUTPUT_PATH as AUDIT_OUTPUT_PATH,
)
from scripts.audit_ppocrlabel_annotations import (
    audit_ppocrlabel_annotations,
)
from scripts.convert_ppocrlabel_annotations import (
    DEFAULT_SOURCE_ID,
    INVENTORY_PATH,
    PROCESSED_ROOT,
    PROJECT_ROOT,
    ConversionError,
    _resolve_source_dir,
    _write_json_atomic,
    convert_ppocrlabel_annotations,
)
from scripts.convert_ppocrlabel_annotations import (
    OUTPUT_PATH as ANNOTATION_OUTPUT_PATH,
)

FREEZE_ROOT = PROJECT_ROOT / "backend" / "data" / "real_pilot" / "frozen"
PIPELINE_VERSION = "ppocrlabel-layout-freeze-v1"


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _read_manifest(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ConversionError(f"unable to read frozen manifest: {path}") from exc
    if not isinstance(value, dict):
        raise ConversionError("frozen manifest root must be an object")
    return cast(dict[str, Any], value)


def _verify_existing_snapshot(target: Path, expected: dict[str, Any]) -> None:
    actual = _read_manifest(target / "manifest.json")
    if actual != expected:
        raise ConversionError(f"snapshot id collision at: {target.name}")
    raw_files = expected.get("files")
    if not isinstance(raw_files, dict):
        raise ConversionError("frozen manifest files must be an object")
    for filename, expected_hash in raw_files.items():
        if not isinstance(filename, str) or not isinstance(expected_hash, str):
            raise ConversionError("frozen manifest file entry is invalid")
        candidate = target / filename
        if not candidate.is_file() or _sha256(candidate) != expected_hash:
            raise ConversionError(f"frozen snapshot file failed verification: {filename}")


def freeze_layout_snapshot(
    *,
    reviewer: str,
    source_id: str = DEFAULT_SOURCE_ID,
    inventory_path: Path = INVENTORY_PATH,
    annotation_output_path: Path = ANNOTATION_OUTPUT_PATH,
    audit_output_path: Path = AUDIT_OUTPUT_PATH,
    project_root: Path = PROJECT_ROOT,
    processed_root: Path = PROCESSED_ROOT,
    freeze_root: Path = FREEZE_ROOT,
) -> dict[str, Any]:
    """Create or verify a deterministic, content-addressed layout snapshot."""

    reviewer = reviewer.strip()
    if not reviewer or len(reviewer) > 200:
        raise ConversionError("reviewer must contain 1-200 non-whitespace characters")
    source_dir = _resolve_source_dir(processed_root, source_id)
    annotations = convert_ppocrlabel_annotations(
        source_id=source_id,
        inventory_path=inventory_path,
        output_path=annotation_output_path,
        project_root=project_root,
        processed_root=processed_root,
        reviewer=reviewer,
        accept_file_state=True,
    )
    audit = audit_ppocrlabel_annotations(
        source_id=source_id,
        inventory_path=inventory_path,
        output_path=audit_output_path,
        project_root=project_root,
        processed_root=processed_root,
    )
    if not audit.get("layout_snapshot_ready"):
        raise ConversionError("layout snapshot quality gate did not pass")
    if annotations["statistics"]["layout_reviewed_pages"] != audit["summary"]["total_pages"]:
        raise ConversionError("not all inventory pages are layout-reviewed")

    source_files = {
        "Cache.cach": source_dir / "Cache.cach",
        "Label.txt": source_dir / "Label.txt",
        "fileState.txt": source_dir / "fileState.txt",
        "derived_pages.json": inventory_path,
        "annotations.json": annotation_output_path,
        "quality_audit.json": audit_output_path,
    }
    file_hashes = {name: _sha256(path) for name, path in source_files.items()}
    snapshot_id = f"{source_id}-layout-{file_hashes['Label.txt'][:12]}"
    manifest: dict[str, Any] = {
        "schema_version": "1.0",
        "snapshot_id": snapshot_id,
        "snapshot_scope": "layout_review_only",
        "evaluation_status": "not_evaluated",
        "pipeline_version": PIPELINE_VERSION,
        "source_id": source_id,
        "reviewer": reviewer,
        "layout_reviewed_pages": annotations["statistics"]["layout_reviewed_pages"],
        "transcription_reviewed_pages": annotations["statistics"][
            "transcription_reviewed_pages"
        ],
        "figure_title_ground_truth": "unavailable",
        "files": file_hashes,
    }
    freeze_root.mkdir(parents=True, exist_ok=True)
    target = freeze_root / snapshot_id
    if target.exists():
        _verify_existing_snapshot(target, manifest)
        return manifest

    staging = Path(tempfile.mkdtemp(prefix=f".{snapshot_id}-", dir=freeze_root))
    try:
        for filename, source_path in source_files.items():
            shutil.copyfile(source_path, staging / filename)
        _write_json_atomic(staging / "manifest.json", manifest)
        staging.replace(target)
    finally:
        if staging.exists():
            shutil.rmtree(staging)
    _verify_existing_snapshot(target, manifest)
    return manifest


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-id", default=DEFAULT_SOURCE_ID)
    parser.add_argument("--reviewer", required=True)
    args = parser.parse_args()
    try:
        manifest = freeze_layout_snapshot(
            source_id=args.source_id,
            reviewer=args.reviewer,
        )
    except ConversionError as exc:
        parser.error(str(exc))
    print(json.dumps(manifest, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
