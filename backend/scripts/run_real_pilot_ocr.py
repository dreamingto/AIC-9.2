"""Run the optional OCR provider against a prepared real-page inventory.

The command writes raw OCR only.  It never fills ``corrected_text`` or marks a
transcription as verified; those fields belong to the human review pass.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import tempfile
from pathlib import Path
from typing import Any

from app.core.errors import DomainError
from app.retrieval.providers.ocr import OCRProvider, OCRResult, create_optional_ocr_provider

PROJECT_ROOT = Path(__file__).resolve().parents[2]
INVENTORY_PATH = PROJECT_ROOT / "backend" / "data" / "real_pilot" / "derived_pages.json"
OUTPUT_PATH = PROJECT_ROOT / "backend" / "data" / "real_pilot" / "ocr_results.json"
PROCESSED_ROOT = (PROJECT_ROOT / "backend" / "data" / "processed" / "real_pilot_v1").resolve()


class RealPilotOCRError(RuntimeError):
    """Raised for invalid inventory or an unavailable OCR runtime."""


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _load_inventory(path: Path = INVENTORY_PATH) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise RealPilotOCRError(f"unable to read page inventory: {path}") from exc
    if not isinstance(payload, dict) or payload.get("dataset_kind") != "real_pilot_page_inventory":
        raise RealPilotOCRError("inventory is not a real pilot page inventory")
    pages = payload.get("pages")
    if not isinstance(pages, list) or not pages:
        raise RealPilotOCRError("page inventory has no pages")
    return payload


def _resolve_page_image(relative_path: str) -> Path:
    image_path = (PROJECT_ROOT / relative_path).resolve()
    try:
        image_path.relative_to(PROCESSED_ROOT)
    except ValueError as exc:
        raise RealPilotOCRError("page image is outside the processed data root") from exc
    if image_path.suffix.lower() != ".png" or not image_path.is_file():
        raise RealPilotOCRError(f"page image is missing or not PNG: {relative_path}")
    return image_path


def _result_record(page: dict[str, Any], image_path: Path, result: OCRResult) -> dict[str, Any]:
    return {
        "page_id": page["page_id"],
        "source_id": page["source_id"],
        "input_sha256": _sha256(image_path),
        "status": "inferred",
        "raw_text": result.raw_text,
        "lines": [
            {
                "text": line.text,
                "bbox": list(line.bbox),
                "confidence": line.confidence,
                "reading_order": line.order,
                "candidates": list(line.candidates),
            }
            for line in result.lines
        ],
        "provider": result.metadata.provider,
        "model": result.metadata.model,
        "version": result.metadata.version,
        "preprocessing_hash": result.metadata.preprocessing_hash,
        "latency_ms": result.metadata.latency_ms,
        "corrected_text": None,
        "review_state": "unreviewed",
    }


def run_ocr(
    *,
    page_ids: set[str] | None = None,
    limit: int | None = None,
    inventory_path: Path = INVENTORY_PATH,
    output_path: Path = OUTPUT_PATH,
    provider: OCRProvider | None = None,
) -> dict[str, Any]:
    inventory = _load_inventory(inventory_path)
    pages = [
        page
        for page in inventory["pages"]
        if page_ids is None or page.get("page_id") in page_ids
    ]
    if limit is not None:
        if limit < 1:
            raise ValueError("limit must be positive")
        pages = pages[:limit]
    if not pages:
        raise RealPilotOCRError("no matching pages")
    provider = provider or create_optional_ocr_provider()
    health = provider.health()
    if not health.available:
        raise DomainError("MODEL_UNAVAILABLE", health.details, 503)
    results: list[dict[str, Any]] = []
    for page in pages:
        if not isinstance(page, dict) or not isinstance(page.get("image_path"), str):
            raise RealPilotOCRError("page inventory has an invalid image_path")
        image_path = _resolve_page_image(page["image_path"])
        results.append(_result_record(page, image_path, provider.recognize(image_path)))
    output = {
        "schema_version": "1.0",
        "dataset_id": "real-pilot-v1-ocr",
        "dataset_kind": "real_pilot_raw_ocr",
        "evaluation_status": "not_evaluated",
        "pipeline_version": "real-pilot-ocr-v1",
        "provider": health.as_dict(),
        "pages": results,
        "disclaimer": (
            "raw OCR is machine inference; corrected_text is intentionally empty "
            "until human review."
        ),
    }
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        mode="w", encoding="utf-8", dir=output_path.parent, delete=False, suffix=".part"
    ) as temporary:
        temporary.write(json.dumps(output, ensure_ascii=False, indent=2) + "\n")
        temporary_path = Path(temporary.name)
    temporary_path.replace(output_path)
    return output


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--page-id", action="append", dest="page_ids")
    parser.add_argument("--limit", type=int)
    args = parser.parse_args()
    try:
        output = run_ocr(page_ids=set(args.page_ids or []) or None, limit=args.limit)
    except (RealPilotOCRError, DomainError, ValueError) as exc:
        parser.error(str(exc))
    print(
        json.dumps(
            {
                "status": "passed",
                "pages": len(output["pages"]),
                "evaluation_status": output["evaluation_status"],
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
