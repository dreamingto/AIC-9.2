"""Safe, deterministic loading and on-disk validation for fixture manifests."""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path, PureWindowsPath
from typing import Any

from PIL import Image, UnidentifiedImageError
from pydantic import ValidationError

from .contracts import FixtureManifest, ValidatedFixture

MANIFEST_NAME_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]*\.json$")
PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"
DEFAULT_MAX_ASSET_BYTES = 20 * 1024 * 1024


class ManifestValidationError(ValueError):
    """A user-correctable manifest or fixture asset error.

    ``code`` is intentionally stable so the API layer can map this exception
    to ``INGESTION_INVALID_MANIFEST`` without importing the ingestion module's
    internals.
    """

    code = "INGESTION_INVALID_MANIFEST"

    def __init__(self, message: str, *, details: dict[str, Any] | None = None) -> None:
        super().__init__(message)
        self.details = details or {}


def validate_manifest_name(manifest_name: str) -> str:
    """Validate an API-provided manifest *file name*, never a path.

    Only a basename with the conservative ``[A-Za-z0-9_.-]`` alphabet is
    accepted.  In particular, slash, backslash, ``..`` and NUL are rejected
    before any filesystem operation occurs.
    """

    if not isinstance(manifest_name, str) or not MANIFEST_NAME_RE.fullmatch(manifest_name):
        raise ManifestValidationError(
            "manifest_name must be a simple .json file name",
            details={"manifest_name": manifest_name},
        )
    if "/" in manifest_name or "\\" in manifest_name or ".." in manifest_name:
        raise ManifestValidationError("manifest_name must not contain a path segment")
    return manifest_name


def resolve_contained_path(root: Path, relative_path: str | Path) -> Path:
    """Resolve a path and prove it remains under ``root``.

    ``Path.resolve(strict=False)`` follows existing symlinks, preventing a
    symlink in the fixture tree from escaping the configured data root.
    """

    if isinstance(relative_path, str) and ("\x00" in relative_path or "\\" in relative_path):
        raise ManifestValidationError("fixture path must use '/' separators")
    root_resolved = root.expanduser().resolve(strict=False)
    candidate = Path(relative_path)
    windows_candidate = PureWindowsPath(str(relative_path))
    if candidate.is_absolute() or windows_candidate.is_absolute() or windows_candidate.drive:
        raise ManifestValidationError("fixture path must be relative")
    candidate_resolved = (root_resolved / candidate).resolve(strict=False)
    try:
        candidate_resolved.relative_to(root_resolved)
    except ValueError as exc:
        raise ManifestValidationError(
            "fixture path escapes its configured data root",
            details={"path": str(relative_path)},
        ) from exc
    return candidate_resolved


def _read_json(manifest_path: Path) -> dict[str, Any]:
    try:
        raw = manifest_path.read_text(encoding="utf-8")
    except OSError as exc:
        raise ManifestValidationError(
            "unable to read manifest", details={"path": str(manifest_path), "reason": str(exc)}
        ) from exc

    def reject_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for key, value in pairs:
            if key in result:
                raise ManifestValidationError(
                    "manifest contains duplicate JSON keys",
                    details={"key": key},
                )
            result[key] = value
        return result

    try:
        payload = json.loads(raw, object_pairs_hook=reject_duplicate_keys)
    except json.JSONDecodeError as exc:
        raise ManifestValidationError(
            "manifest is not valid JSON", details={"line": exc.lineno, "column": exc.colno}
        ) from exc
    if not isinstance(payload, dict):
        raise ManifestValidationError("manifest root must be a JSON object")
    return payload


def parse_manifest(manifest_path: Path) -> FixtureManifest:
    """Parse and cross-reference-check a manifest without touching assets."""

    payload = _read_json(manifest_path)
    try:
        return FixtureManifest.model_validate(payload)
    except ValidationError as exc:
        # Keep Pydantic's useful field paths while exposing a stable exception
        # type to FastAPI and the ingestion runner.
        errors = [
            {"loc": list(error.get("loc", ())), "msg": error.get("msg", "invalid value")}
            for error in exc.errors()
        ]
        raise ManifestValidationError(
            "manifest schema validation failed", details={"errors": errors}
        ) from exc


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    try:
        with path.open("rb") as stream:
            for block in iter(lambda: stream.read(1024 * 1024), b""):
                digest.update(block)
    except OSError as exc:
        raise ManifestValidationError(
            "unable to read fixture asset", details={"path": str(path), "reason": str(exc)}
        ) from exc
    return digest.hexdigest()


def _validate_png(
    asset_path: Path,
    expected_width: int,
    expected_height: int,
    *,
    max_asset_bytes: int = DEFAULT_MAX_ASSET_BYTES,
) -> None:
    try:
        stat = asset_path.stat()
    except OSError as exc:
        raise ManifestValidationError(
            "fixture asset metadata cannot be read", details={"path": str(asset_path)}
        ) from exc
    if stat.st_size > max_asset_bytes:
        raise ManifestValidationError(
            "fixture asset exceeds the maximum allowed size",
            details={"path": str(asset_path), "max_bytes": max_asset_bytes},
        )
    try:
        with asset_path.open("rb") as stream:
            signature = stream.read(len(PNG_SIGNATURE))
    except OSError as exc:
        raise ManifestValidationError("unable to read PNG signature") from exc
    if signature != PNG_SIGNATURE:
        raise ManifestValidationError(
            "fixture asset is not a PNG file", details={"path": str(asset_path)}
        )

    try:
        with Image.open(asset_path) as image:
            if image.format != "PNG":
                raise ManifestValidationError("fixture asset format does not match image/png")
            width, height = image.size
            if (width, height) != (expected_width, expected_height):
                raise ManifestValidationError(
                    "fixture asset dimensions do not match manifest",
                    details={
                        "path": str(asset_path),
                        "expected": [expected_width, expected_height],
                        "actual": [width, height],
                    },
                )
            # Verify checks the encoded stream without retaining the image.
            image.verify()
    except UnidentifiedImageError as exc:
        raise ManifestValidationError("fixture asset cannot be decoded as PNG") from exc
    except OSError as exc:
        raise ManifestValidationError("fixture asset is corrupt") from exc


def validate_assets(
    manifest: FixtureManifest,
    *,
    assets_root: Path,
    max_asset_bytes: int = DEFAULT_MAX_ASSET_BYTES,
) -> dict[str, Path]:
    """Validate every declared asset and return a safe ID-to-path mapping."""

    if max_asset_bytes <= 0:
        raise ValueError("max_asset_bytes must be positive")
    asset_paths: dict[str, Path] = {}
    root = assets_root.expanduser().resolve(strict=False)
    for asset in manifest.assets:
        path = resolve_contained_path(root, asset.relative_path)
        if not path.exists() or not path.is_file():
            raise ManifestValidationError(
                "fixture asset does not exist", details={"asset_id": asset.asset_id}
            )
        try:
            if path.stat().st_size > max_asset_bytes:
                raise ManifestValidationError(
                    "fixture asset exceeds the maximum allowed size",
                    details={"asset_id": asset.asset_id, "max_bytes": max_asset_bytes},
                )
        except OSError as exc:
            raise ManifestValidationError("unable to stat fixture asset") from exc
        _validate_png(
            path,
            asset.width,
            asset.height,
            max_asset_bytes=max_asset_bytes,
        )
        actual_hash = _sha256(path)
        if actual_hash != asset.sha256.lower():
            raise ManifestValidationError(
                "fixture asset sha256 does not match manifest",
                details={
                    "asset_id": asset.asset_id,
                    "expected": asset.sha256,
                    "actual": actual_hash,
                },
            )
        asset_paths[asset.asset_id] = path
    return asset_paths


def load_manifest(
    manifest_name: str,
    *,
    manifests_root: Path,
    assets_root: Path,
    max_asset_bytes: int = DEFAULT_MAX_ASSET_BYTES,
) -> ValidatedFixture:
    """Load a controlled manifest name and return normalized validated data."""

    safe_name = validate_manifest_name(manifest_name)
    manifest_root = manifests_root.expanduser().resolve(strict=False)
    manifest_path = resolve_contained_path(manifest_root, safe_name)
    if not manifest_path.exists() or not manifest_path.is_file():
        raise ManifestValidationError(
            "manifest file does not exist", details={"manifest_name": safe_name}
        )
    manifest = parse_manifest(manifest_path)

    # Figure.original_path is provenance, not an instruction to open a file;
    # nevertheless reject path traversal so downstream renderers can safely
    # display it or resolve it under the same assets root.
    for figure in manifest.figures:
        try:
            resolve_contained_path(assets_root, figure.original_path)
        except ManifestValidationError as exc:
            raise ManifestValidationError(
                "figure original_path escapes the asset root",
                details={"figure_id": figure.figure_id},
            ) from exc

    asset_paths = validate_assets(
        manifest, assets_root=assets_root, max_asset_bytes=max_asset_bytes
    )
    return ValidatedFixture.from_manifest(manifest, manifest_path, asset_paths)


__all__ = [
    "DEFAULT_MAX_ASSET_BYTES",
    "MANIFEST_NAME_RE",
    "ManifestValidationError",
    "load_manifest",
    "parse_manifest",
    "resolve_contained_path",
    "validate_assets",
    "validate_manifest_name",
]
