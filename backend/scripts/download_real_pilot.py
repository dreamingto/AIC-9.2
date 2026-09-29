#!/usr/bin/env python3
"""Download and verify the controlled V1.1-B real-book pilot sources."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Self
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit
from urllib.request import Request, urlopen

ALLOWED_DOWNLOAD_HOSTS = {"upload.wikimedia.org"}
DEFAULT_REGISTRY = (
    Path(__file__).resolve().parents[1] / "data" / "real_pilot" / "sources.json"
)
DEFAULT_OUTPUT_ROOT = (
    Path(__file__).resolve().parents[1] / "data" / "assets" / "real_pilot_v1"
)


class RealSourceError(RuntimeError):
    """Raised when a source registry or downloaded file is invalid."""


@dataclass(frozen=True)
class SourceSpec:
    source_id: str
    download_url: str
    local_filename: str
    mime_type: str
    expected_bytes: int
    expected_sha1: str
    expected_sha256: str | None

    @classmethod
    def from_mapping(cls, value: object) -> Self:
        if not isinstance(value, dict):
            raise RealSourceError("Each source must be a JSON object")

        def required_string(name: str) -> str:
            item = value.get(name)
            if not isinstance(item, str) or not item.strip():
                raise RealSourceError(f"Source field {name!r} must be a non-empty string")
            return item

        source_id = required_string("source_id")
        download_url = required_string("download_url")
        local_filename = required_string("local_filename")
        mime_type = required_string("mime_type")
        expected_sha1 = required_string("expected_sha1").lower()
        expected_bytes = value.get("expected_bytes")
        expected_sha256_value = value.get("sha256")

        if not isinstance(expected_bytes, int) or isinstance(expected_bytes, bool):
            raise RealSourceError(f"{source_id}: expected_bytes must be an integer")
        if expected_bytes <= 0:
            raise RealSourceError(f"{source_id}: expected_bytes must be positive")
        if len(expected_sha1) != 40 or any(
            char not in "0123456789abcdef" for char in expected_sha1
        ):
            raise RealSourceError(f"{source_id}: expected_sha1 must be 40 lowercase hex characters")
        if expected_sha256_value is not None and (
            not isinstance(expected_sha256_value, str)
            or len(expected_sha256_value) != 64
            or any(char not in "0123456789abcdef" for char in expected_sha256_value.lower())
        ):
            raise RealSourceError(f"{source_id}: sha256 must be null or 64 hex characters")
        if mime_type != "application/pdf":
            raise RealSourceError(f"{source_id}: only application/pdf is allowed")
        if Path(local_filename).name != local_filename or not local_filename.endswith(".pdf"):
            raise RealSourceError(f"{source_id}: local_filename must be a plain .pdf filename")

        parsed_url = urlsplit(download_url)
        if parsed_url.scheme != "https" or parsed_url.hostname not in ALLOWED_DOWNLOAD_HOSTS:
            raise RealSourceError(
                f"{source_id}: download_url must use HTTPS on an approved Wikimedia host"
            )

        return cls(
            source_id=source_id,
            download_url=download_url,
            local_filename=local_filename,
            mime_type=mime_type,
            expected_bytes=expected_bytes,
            expected_sha1=expected_sha1,
            expected_sha256=(
                expected_sha256_value.lower()
                if isinstance(expected_sha256_value, str)
                else None
            ),
        )


def load_sources(registry_path: Path) -> list[SourceSpec]:
    try:
        payload: object = json.loads(registry_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise RealSourceError(f"Cannot read source registry {registry_path}: {error}") from error
    if not isinstance(payload, dict):
        raise RealSourceError("Source registry root must be a JSON object")
    if payload.get("schema_version") != "1.0":
        raise RealSourceError("Unsupported source registry schema_version")

    raw_sources = payload.get("sources")
    if not isinstance(raw_sources, list) or not raw_sources:
        raise RealSourceError("Source registry must contain a non-empty sources list")
    sources = [SourceSpec.from_mapping(item) for item in raw_sources]
    source_ids = [source.source_id for source in sources]
    filenames = [source.local_filename for source in sources]
    if len(source_ids) != len(set(source_ids)):
        raise RealSourceError("Source registry contains duplicate source_id values")
    if len(filenames) != len(set(filenames)):
        raise RealSourceError("Source registry contains duplicate local_filename values")
    return sources


def file_digests(path: Path) -> tuple[int, str, str]:
    size = 0
    sha1 = hashlib.sha1()
    sha256 = hashlib.sha256()
    with path.open("rb") as stream:
        if stream.read(5) != b"%PDF-":
            raise RealSourceError(f"{path.name}: file does not have a PDF signature")
        stream.seek(0)
        while chunk := stream.read(1024 * 1024):
            size += len(chunk)
            sha1.update(chunk)
            sha256.update(chunk)
    return size, sha1.hexdigest(), sha256.hexdigest()


def verify_file(path: Path, source: SourceSpec) -> dict[str, Any]:
    size, sha1, sha256 = file_digests(path)
    if size != source.expected_bytes:
        raise RealSourceError(
            f"{source.source_id}: byte size {size} does not match {source.expected_bytes}"
        )
    if sha1 != source.expected_sha1:
        raise RealSourceError(f"{source.source_id}: SHA-1 does not match Commons metadata")
    if source.expected_sha256 is not None and sha256 != source.expected_sha256:
        raise RealSourceError(f"{source.source_id}: SHA-256 does not match the registry")
    return {
        "source_id": source.source_id,
        "path": str(path),
        "bytes": size,
        "sha1": sha1,
        "sha256": sha256,
    }


def materialize_source(
    source: SourceSpec, output_root: Path, *, force: bool = False
) -> dict[str, Any]:
    resolved_root = output_root.resolve()
    resolved_root.mkdir(parents=True, exist_ok=True)
    destination = (resolved_root / source.local_filename).resolve()
    if destination.parent != resolved_root:
        raise RealSourceError(f"{source.source_id}: output path escapes the output root")

    if destination.exists() and not force:
        try:
            result = verify_file(destination, source)
        except RealSourceError as error:
            raise RealSourceError(f"{error}; pass --force to replace the file") from error
        result["status"] = "existing_verified"
        return result

    temporary = destination.with_suffix(destination.suffix + ".part")
    temporary.unlink(missing_ok=True)
    request = Request(
        source.download_url,
        headers={"User-Agent": "JiTu-Suoyin-Research/0.1 (+local controlled dataset)"},
    )
    try:
        with urlopen(request, timeout=90) as response, temporary.open("wb") as stream:
            content_type = response.headers.get_content_type()
            if content_type != source.mime_type:
                raise RealSourceError(
                    f"{source.source_id}: response MIME {content_type!r} "
                    f"is not {source.mime_type!r}"
                )
            while chunk := response.read(1024 * 1024):
                stream.write(chunk)
        result = verify_file(temporary, source)
        os.replace(temporary, destination)
    except (HTTPError, URLError, OSError, RealSourceError) as error:
        temporary.unlink(missing_ok=True)
        if isinstance(error, RealSourceError):
            raise
        raise RealSourceError(f"{source.source_id}: download failed: {error}") from error

    result["path"] = str(destination)
    result["status"] = "downloaded"
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--registry", type=Path, default=DEFAULT_REGISTRY)
    parser.add_argument("--output-root", type=Path, default=DEFAULT_OUTPUT_ROOT)
    parser.add_argument("--source-id", action="append", default=[])
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()

    try:
        sources = load_sources(args.registry.resolve())
        selected_ids = set(args.source_id)
        if selected_ids:
            sources = [source for source in sources if source.source_id in selected_ids]
            missing_ids = selected_ids - {source.source_id for source in sources}
            if missing_ids:
                raise RealSourceError(f"Unknown source_id values: {sorted(missing_ids)}")
        results = []
        for source in sources:
            print(f"materializing {source.source_id}...", file=sys.stderr)
            results.append(
                materialize_source(source, args.output_root.resolve(), force=args.force)
            )
    except RealSourceError as error:
        print(f"real-pilot download failed: {error}", file=sys.stderr)
        return 1

    print(json.dumps({"status": "passed", "sources": results}, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
