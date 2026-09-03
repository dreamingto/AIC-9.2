"""Contract and filesystem validation tests for the offline fixture."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from app.ingestion.contracts import FixtureManifest, NormalizedBBox, SourceRecord
from app.ingestion.loader import (
    ManifestValidationError,
    load_manifest,
    resolve_contained_path,
    validate_manifest_name,
)
from scripts.generate_fixture import generate


def _generate(tmp_path: Path) -> tuple[Path, Path, Path]:
    assets_root = tmp_path / "assets"
    manifests_root = tmp_path / "manifests"
    manifest_path = generate(assets_root=assets_root, manifests_root=manifests_root)
    return manifest_path, manifests_root, assets_root


def test_generated_fixture_has_required_counts_and_valid_hashes(tmp_path: Path) -> None:
    manifest_path, manifests_root, assets_root = _generate(tmp_path)
    validated = load_manifest(
        manifest_path.name,
        manifests_root=manifests_root,
        assets_root=assets_root,
    )
    assert validated.counts == {
        "sources": 3,
        "assets": 9,
        "pages": 9,
        "figures": 9,
        "regions": 18,
        "text_chunks": 18,
        "evidence": 27,
        "functional_assertions": 54,
        "relations": 9,
        "benchmark_pairs": 12,
    }
    assert all(path.suffix == ".png" for path in validated.asset_paths.values())
    records = validated.normalized_records()
    assert records["figures"][0]["figure_id"] == "fig-water-wheel-01"
    assert records["sources"][0]["retrieved_at"].endswith("+00:00")
    redistribution = {
        source.source_id: source.allow_redistribution for source in validated.manifest.sources
    }
    assert redistribution["src-textile-machines"] is False
    assert any(redistribution.values())


@pytest.mark.parametrize(
    "name",
    ["../fixture.json", "nested/fixture.json", r"nested\fixture.json", "fixture.txt", "..json"],
)
def test_manifest_name_is_basename_only(name: str) -> None:
    with pytest.raises(ManifestValidationError):
        validate_manifest_name(name)


def test_path_containment_rejects_escape() -> None:
    with pytest.raises(ManifestValidationError):
        resolve_contained_path(Path("/tmp/fixture-root"), "../outside.png")


def test_sha256_mismatch_is_rejected(tmp_path: Path) -> None:
    manifest_path, manifests_root, assets_root = _generate(tmp_path)
    payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    payload["assets"][0]["sha256"] = "0" * 64
    manifest_path.write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(ManifestValidationError, match="sha256"):
        load_manifest(manifest_path.name, manifests_root=manifests_root, assets_root=assets_root)


def test_missing_asset_is_rejected(tmp_path: Path) -> None:
    manifest_path, manifests_root, assets_root = _generate(tmp_path)
    asset_path = assets_root / "fixture_v1" / "fig-water-wheel-01.png"
    asset_path.unlink()
    with pytest.raises(ManifestValidationError, match="does not exist"):
        load_manifest(manifest_path.name, manifests_root=manifests_root, assets_root=assets_root)


def test_duplicate_json_key_is_rejected(tmp_path: Path) -> None:
    manifest_path, manifests_root, assets_root = _generate(tmp_path)
    original = manifest_path.read_text(encoding="utf-8")
    # Keep a valid-looking root while deliberately repeating a top-level key.
    manifest_path.write_text(
        original.replace(
            '"title": "机图索隐 V1 离线合成夹具",', '"title": "first",\n  "title": "second",'
        ),
        encoding="utf-8",
    )
    with pytest.raises(ManifestValidationError, match="duplicate JSON keys"):
        load_manifest(manifest_path.name, manifests_root=manifests_root, assets_root=assets_root)


def test_schema_rejects_unknown_references(tmp_path: Path) -> None:
    manifest_path, _, _ = _generate(tmp_path)
    payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    payload["figures"][0]["page_id"] = "page-does-not-exist"
    with pytest.raises(ValueError, match="unknown figure.page_id"):
        FixtureManifest.model_validate(payload)


def test_schema_rejects_duplicate_unordered_pairs(tmp_path: Path) -> None:
    manifest_path, _, _ = _generate(tmp_path)
    payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    duplicate = dict(payload["benchmark_pairs"][0])
    duplicate["pair_id"] = "pair-duplicate"
    duplicate["query_figure_id"], duplicate["candidate_figure_id"] = (
        duplicate["candidate_figure_id"],
        duplicate["query_figure_id"],
    )
    payload["benchmark_pairs"].append(duplicate)
    with pytest.raises(ValueError, match="duplicate unordered benchmark pair"):
        FixtureManifest.model_validate(payload)


def test_bbox_rejects_nan_and_overflow() -> None:
    with pytest.raises(ValueError):
        NormalizedBBox(x=float("nan"), y=0.0, width=0.2, height=0.2)
    with pytest.raises(ValueError):
        NormalizedBBox(x=0.9, y=0.0, width=0.2, height=0.2)


def test_restricted_license_cannot_allow_redistribution() -> None:
    with pytest.raises(ValueError, match="restricted"):
        SourceRecord(
            source_id="src-restricted",
            source_url="https://example.invalid/restricted",
            source_name="restricted",
            book_title="example",
            author="example",
            era="example",
            edition="example",
            volume="1",
            page_or_folio="1",
            license_status="restricted",
            license_note="permission required",
            allow_training=False,
            allow_redistribution=True,
            retrieved_at="2026-09-02T00:00:00+00:00",
            pipeline_version="test",
        )
