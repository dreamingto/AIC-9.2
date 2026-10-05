"""Local-only annotation server for the real-book pilot.

The server deliberately keeps annotation data outside the database and never
serves arbitrary filesystem paths. It is intended for a controlled desktop
review session, not for network deployment.
"""

from __future__ import annotations

import json
import math
import mimetypes
import re
import tempfile
from datetime import UTC, datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import unquote, urlparse

PROJECT_ROOT = Path(__file__).resolve().parents[2]
INVENTORY_PATH = PROJECT_ROOT / "backend" / "data" / "real_pilot" / "derived_pages.json"
OCR_PATH = PROJECT_ROOT / "backend" / "data" / "real_pilot" / "ocr_results.json"
ANNOTATION_PATH = PROJECT_ROOT / "backend" / "data" / "real_pilot" / "annotations.json"
ANNOTATION_HTML = PROJECT_ROOT / "backend" / "data" / "real_pilot" / "annotation_tool.html"
PROCESSED_ROOT = (PROJECT_ROOT / "backend" / "data" / "processed" / "real_pilot_v1").resolve()


class AnnotationError(ValueError):
    """Raised when a local annotation payload is invalid."""


def _read_json(path: Path, default: Any) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return default


def _now() -> str:
    return datetime.now(UTC).isoformat()


def _default_annotation(page_id: str) -> dict[str, Any]:
    return {
        "page_id": page_id,
        "layout": {
            "status": "pending_review",
            "orientation": "vertical_columns",
            "regions": [],
            "reading_order": [],
        },
        "text_layers": {
            "raw_ocr": None,
            "corrected_text": None,
            "correction_state": "unreviewed",
            "reviewer": None,
            "reviewed_at": None,
            "change_log": [],
        },
    }


def _load_state() -> tuple[list[dict[str, Any]], dict[str, dict[str, Any]]]:
    inventory = _read_json(INVENTORY_PATH, {})
    ocr_payload = _read_json(OCR_PATH, {})
    saved = _read_json(ANNOTATION_PATH, {})
    ocr_by_id = {
        item.get("page_id"): item
        for item in ocr_payload.get("pages", [])
        if isinstance(item, dict) and isinstance(item.get("page_id"), str)
    }
    saved_pages = saved.get("pages", {}) if isinstance(saved, dict) else {}
    annotations = saved_pages if isinstance(saved_pages, dict) else {}
    pages: list[dict[str, Any]] = []
    for page in inventory.get("pages", []):
        if not isinstance(page, dict) or not isinstance(page.get("page_id"), str):
            continue
        page_id = page["page_id"]
        ocr = ocr_by_id.get(page_id, {})
        pages.append(
            {
                "page_id": page_id,
                "source_id": page.get("source_id"),
                "book_title": page.get("book_title"),
                "volume": page.get("volume"),
                "pdf_page": page.get("pdf_page"),
                "image_path": page.get("image_path"),
                "width": page.get("width"),
                "height": page.get("height"),
                "sha256": page.get("sha256"),
                "raw_text": ocr.get("raw_text", page.get("ocr", {}).get("raw_text")),
                "ocr_lines": ocr.get("lines", page.get("ocr", {}).get("lines", [])),
                "ocr_provider": {
                    "provider": ocr.get("provider"),
                    "model": ocr.get("model"),
                    "version": ocr.get("version"),
                },
                "annotation": annotations.get(page_id, _default_annotation(page_id)),
            }
        )
    return pages, annotations


def _validate_bbox(value: Any) -> dict[str, float]:
    if not isinstance(value, dict):
        raise AnnotationError("bbox must be an object")
    fields: dict[str, float] = {}
    for key in ("x", "y", "width", "height"):
        item = value.get(key)
        if (
            isinstance(item, bool)
            or not isinstance(item, (int, float))
            or not math.isfinite(float(item))
        ):
            raise AnnotationError("bbox values must be finite numbers")
        fields[key] = float(item)
    x, y, width, height = (fields[key] for key in ("x", "y", "width", "height"))
    if x < 0 or y < 0 or width <= 0 or height <= 0 or x + width > 1 or y + height > 1:
        raise AnnotationError("bbox must stay inside normalized page bounds")
    return {key: float(fields[key]) for key in fields}


def _validate_annotation(page_id: str, payload: Any, raw_text: str | None) -> dict[str, Any]:
    if not isinstance(payload, dict):
        raise AnnotationError("annotation payload must be an object")
    layout = payload.get("layout")
    text_layers = payload.get("text_layers")
    if not isinstance(layout, dict) or not isinstance(text_layers, dict):
        raise AnnotationError("layout and text_layers are required")
    regions = layout.get("regions", [])
    reading_order = layout.get("reading_order", [])
    if not isinstance(regions, list) or not isinstance(reading_order, list):
        raise AnnotationError("regions and reading_order must be arrays")
    normalized_regions: list[dict[str, Any]] = []
    ids: set[str] = set()
    for index, region in enumerate(regions, start=1):
        if not isinstance(region, dict):
            raise AnnotationError("each region must be an object")
        region_id = region.get("region_id") or f"{page_id}-r{index:03d}"
        if not isinstance(region_id, str) or region_id in ids:
            raise AnnotationError("region_id values must be unique")
        ids.add(region_id)
        category = region.get("category", "unknown")
        if category not in {"text", "caption", "figure", "annotation", "unknown"}:
            raise AnnotationError("unsupported region category")
        normalized_regions.append(
            {
                "region_id": region_id,
                "category": category,
                "bbox": _validate_bbox(region.get("bbox")),
                "reading_order": int(region.get("reading_order", index)),
                "review_state": "reviewed",
            }
        )
    order = [item for item in reading_order if isinstance(item, str) and item in ids]
    missing = [
        region["region_id"]
        for region in normalized_regions
        if region["region_id"] not in order
    ]
    order.extend(missing)
    corrected = text_layers.get("corrected_text")
    if corrected is not None and not isinstance(corrected, str):
        raise AnnotationError("corrected_text must be a string or null")
    if isinstance(corrected, str):
        corrected = corrected.strip() or None
    reviewer = text_layers.get("reviewer")
    if reviewer is not None and not isinstance(reviewer, str):
        raise AnnotationError("reviewer must be a string or null")
    previous_log = text_layers.get("change_log", [])
    if not isinstance(previous_log, list):
        raise AnnotationError("change_log must be an array")
    return {
        "page_id": page_id,
        "layout": {
            "status": "reviewed",
            "orientation": layout.get("orientation", "vertical_columns"),
            "regions": normalized_regions,
            "reading_order": order,
        },
        "text_layers": {
            "raw_ocr": raw_text,
            "corrected_text": corrected,
            "correction_state": "reviewed" if corrected is not None else "unreviewed",
            "reviewer": reviewer,
            "reviewed_at": _now(),
            "change_log": previous_log,
        },
        "updated_at": _now(),
    }


def _save_annotations(annotations: dict[str, dict[str, Any]]) -> None:
    payload = {
        "schema_version": "1.0",
        "dataset_id": "real-pilot-v1-annotations",
        "dataset_kind": "real_pilot_annotations",
        "evaluation_status": "not_evaluated",
        "pipeline_version": "real-pilot-annotation-v1",
        "pages": annotations,
    }
    ANNOTATION_PATH.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        mode="w", encoding="utf-8", dir=ANNOTATION_PATH.parent, delete=False, suffix=".part"
    ) as temporary:
        temporary.write(json.dumps(payload, ensure_ascii=False, indent=2) + "\n")
        temporary_path = Path(temporary.name)
    temporary_path.replace(ANNOTATION_PATH)


class AnnotationHandler(BaseHTTPRequestHandler):
    server_version = "TujiAnnotation/1.0"

    def _send_json(self, status: int, payload: Any) -> None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _send_bytes(self, status: int, body: bytes, content_type: str) -> None:
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:  # noqa: N802
        parsed = urlparse(self.path)
        if parsed.path == "/" or parsed.path == "/index.html":
            try:
                self._send_bytes(200, ANNOTATION_HTML.read_bytes(), "text/html; charset=utf-8")
            except OSError:
                self._send_json(500, {"error": "annotation tool is missing"})
            return
        pages, _ = _load_state()
        if parsed.path == "/api/pages":
            summaries = [
                {
                    "page_id": page["page_id"],
                    "pdf_page": page["pdf_page"],
                    "width": page["width"],
                    "height": page["height"],
                    "raw_chars": len(page["raw_text"] or ""),
                    "ocr_lines": len(page["ocr_lines"]),
                    "layout_status": page["annotation"].get("layout", {}).get("status"),
                    "correction_state": page["annotation"]
                    .get("text_layers", {})
                    .get("correction_state"),
                }
                for page in pages
            ]
            self._send_json(200, {"pages": summaries, "evaluation_status": "not_evaluated"})
            return
        page_match = re.fullmatch(r"/api/page/(.+)", parsed.path)
        if page_match:
            page_id = unquote(page_match.group(1))
            page = next((item for item in pages if item["page_id"] == page_id), None)
            if page is None:
                self._send_json(404, {"error": "page not found"})
                return
            page["image_url"] = f"/assets/{page['source_id']}/page-{int(page['pdf_page']):04d}.png"
            self._send_json(200, page)
            return
        asset_match = re.fullmatch(r"/assets/([^/]+)/([^/]+\.png)", parsed.path)
        if asset_match:
            source_id, filename = asset_match.groups()
            candidate = (PROCESSED_ROOT / source_id / filename).resolve()
            try:
                candidate.relative_to(PROCESSED_ROOT)
            except ValueError:
                self._send_json(403, {"error": "asset path rejected"})
                return
            if not candidate.is_file():
                self._send_json(404, {"error": "asset not found"})
                return
            content_type = mimetypes.guess_type(candidate.name)[0] or "image/png"
            self._send_bytes(200, candidate.read_bytes(), content_type)
            return
        self._send_json(404, {"error": "not found"})

    def do_POST(self) -> None:  # noqa: N802
        page_match = re.fullmatch(r"/api/page/(.+)", urlparse(self.path).path)
        if page_match is None:
            self._send_json(404, {"error": "not found"})
            return
        page_id = unquote(page_match.group(1))
        pages, annotations = _load_state()
        page = next((item for item in pages if item["page_id"] == page_id), None)
        if page is None:
            self._send_json(404, {"error": "page not found"})
            return
        try:
            length = int(self.headers.get("Content-Length", "0"))
            if length <= 0 or length > 2_000_000:
                raise AnnotationError("request body size is invalid")
            payload = json.loads(self.rfile.read(length).decode("utf-8"))
            annotation = _validate_annotation(page_id, payload, page["raw_text"])
            previous = annotations.get(page_id)
            previous_corrected = (previous or {}).get("text_layers", {}).get("corrected_text")
            corrected = annotation["text_layers"]["corrected_text"]
            if corrected != previous_corrected:
                annotation["text_layers"]["change_log"].append(
                    {
                        "from": previous_corrected,
                        "to": corrected,
                        "reviewer": annotation["text_layers"]["reviewer"],
                        "changed_at": annotation["text_layers"]["reviewed_at"],
                        "reason": "manual_transcription_review",
                    }
                )
            annotations[page_id] = annotation
            _save_annotations(annotations)
        except (AnnotationError, json.JSONDecodeError, UnicodeDecodeError, ValueError) as exc:
            self._send_json(422, {"error": str(exc)})
            return
        self._send_json(200, {"status": "saved", "page_id": page_id, "annotation": annotation})

    def log_message(self, format: str, *args: Any) -> None:
        del format, args


def main() -> int:
    import argparse

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8765)
    args = parser.parse_args()
    server = ThreadingHTTPServer((args.host, args.port), AnnotationHandler)
    print(f"annotation server listening at http://{args.host}:{args.port}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
