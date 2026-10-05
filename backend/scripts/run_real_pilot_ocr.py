"""Run the optional OCR provider against a prepared real-page inventory.

The command writes raw OCR only.  It never fills ``corrected_text`` or marks a
transcription as verified; those fields belong to the human review pass.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import tempfile
from collections.abc import Callable
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
    ids: set[str] = set()
    for page in pages:
        if not isinstance(page, dict) or not all(
            isinstance(page.get(key), str) and page[key]
            for key in ("page_id", "source_id", "image_path", "sha256")
        ):
            raise RealPilotOCRError("invalid page record in inventory")
        if page["page_id"] in ids:
            raise RealPilotOCRError("duplicate page_id in inventory")
        ids.add(page["page_id"])
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
    resume: bool = False,
    progress: Callable[[dict[str, Any]], None] | None = None,
) -> dict[str, Any]:
    if inventory_path.resolve() != INVENTORY_PATH.resolve() and (
        output_path.resolve() == OUTPUT_PATH.resolve()
    ):
        raise RealPilotOCRError("alternate inventory requires a separate --output")
    if output_path.resolve() == inventory_path.resolve():
        raise RealPilotOCRError("OCR output must not overwrite inventory")
    inventory = _load_inventory(inventory_path)
    known_ids = {page["page_id"] for page in inventory["pages"]}
    if page_ids and (unknown := page_ids - known_ids):
        raise RealPilotOCRError(f"unknown page IDs: {', '.join(sorted(unknown))}")
    pages = [
        page for page in inventory["pages"] if page_ids is None or page.get("page_id") in page_ids
    ]
    if limit is not None:
        if limit < 1:
            raise ValueError("limit must be positive")
        pages = pages[:limit]
    if not pages:
        raise RealPilotOCRError("no matching pages")
    images: dict[str, Path] = {}
    for page in pages:
        image_path = _resolve_page_image(page["image_path"])
        if _sha256(image_path) != page["sha256"]:
            raise RealPilotOCRError(f"inventory image hash mismatch: {page['page_id']}")
        images[page["page_id"]] = image_path
    if output_path.exists() and not resume:
        raise RealPilotOCRError("output already exists; use --resume or a new output name")
    provider = provider or create_optional_ocr_provider()
    health = provider.health()
    if not health.available:
        raise DomainError("MODEL_UNAVAILABLE", health.details, 503)
    signature = {
        key: health.as_dict()[key] for key in ("provider", "model", "version", "preprocessing_hash")
    }
    identity = {
        "inventory_sha256": _sha256(inventory_path),
        "requested_page_ids": [page["page_id"] for page in pages],
        "provider_signature": signature,
    }
    results: list[dict[str, Any]] = []
    if output_path.exists():
        try:
            cached = json.loads(output_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise RealPilotOCRError("unable to read existing OCR checkpoint") from exc
        if (
            not isinstance(cached, dict)
            or cached.get("dataset_kind") != "real_pilot_raw_ocr"
            or cached.get("run_identity") != identity
            or not isinstance(cached.get("pages"), list)
        ):
            raise RealPilotOCRError("checkpoint scope/model changed; use a new output name")
        for record in cached["pages"]:
            if not isinstance(record, dict) or (
                record.get("corrected_text") is not None
                or record.get("review_state") != "unreviewed"
                or record.get("status") != "inferred"
            ):
                raise RealPilotOCRError("checkpoint contains reviewed or invalid data")
            if record.get("page_id") not in identity["requested_page_ids"]:
                raise RealPilotOCRError("checkpoint contains a page outside its scope")
            expected = next(p for p in pages if p["page_id"] == record["page_id"])
            if record.get("input_sha256") != expected["sha256"] or any(
                record.get(key) != value for key, value in signature.items()
            ):
                raise RealPilotOCRError("checkpoint image/model fingerprint mismatch")
            if record.get("result_sha256") != _record_hash(record):
                raise RealPilotOCRError("checkpoint result integrity mismatch")
            results.append(record)
        if len({r["page_id"] for r in results}) != len(results):
            raise RealPilotOCRError("checkpoint contains duplicate results")
    output = {
        "schema_version": "1.0",
        "dataset_id": "real-pilot-v1-ocr",
        "dataset_kind": "real_pilot_raw_ocr",
        "evaluation_status": "not_evaluated",
        "pipeline_version": "real-pilot-ocr-v2-checkpoint",
        "run_identity": identity,
        "run_status": "running",
        "provider": health.as_dict(),
        "pages": results,
        "disclaimer": (
            "raw OCR is machine inference; corrected_text is intentionally empty "
            "until human review."
        ),
    }
    completed = {record["page_id"] for record in results}
    if progress:
        progress({"event": "start", "requested": len(pages), "reused": len(completed)})
    _save_output(output_path, output)
    try:
        for page in pages:
            if page["page_id"] in completed:
                continue
            image_path = images[page["page_id"]]
            record = _result_record(page, image_path, provider.recognize(image_path))
            if record["input_sha256"] != page["sha256"] or any(
                record[key] != value for key, value in signature.items()
            ):
                raise RealPilotOCRError("OCR input or provider changed during recognition")
            record["result_sha256"] = _record_hash(record)
            results.append(record)
            _save_output(output_path, output)
            if progress:
                progress({"event": "page", "page_id": page["page_id"], "done": len(results)})
    except Exception as exc:
        output["run_status"] = "failed"
        output["failure_type"] = type(exc).__name__
        _save_output(output_path, output)
        raise
    rank = {page["page_id"]: i for i, page in enumerate(pages)}
    results.sort(key=lambda record: rank[record["page_id"]])
    output["run_status"] = "completed"
    _save_output(output_path, output)
    return output


def _record_hash(record: dict[str, Any]) -> str:
    payload = {key: value for key, value in record.items() if key != "result_sha256"}
    return hashlib.sha256(
        json.dumps(payload, sort_keys=True, ensure_ascii=False, allow_nan=False).encode("utf-8")
    ).hexdigest()


def _save_output(output_path: Path, output: dict[str, Any]) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        mode="w", encoding="utf-8", dir=output_path.parent, delete=False, suffix=".part"
    ) as temporary:
        temporary.write(json.dumps(output, ensure_ascii=False, indent=2) + "\n")
        temporary_path = Path(temporary.name)
    temporary_path.replace(output_path)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--page-id", action="append", dest="page_ids")
    parser.add_argument("--limit", type=int)
    parser.add_argument("--inventory", type=Path, default=INVENTORY_PATH)
    parser.add_argument("--output", type=Path, default=OUTPUT_PATH)
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--selection", type=Path, help="JSON object containing page_ids")
    args = parser.parse_args()
    try:
        selected_ids = set(args.page_ids or [])
        if args.selection:
            selection = json.loads(args.selection.read_text(encoding="utf-8"))
            ids = selection.get("page_ids") if isinstance(selection, dict) else None
            if not isinstance(ids, list) or not ids or not all(isinstance(i, str) for i in ids):
                raise RealPilotOCRError("selection must contain a nonempty page_ids array")
            selected_ids.update(ids)
        output = run_ocr(
            page_ids=selected_ids or None,
            limit=args.limit,
            inventory_path=args.inventory,
            output_path=args.output,
            resume=args.resume,
            progress=lambda event: print(json.dumps(event, ensure_ascii=False), flush=True),
        )
    except (RealPilotOCRError, DomainError, ValueError, OSError) as exc:
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
