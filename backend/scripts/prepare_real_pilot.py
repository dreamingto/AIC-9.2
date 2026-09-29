"""Prepare a reproducible page inventory for the real-book OCR pilot.

The downloader keeps the original PDFs intact.  This script validates those
PDFs, renders the selected pages with Poppler, and writes a small tracked JSON
inventory.  It deliberately creates no OCR, figure, or historical labels:
those fields remain pending until a human annotation pass and an OCR provider
are selected.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import subprocess
import tempfile
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from PIL import Image

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SOURCE_MANIFEST = PROJECT_ROOT / "backend" / "data" / "real_pilot" / "sources.json"
PDF_ROOT = PROJECT_ROOT / "backend" / "data" / "assets" / "real_pilot_v1"
DEFAULT_OUTPUT_ROOT = PROJECT_ROOT / "backend" / "data" / "processed" / "real_pilot_v1"
DEFAULT_INVENTORY = PROJECT_ROOT / "backend" / "data" / "real_pilot" / "derived_pages.json"


class RealPilotPreparationError(RuntimeError):
    """Raised when a source cannot be safely prepared."""


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _load_sources(path: Path = SOURCE_MANIFEST) -> list[dict[str, Any]]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise RealPilotPreparationError(f"unable to read source manifest: {path}") from exc
    if not isinstance(payload, dict) or payload.get("dataset_id") != "real-pilot-v1":
        raise RealPilotPreparationError("source manifest is not real-pilot-v1")
    sources = payload.get("sources")
    if not isinstance(sources, list) or not sources:
        raise RealPilotPreparationError("source manifest has no sources")
    required = {
        "source_id",
        "local_filename",
        "expected_bytes",
        "expected_sha1",
        "sha256",
        "page_count",
        "source_url",
        "source_name",
        "book_title",
        "volume",
        "license_status",
        "allow_training",
        "allow_redistribution",
    }
    retrieved_at = payload.get("retrieved_at")
    validated: list[dict[str, Any]] = []
    for source in sources:
        if not isinstance(source, dict) or not required.issubset(source):
            raise RealPilotPreparationError("source manifest has missing required fields")
        if not isinstance(source["sha256"], str) or len(source["sha256"]) != 64:
            raise RealPilotPreparationError(f"missing SHA-256 for {source.get('source_id')}")
        if isinstance(retrieved_at, str):
            source.setdefault("retrieved_at", retrieved_at)
        validated.append(source)
    return validated


def _pdf_info(pdf_path: Path) -> dict[str, str]:
    executable = shutil.which("pdfinfo")
    if executable is None:
        raise RealPilotPreparationError("pdfinfo is required; install Poppler or add it to PATH")
    try:
        completed = subprocess.run(
            [executable, str(pdf_path)],
            check=True,
            capture_output=True,
            text=False,
        )
    except (OSError, subprocess.CalledProcessError) as exc:
        raise RealPilotPreparationError(f"pdfinfo failed for {pdf_path.name}") from exc
    values: dict[str, str] = {}
    raw_stdout = completed.stdout or b""
    stdout = raw_stdout.decode("utf-8", errors="replace")
    for line in stdout.splitlines():
        if ":" in line:
            key, value = line.split(":", 1)
            values[key.strip().lower().replace(" ", "_")] = value.strip()
    return values


def _safe_output_dir(root: Path, source_id: str) -> Path:
    output_root = root.resolve()
    output_root.mkdir(parents=True, exist_ok=True)
    candidate = (output_root / source_id).resolve()
    try:
        candidate.relative_to(output_root)
    except ValueError as exc:
        raise RealPilotPreparationError("source_id escapes the output directory") from exc
    return candidate


def _render_pages(
    pdf_path: Path,
    source_id: str,
    page_count: int,
    output_root: Path,
    dpi: int,
    force: bool,
) -> list[Path]:
    executable = shutil.which("pdftoppm")
    if executable is None:
        raise RealPilotPreparationError("pdftoppm is required; install Poppler or add it to PATH")
    source_dir = _safe_output_dir(output_root, source_id)
    source_dir.mkdir(parents=True, exist_ok=True)
    existing = sorted(source_dir.glob("page-*.png"))
    if existing and not force:
        if len(existing) != page_count:
            raise RealPilotPreparationError(
                f"{source_id} has {len(existing)} existing pages; use --force to replace them"
            )
        return existing

    with tempfile.TemporaryDirectory(prefix=f".{source_id}-", dir=output_root) as temporary:
        temporary_prefix = Path(temporary) / "page"
        try:
            subprocess.run(
                [
                    executable,
                    "-png",
                    "-r",
                    str(dpi),
                    "-f",
                    "1",
                    "-l",
                    str(page_count),
                    str(pdf_path),
                    str(temporary_prefix),
                ],
                check=True,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
        except (OSError, subprocess.CalledProcessError) as exc:
            raise RealPilotPreparationError(f"pdftoppm failed for {pdf_path.name}") from exc
        rendered = sorted(Path(temporary).glob("page-*.png"))
        if len(rendered) != page_count:
            raise RealPilotPreparationError(
                f"expected {page_count} rendered pages, got {len(rendered)}"
            )
        if force:
            for path in existing:
                path.unlink()
        final_paths: list[Path] = []
        for index, rendered_path in enumerate(rendered, start=1):
            destination = source_dir / f"page-{index:04d}.png"
            shutil.copy2(rendered_path, destination)
            final_paths.append(destination)
    return final_paths


def _page_record(source: dict[str, Any], page_number: int, image_path: Path) -> dict[str, Any]:
    with Image.open(image_path) as image:
        width, height = image.size
        if image.format != "PNG":
            raise RealPilotPreparationError(f"rendered page is not PNG: {image_path}")
    return {
        "page_id": f"{source['source_id']}-p{page_number:04d}",
        "source_id": source["source_id"],
        "book_title": source["book_title"],
        "volume": source["volume"],
        "pdf_page": page_number,
        "page_or_folio": f"pdf-page-{page_number:04d}",
        "image_path": image_path.relative_to(PROJECT_ROOT).as_posix(),
        "mime_type": "image/png",
        "width": width,
        "height": height,
        "sha256": _sha256(image_path),
        "layout": {
            "status": "pending_review",
            "orientation": "unknown",
            "regions": [],
            "reading_order": [],
        },
        "ocr": {
            "status": "pending_provider",
            "provider": None,
            "model": None,
            "version": None,
            "raw_text": None,
            "corrected_text": None,
            "lines": [],
        },
        "provenance": {
            "source_url": source["source_url"],
            "source_name": source["source_name"],
            "license_status": source["license_status"],
            "allow_training": source["allow_training"],
            "allow_redistribution": source["allow_redistribution"],
            "retrieved_at": source.get("retrieved_at"),
            "pdf_filename": source["local_filename"],
            "pdf_sha256": source["sha256"],
            "pipeline_version": "real-pilot-pages-v1",
        },
    }


def prepare(
    *,
    source_ids: set[str] | None = None,
    output_root: Path = DEFAULT_OUTPUT_ROOT,
    inventory_path: Path = DEFAULT_INVENTORY,
    dpi: int = 150,
    force: bool = False,
) -> dict[str, Any]:
    if not 72 <= dpi <= 300:
        raise ValueError("dpi must be between 72 and 300")
    sources = _load_sources()
    selected = [
        source
        for source in sources
        if (
            source_ids is None
            and str(source.get("pilot_selection", "")).startswith("primary")
        ) or (source_ids is not None and source["source_id"] in source_ids)
    ]
    if not selected:
        raise RealPilotPreparationError("no sources selected")
    pages: list[dict[str, Any]] = []
    source_results: list[dict[str, Any]] = []
    for source in selected:
        pdf_path = (PDF_ROOT / source["local_filename"]).resolve()
        if not pdf_path.is_file() or pdf_path.parent != PDF_ROOT.resolve():
            raise RealPilotPreparationError(
                f"source PDF is missing or outside asset root: {pdf_path}"
            )
        if pdf_path.stat().st_size != source["expected_bytes"]:
            raise RealPilotPreparationError(f"byte size mismatch for {source['source_id']}")
        if _sha256(pdf_path) != source["sha256"].lower():
            raise RealPilotPreparationError(f"SHA-256 mismatch for {source['source_id']}")
        info = _pdf_info(pdf_path)
        if int(info.get("pages", "0")) != source["page_count"]:
            raise RealPilotPreparationError(f"page count mismatch for {source['source_id']}")
        image_paths = _render_pages(
            pdf_path,
            source["source_id"],
            source["page_count"],
            output_root,
            dpi,
            force,
        )
        source_pages = [
            _page_record(source, page_number, image_path)
            for page_number, image_path in enumerate(image_paths, start=1)
        ]
        pages.extend(source_pages)
        source_results.append(
            {
                "source_id": source["source_id"],
                "pdf_filename": source["local_filename"],
                "page_count": len(source_pages),
                "dpi": dpi,
                "status": "rendered_pending_annotation",
            }
        )
    inventory = {
        "schema_version": "1.0",
        "dataset_id": "real-pilot-v1-pages",
        "dataset_kind": "real_pilot_page_inventory",
        "evaluation_status": "not_evaluated",
        "generated_at": datetime.now(UTC).isoformat(),
        "pipeline_version": "real-pilot-pages-v1",
        "disclaimer": (
            "页面已从真实馆藏扫描渲染；OCR、版面、图题和功能标注尚未完成，"
            "not_evaluated。"
        ),
        "sources": source_results,
        "pages": pages,
    }
    inventory_path.parent.mkdir(parents=True, exist_ok=True)
    inventory_path.write_text(
        json.dumps(inventory, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    return inventory


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-id", action="append", dest="source_ids")
    parser.add_argument("--all-sources", action="store_true")
    parser.add_argument("--dpi", type=int, default=150)
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()
    source_ids = set(args.source_ids or []) if args.source_ids else None
    if args.all_sources:
        source_ids = {source["source_id"] for source in _load_sources()}
    try:
        inventory = prepare(source_ids=source_ids, dpi=args.dpi, force=args.force)
    except (RealPilotPreparationError, ValueError) as exc:
        parser.error(str(exc))
    print(
        json.dumps(
            {
                "status": "passed",
                "inventory": str(DEFAULT_INVENTORY),
                "sources": len(inventory["sources"]),
                "pages": len(inventory["pages"]),
                "evaluation_status": inventory["evaluation_status"],
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
