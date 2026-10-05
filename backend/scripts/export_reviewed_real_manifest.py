"""Export confirmed figure extents/titles only after human-truth and hash gates.

The export is deliberately conservative: page body text is not automatically
associated with a figure, and no function, graph, or relevance labels are fabricated.
Transcription review does not change historical Evidence to Verified.
"""

from __future__ import annotations

import argparse
import json
import shutil
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Any

from app.ingestion.contracts import RealManifest
from app.ingestion.loader import load_manifest, validate_manifest_name
from scripts.convert_ppocrlabel_annotations import (
    PROJECT_ROOT,
    ConversionError,
    _read_json_object,
    _sha256,
    _write_json_atomic,
)
from scripts.evaluate_competition_ocr import evaluate_scope, verify_frozen_snapshot

DATA_ROOT = PROJECT_ROOT / "backend/data"
PIPELINE_VERSION = "reviewed-real-title-import-v1"


def _confirmation(record: dict[str, Any]) -> dict[str, Any]:
    if record.get("confirmed") is not True:
        raise ConversionError("figure/title requires explicit human confirmation")
    return {key: record[key] for key in ("confirmed", "reviewer", "reviewed_at")}


def _build_manifest(
    snapshot: Path,
    sources_path: Path,
) -> tuple[RealManifest, dict[str, Path]]:
    frozen = verify_frozen_snapshot(snapshot)
    evaluation = frozen.get("evaluation", {})
    if (
        evaluation.get("evaluation_status") != "evaluated"
        or not evaluation.get("readiness")
        or not all(p.get("ready") is True for p in evaluation["readiness"])
    ):
        raise ConversionError("snapshot is not a complete human-reviewed scope")
    annotation = _read_json_object(snapshot / "annotations.json")
    scope = _read_json_object(snapshot / "scope.json")
    overrides = _read_json_object(snapshot / "human-overrides.json")
    candidates = _read_json_object(snapshot / "candidates.json")
    if (
        annotation.get("review_import", {}).get("override_sha256")
        != frozen["files"]["human-overrides.json"]
    ):
        raise ConversionError("snapshot lacks matching human review import")
    registry = _read_json_object(sources_path)
    source = next((s for s in registry["sources"] if s["source_id"] == scope["source_id"]), None)
    if source is None:
        raise ConversionError("review source is absent from the provenance registry")
    records = {r["box_or_figure_id"]: r for r in overrides["records"]}
    raw_boxes = {box["box_id"]: box for page in candidates["pages"] for box in page["boxes"]}
    figures, regions, chunks, evidence, audits = [], [], [], [], []
    pages, assets = [], []
    files: dict[str, Path] = {}
    for selected in scope["pages"]:
        page_id = selected["page_id"]
        if selected["pdf_sha256"] != source["sha256"]:
            raise ConversionError("source registry PDF hash differs from frozen scope")
        page = annotation["pages"][page_id]
        selected_ids = set(selected["figure_ids"])
        own_figures = [f for f in page.get("figures", []) if f["figure_id"] in selected_ids]
        if {f["figure_id"] for f in own_figures} != selected_ids:
            raise ConversionError("frozen figure inventory is incomplete")
        if not own_figures:
            continue
        asset_id = page_id + "-scan"
        image = snapshot / "images" / (page_id + ".png")
        relative = f"reviewed_real_v1/{snapshot.name}/{page_id}.png"
        files[relative] = image
        assets.append(
            {
                "asset_id": asset_id,
                "relative_path": relative,
                "sha256": selected["image_sha256"],
                "width": page["width"],
                "height": page["height"],
            }
        )
        pages.append(
            {
                "page_id": page_id,
                "source_id": scope["source_id"],
                "volume": source["volume"],
                "page_or_folio": f"pdf-page-{selected['pdf_page']:04d}",
            }
        )
        for figure in own_figures:
            figure_id, title_id = figure["figure_id"], figure["title_box_id"]
            region_review, title_review = records.get(figure_id, {}), records.get(title_id, {})
            if (
                figure.get("region_verification_state") != "verified"
                or figure.get("title_verification_state") != "verified"
                or region_review.get("category") != "figure"
                or title_review.get("category") != "caption"
                or title_review.get("role") != "figure_title"
                or not figure.get("title")
                or figure["title"] != title_review.get("corrected_text")
                or figure["bbox"] != region_review.get("bbox")
            ):
                raise ConversionError(f"figure extent or title still unconfirmed: {figure_id}")
            title = figure["title"]
            if len(title) > 500:
                raise ConversionError("figure title exceeds database length")
            figures.append(
                {
                    "figure_id": figure_id,
                    "page_id": page_id,
                    "asset_id": asset_id,
                    "title": title,
                    "caption": title,
                    "bbox": figure["bbox"],
                    "original_path": relative,
                }
            )
            regions.append(
                {
                    "region_id": figure_id + "-extent",
                    "figure_id": figure_id,
                    "label": "人工确认技术图区",
                    "role": "figure_extent",
                    "bbox": figure["bbox"],
                }
            )
            text_id = figure_id + "-title"
            chunks.append(
                {
                    "text_id": text_id,
                    "figure_id": figure_id,
                    "kind": "title",
                    "content": title,
                    "evidence_state": "Documented",
                    "transcription_review": {
                        "box_id": title_id,
                        "bbox": title_review["bbox"],
                        "raw_text": raw_boxes.get(title_id, {}).get("raw_text"),
                        "confirmation": _confirmation(title_review),
                    },
                }
            )
            audits.append(
                {
                    "figure_id": figure_id,
                    "page_id": page_id,
                    "title_box_id": title_id,
                    "region_confirmation": _confirmation(region_review),
                    "title_confirmation": _confirmation(title_review),
                }
            )
            for suffix, kind, state, ref, excerpt in (
                ("image", "image", "Observed", asset_id, "扫描中人工确认的技术图区，见图 bbox。"),
                ("title", "text", "Documented", text_id, title),
                ("source", "metadata", "Documented", scope["source_id"], source["edition_note"]),
            ):
                evidence.append(
                    {
                        "evidence_id": figure_id + "-" + suffix + "-evidence",
                        "figure_id": figure_id,
                        "kind": kind,
                        "state": state,
                        "source_ref": ref,
                        "excerpt": excerpt[:1000],
                    }
                )
    if not figures:
        raise ConversionError("reviewed scope has no exportable figures")
    generated_at = max(
        datetime.fromisoformat(r["region_confirmation"]["reviewed_at"]) for r in audits
    ).isoformat()
    manifest = RealManifest.model_validate(
        {
            "fixture_id": "reviewed-" + snapshot.name[-16:],
            "title": "机图索隐真实古籍已确认图区/图题",
            "description": "只导入扫描级人工确认的图区与图题；正文归属、功能和关联未标注。",
            "dataset_kind": "human_reviewed_real_pilot",
            "evaluation_status": "not_evaluated",
            "generated_at": generated_at,
            "generator_version": PIPELINE_VERSION,
            "disclaimer": "业务导入不等于检索效果验证或历史主张核验，retrieval not_evaluated。",
            "sources": [
                {
                    "source_id": source["source_id"],
                    "source_url": source["source_url"],
                    "source_name": source["source_name"],
                    "book_title": source["book_title"],
                    "author": source["author"],
                    "era": "见来源作者与版本目录，未另行推断",
                    "edition": source["edition_note"],
                    "volume": source["volume"],
                    "page_or_folio": "见扫描页记录",
                    "license_status": source["license_status"],
                    "license_note": source["license_note"],
                    "allow_training": source["allow_training"],
                    "allow_redistribution": source["allow_redistribution"],
                    "retrieved_at": source.get("retrieved_at", registry["retrieved_at"]),
                    "pipeline_version": PIPELINE_VERSION,
                    "original_sha256": source["sha256"],
                }
            ],
            "assets": assets,
            "pages": pages,
            "figures": figures,
            "regions": regions,
            "text_chunks": chunks,
            "evidence": evidence,
            "review_audit": {
                "review_scope": "figure_extent_and_title_only",
                "snapshot_id": snapshot.name,
                "snapshot_manifest_sha256": _sha256(snapshot / "manifest.json"),
                "annotation_sha256": frozen["files"]["annotations.json"],
                "override_sha256": frozen["files"]["human-overrides.json"],
                "candidate_sha256": frozen["files"]["candidates.json"],
                "scope_sha256": frozen["files"]["scope.json"],
                "source_registry_sha256": _sha256(sources_path),
                "figures": audits,
            },
        }
    )
    return manifest, files


def export_reviewed_manifest(
    *,
    manifest_name: str = "reviewed-real-core-v1.json",
    manifests_root: Path = DATA_ROOT / "manifests",
    assets_root: Path = DATA_ROOT / "assets",
    sources_path: Path = DATA_ROOT / "real_pilot/sources.json",
    report_path: Path = DATA_ROOT / "real_pilot/real_export_report.json",
    evaluation_kwargs: dict[str, Any] | None = None,
) -> dict[str, Any]:
    name = validate_manifest_name(manifest_name)
    if not name.startswith("reviewed-real-"):
        raise ConversionError("real manifests must use the reviewed-real- prefix")
    kwargs = dict(evaluation_kwargs or {})
    kwargs["freeze"] = True
    evaluation = evaluate_scope(**kwargs)
    report: dict[str, Any] = {
        "dataset_kind": "reviewed_real_export_report",
        "status": "blocked_pending_human_truth",
        "manifest_name": name,
        "ready_pages": sum(p["ready"] for p in evaluation["readiness"]),
        "scope_pages": len(evaluation["readiness"]),
        "exported_figures": 0,
        "evaluation_status": "not_evaluated",
    }
    if evaluation.get("freeze_status") != "frozen_verified":
        _write_json_atomic(report_path, report)
        return report
    snapshot = Path(evaluation["snapshot_path"])
    manifest, files = _build_manifest(snapshot, sources_path)
    destination = assets_root / "reviewed_real_v1" / snapshot.name
    manifest_path = manifests_root / name
    payload = manifest.model_dump(mode="json")
    if manifest_path.exists() and _read_json_object(manifest_path) != payload:
        raise ConversionError("existing real manifest differs; choose a new name")
    if destination.exists():
        for relative, original in files.items():
            existing = assets_root / relative
            if not existing.is_file() or _sha256(existing) != _sha256(original):
                raise ConversionError("existing export asset differs from the frozen scan")
    else:
        destination.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(prefix="real-export-", dir=destination.parent) as temp:
            staging = Path(temp)
            for original in files.values():
                target = staging / original.name
                shutil.copyfile(original, target)
                if _sha256(target) != _sha256(original):
                    raise ConversionError("export scan copy hash mismatch")
            staging.rename(destination)
    _write_json_atomic(manifest_path, payload)
    validated = load_manifest(name, manifests_root=manifests_root, assets_root=assets_root)
    report.update(
        {
            "status": "exported_validated_not_imported",
            "exported_figures": len(manifest.figures),
            "snapshot_id": snapshot.name,
            "manifest_sha256": _sha256(manifest_path),
            "counts": validated.counts,
        }
    )
    _write_json_atomic(report_path, report)
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest-name", default="reviewed-real-core-v1.json")
    parser.add_argument(
        "--report", type=Path, default=DATA_ROOT / "real_pilot/real_export_report.json"
    )
    for name in ("candidate", "scope", "annotation", "overrides", "evaluation-report"):
        parser.add_argument("--" + name, type=Path)
    args = parser.parse_args()
    try:
        paths = {
            "candidate_path": args.candidate,
            "scope_path": args.scope,
            "annotation_path": args.annotation,
            "override_path": args.overrides,
            "report_path": args.evaluation_report,
        }
        report = export_reviewed_manifest(
            manifest_name=args.manifest_name,
            report_path=args.report,
            evaluation_kwargs={name: path for name, path in paths.items() if path is not None},
        )
    except (ValueError, OSError) as exc:
        parser.error(str(exc))
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["status"] == "exported_validated_not_imported" else 2


if __name__ == "__main__":
    raise SystemExit(main())
