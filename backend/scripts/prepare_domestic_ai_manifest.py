"""Hash-bound domestic scan import for an explicitly AI-assisted competition demo.

This path never reads/writes human review exports, corrected truth, or qrels.
The original scans and OCR stay intact; only selected scene-local raw lines
and separately attributed visual descriptions enter the business manifest.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
from pathlib import Path
from typing import Any, Literal

from PIL import Image
from pydantic import Field

from app.ingestion.contracts import (
    AIRealManifest,
    Identifier,
    NonEmptyText,
    NormalizedBBox,
    StrictModel,
)
from app.ingestion.loader import load_manifest, resolve_contained_path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
VERSION = "domestic-ai-scenes-v1"


class SceneRegion(StrictModel):
    label: NonEmptyText
    bbox: NormalizedBBox


class Scene(StrictModel):
    figure_id: Identifier
    page_id: Identifier
    title: NonEmptyText
    title_origin: Literal["ai_visual_description", "ai_visual_transcription"]
    description: NonEmptyText
    bbox: NormalizedBBox
    title_bbox: NormalizedBBox | None = None
    regions: list[SceneRegion] = Field(min_length=1)
    visual_note: NonEmptyText


class Selection(StrictModel):
    schema_version: Literal["1.0"]
    selection_id: Identifier
    review_origin: Literal["ai_assisted"]
    human_review_status: Literal["skipped_by_user_for_competition"]
    evaluation_status: Literal["not_evaluated"]
    priority: Literal["domestic_publication"]
    disclaimer: NonEmptyText
    source_categories: dict[str, Literal["domestic_publication", "domestic_holding"]]
    scope_note: NonEmptyText
    figures: list[Scene] = Field(min_length=1)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _read(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError("input must be a JSON object")
    return value


def _immutable_write(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        if path.read_bytes() != data:
            raise ValueError(f"refuse to overwrite immutable output: {path.name}")
        return
    with path.open("xb") as stream:
        stream.write(data)


def _json_bytes(value: dict[str, Any]) -> bytes:
    return (json.dumps(value, ensure_ascii=False, indent=2) + "\n").encode("utf-8")


def _inside(inner: NormalizedBBox, outer: NormalizedBBox) -> bool:
    return (
        inner.x >= outer.x - 1e-9 and inner.y >= outer.y - 1e-9
        and inner.x + inner.width <= outer.x + outer.width + 1e-9
        and inner.y + inner.height <= outer.y + outer.height + 1e-9
    )


def _raw_lines(page: dict[str, Any], scene: Scene, width: int, height: int) -> list[dict[str, Any]]:
    selected = []
    for index, line in enumerate(page["lines"]):
        if not str(line["text"]).strip():
            continue
        left, top, right, bottom = line["bbox"]
        box = NormalizedBBox(
            x=left / width, y=top / height,
            width=(right - left) / width, height=(bottom - top) / height,
        )
        # Entirely within the selected scene: no neighbouring scene or header poem.
        if _inside(box, scene.bbox):
            selected.append({
                "line_index": index, "bbox": box.model_dump(), "text": line["text"],
                "confidence": line["confidence"], "reading_order": line["reading_order"],
            })
    return selected


def prepare(
    *, project_root: Path, selection_path: Path, source_registry: Path,
    inventory_path: Path, raw_ocr_path: Path, assets_root: Path, manifests_root: Path,
    report_root: Path,
) -> dict[str, Any]:
    selection = Selection.model_validate(_read(selection_path))
    registry = _read(source_registry)
    inventory = _read(inventory_path)
    raw = _read(raw_ocr_path)
    hashes = {
        "source_registry_sha256": sha256(source_registry),
        "inventory_sha256": sha256(inventory_path),
        "raw_ocr_sha256": sha256(raw_ocr_path),
        "selection_sha256": sha256(selection_path),
    }
    if raw["run_status"] != "completed" or raw["run_identity"]["inventory_sha256"] != hashes[
        "inventory_sha256"
    ]:
        raise ValueError("OCR is incomplete or bound to another inventory")
    figure_ids = [f.figure_id for f in selection.figures]
    if len(figure_ids) != len(set(figure_ids)):
        raise ValueError("duplicate selected figure IDs")
    sources = {s["source_id"]: s for s in registry["sources"]}
    pages = {p["page_id"]: p for p in inventory["pages"]}
    ocr_pages = {p["page_id"]: p for p in raw["pages"]}
    if len(pages) != len(inventory["pages"]) or len(ocr_pages) != len(raw["pages"]):
        raise ValueError("duplicate page IDs")
    selected_ids = sorted({f.page_id for f in selection.figures})
    if not set(selected_ids).issubset(pages) or not set(selected_ids).issubset(ocr_pages):
        raise ValueError("selected page missing from scan inventory or raw OCR")
    source_ids = sorted({pages[p]["source_id"] for p in selected_ids})
    if set(source_ids) != set(selection.source_categories):
        raise ValueError("source category audit must match exactly the selected sources")
    domestic_count = sum(
        selection.source_categories[pages[f.page_id]["source_id"]] == "domestic_publication"
        for f in selection.figures
    )
    if domestic_count <= len(selection.figures) / 2:
        raise ValueError("domestic publication scenes must form the majority")
    fingerprint = hashlib.sha256(
        json.dumps({"version": VERSION, **hashes}, sort_keys=True).encode()
    ).hexdigest()[:16]
    prefix = f"ai_real_v1/{fingerprint}"
    payload: dict[str, Any] = {
        "schema_version": "1.0", "fixture_id": f"domestic-ai-{fingerprint}",
        "title": "国内古籍 AI 辅助比赛演示数据",
        "description": "国内出版《耕织图》优先，国图《天工开物》补充；AI辅助整理，暂不人工审核。",
        "dataset_kind": "ai_assisted_real_pilot", "evaluation_status": "not_evaluated",
        "generated_at": inventory["generated_at"], "generator_version": VERSION,
        "disclaimer": selection.disclaimer + " " + selection.scope_note,
        "sources": [], "assets": [], "pages": [], "figures": [], "regions": [],
        "text_chunks": [], "evidence": [], "functional_assertions": [], "relations": [],
        "benchmark_pairs": [],
        "ai_audit": {
            "review_origin": "ai_assisted", "human_review": False,
            "human_review_status": selection.human_review_status,
            "independent_ground_truth": False, **hashes, "pages": [], "figures": [],
        },
    }
    for source_id in source_ids:
        source = sources[source_id]
        pdf = resolve_contained_path(
            project_root / "backend/data/assets/real_pilot_v1", source["local_filename"]
        )
        if sha256(pdf) != source["sha256"]:
            raise ValueError("original PDF hash mismatch")
        if not source["allow_redistribution"]:
            raise ValueError("this demo export requires permission to redistribute selected scans")
        payload["sources"].append({
            "source_id": source_id, "source_url": source["source_url"],
            "source_name": source["source_name"], "book_title": source["book_title"],
            "author": source["author"], "era": "清" if "zhsy" in source_id else "明",
            "edition": source["edition_note"], "volume": source["volume"],
            "page_or_folio": "selected-pdf-pages",
            "license_status": source["license_status"], "license_note": source["license_note"],
            "allow_training": source["allow_training"],
            "allow_redistribution": source["allow_redistribution"],
            "retrieved_at": source.get("retrieved_at", registry.get("retrieved_at")),
            "pipeline_version": VERSION, "original_sha256": source["sha256"],
            "source_category": selection.source_categories[source_id],
        })
    copied_assets: list[tuple[Path, Path]] = []
    for page_id in selected_ids:
        page, ocr = pages[page_id], ocr_pages[page_id]
        source = sources[page["source_id"]]
        scan = resolve_contained_path(project_root, page["image_path"])
        if (
            sha256(scan) != page["sha256"] or ocr["input_sha256"] != page["sha256"]
            or ocr["source_id"] != page["source_id"] or ocr["status"] != "inferred"
            or page["provenance"]["pdf_sha256"] != source["sha256"]
        ):
            raise ValueError("scan, PDF provenance or raw OCR input hash mismatch")
        with Image.open(scan) as image:
            if image.format != "PNG" or image.size != (page["width"], page["height"]):
                raise ValueError("scan dimensions/format mismatch")
            image.verify()
        relative = f"{prefix}/{page_id}.png"
        destination = resolve_contained_path(assets_root, relative)
        copied_assets.append((scan, destination))
        payload["assets"].append({
            "asset_id": page_id, "relative_path": relative, "sha256": page["sha256"],
            "width": page["width"], "height": page["height"], "mime_type": "image/png",
        })
        payload["pages"].append({
            "page_id": page_id, "source_id": page["source_id"],
            "volume": page["volume"], "page_or_folio": page["page_or_folio"],
        })
        payload["ai_audit"]["pages"].append({
            "page_id": page_id, "source_id": page["source_id"],
            "image_sha256": page["sha256"],
        })
    for scene in selection.figures:
        page, ocr = pages[scene.page_id], ocr_pages[scene.page_id]
        sid = scene.figure_id
        payload["figures"].append({
            "figure_id": sid, "page_id": scene.page_id, "asset_id": scene.page_id,
            "title": scene.title, "caption": scene.description, "bbox": scene.bbox.model_dump(),
            "original_path": f"{prefix}/{scene.page_id}.png",
        })
        payload["ai_audit"]["figures"].append({
            "figure_id": sid, "page_id": scene.page_id, "bbox": scene.bbox.model_dump(),
            "title_origin": scene.title_origin, "visual_checked": True, "note": scene.visual_note,
        })
        for index, region in enumerate(scene.regions):
            if not _inside(region.bbox, scene.bbox):
                raise ValueError("AI focus region escapes its figure")
            payload["regions"].append({
                "region_id": f"{sid}-r{index}", "figure_id": sid, "label": region.label,
                "role": "ai_selected_structure", "bbox": region.bbox.model_dump(),
                "evidence_state": "Inferred",
            })
        visual_provider = {
            "provider": "codex_visual_assistance", "model": "unreported", "version": "unreported",
        }
        for kind, content, origin, bbox in [
            ("title", scene.title, scene.title_origin, scene.title_bbox or scene.bbox),
            ("context", scene.description, "ai_visual_description", scene.bbox),
        ]:
            tid = f"{sid}-{kind}"
            payload["text_chunks"].append({
                "text_id": tid, "figure_id": sid, "kind": kind, "content": content,
                "evidence_state": "Inferred", "ai_trace": {
                    "origin": origin, "page_id": scene.page_id, "bbox": bbox.model_dump(),
                    **visual_provider,
                },
            })
            payload["evidence"].append({
                "evidence_id": f"{sid}-e-{kind}", "figure_id": sid, "kind": "text",
                "state": "Inferred", "source_ref": tid, "excerpt": content,
            })
        lines = _raw_lines(ocr, scene, page["width"], page["height"])
        if lines:
            content = "\n".join(line["text"] for line in lines)
            tid = f"{sid}-raw"
            payload["text_chunks"].append({
                "text_id": tid, "figure_id": sid, "kind": "ocr", "content": content,
                "evidence_state": "Inferred", "ai_trace": {
                    "origin": "raw_ocr", "page_id": scene.page_id,
                    "bbox": scene.bbox.model_dump(), "provider": ocr["provider"],
                    "model": ocr["model"], "version": ocr["version"], "raw_lines": lines,
                },
            })
            payload["evidence"].append({
                "evidence_id": f"{sid}-e-raw", "figure_id": sid, "kind": "text",
                "state": "Inferred", "source_ref": tid,
                "excerpt": "机器原始OCR（未校订，不代表可靠古文）：" + content[:900],
            })
        payload["evidence"].extend([
            {"evidence_id": f"{sid}-e-image", "figure_id": sid, "kind": "image",
             "state": "Observed", "source_ref": scene.page_id,
             "excerpt": "真实扫描图像；AI框选范围未人工核实，原图水印保持。"},
            {"evidence_id": f"{sid}-e-source", "figure_id": sid, "kind": "metadata",
             "state": "Documented", "source_ref": page["source_id"],
             "excerpt": f"{sources[page['source_id']]['source_name']}；PDF第{page['pdf_page']}页。"
                        "来源目录记录，不作独立版本鉴定；AI辅助/暂不人工审核/not_evaluated。"},
        ])
    # Validate the complete portable contract BEFORE generating any output.
    manifest = AIRealManifest.model_validate(payload)
    for scan, destination in copied_assets:
        destination.parent.mkdir(parents=True, exist_ok=True)
        if destination.exists():
            if sha256(destination) != sha256(scan):
                raise ValueError("refuse to overwrite changed scan copy")
        else:
            shutil.copyfile(scan, destination)
    name = f"ai-real-domestic-{fingerprint}.json"
    _immutable_write(manifests_root / name, _json_bytes(manifest.model_dump(mode="json")))
    validated = load_manifest(name, manifests_root=manifests_root, assets_root=assets_root)
    report = {
        "manifest_name": name, "manifest_sha256": sha256(manifests_root / name),
        "dataset_kind": manifest.dataset_kind, "counts": validated.counts,
        "domestic_publication_figures": domestic_count,
        "domestic_holding_figures": len(selection.figures) - domestic_count,
        "human_review": False, "evaluation_status": "not_evaluated",
        "metrics": None, "independent_ground_truth": False,
        "scoped_raw_lines": sum(
            len(c.ai_trace.raw_lines) for c in manifest.text_chunks if c.ai_trace
        ),
        "figures": [
            {"figure_id": f.figure_id, "page_id": f.page_id, "title": f.title,
             "bbox": f.bbox.model_dump()} for f in manifest.figures
        ],
        **hashes,
    }
    _immutable_write(report_root / fingerprint / "export-report.json", _json_bytes(report))
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project-root", type=Path, default=PROJECT_ROOT)
    args = parser.parse_args()
    root = args.project_root.resolve()
    pilot = root / "backend/data/real_pilot"
    report = prepare(
        project_root=root, selection_path=pilot / "domestic_ai_selection.json",
        source_registry=pilot / "sources.json", inventory_path=pilot / "supplementary_pages.json",
        raw_ocr_path=pilot / "supplementary_ocr_results.json",
        assets_root=root / "backend/data/assets", manifests_root=root / "backend/data/manifests",
        report_root=pilot / "ai_domestic_exports",
    )
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
