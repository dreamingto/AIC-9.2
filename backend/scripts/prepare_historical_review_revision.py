"""Create an immutable supplement revision while preserving original OCR inputs."""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import re
from pathlib import Path
from typing import Any

from scripts.apply_historical_review_overrides import _bbox
from scripts.build_historical_review_queue import TEMPLATE_PATH, build_review_queue
from scripts.convert_ppocrlabel_annotations import (
    INVENTORY_PATH,
    PROJECT_ROOT,
    ConversionError,
    _read_json_object,
    _sha256,
    _write_json_atomic,
)
from scripts.generate_historical_review_candidates import OUTPUT_PATH as CANDIDATE_PATH
from scripts.prepare_competition_scope import SELECTION_PATH, prepare_scope

DATA_ROOT = PROJECT_ROOT / "backend/data/real_pilot"
PROPOSAL_PATH = DATA_ROOT / "review_supplements_v2.json"
AI_PATH = DATA_ROOT / "ai-assisted-review-overrides.json"


def _save_preserving(path: Path, payload: dict[str, Any]) -> None:
    if path.exists():
        if _read_json_object(path) != payload:
            raise ConversionError("existing revision differs; use a new revision identifier")
        return
    _write_json_atomic(path, payload)


def prepare_revision(
    *,
    proposal_path: Path = PROPOSAL_PATH,
    ai_path: Path = AI_PATH,
    candidate_path: Path = CANDIDATE_PATH,
    selection_path: Path = SELECTION_PATH,
    inventory_path: Path = INVENTORY_PATH,
    output_root: Path = DATA_ROOT / "review_revisions",
    project_root: Path = PROJECT_ROOT,
) -> dict[str, Any]:
    proposal, original, prior = (
        _read_json_object(path) for path in (proposal_path, candidate_path, ai_path)
    )
    base_hash = _sha256(candidate_path)
    source_id = original.get("source_id")
    if (
        proposal.get("dataset_kind") != "ai_supplemental_region_proposals"
        or proposal.get("verification_state") != "inferred"
        or proposal.get("requires_human_confirmation") is not True
        or proposal.get("source_candidate_sha256") != base_hash
        or proposal.get("source_id") != source_id
        or original.get("dataset_kind") != "real_pilot_model_assisted_review_candidates"
        or original.get("evaluation_status") != "not_evaluated"
        or prior.get("dataset_kind") != "ai_assisted_review_overrides"
        or prior.get("review_origin") != "ai_assisted"
        or prior.get("source_id") != source_id
        or prior.get("source_candidate_sha256") != base_hash
        or prior.get("input_hashes") != original.get("input_hashes")
    ):
        raise ConversionError(
            "revision inputs must match the original inferred candidate and AI review"
        )
    version = proposal.get("revision_id")
    if not isinstance(version, str) or not re.fullmatch(r"[a-z][a-z0-9-]{1,48}", version):
        raise ConversionError("invalid revision identifier")
    if project_root.resolve() not in output_root.resolve().parents:
        raise ConversionError("revision output must stay inside the project")

    revised = copy.deepcopy(original)
    inventory = _read_json_object(inventory_path)
    scans = {p["page_id"]: p for p in inventory["pages"]}
    pages = {p["page_id"]: p for p in revised["pages"]}
    items: dict[str, dict[str, Any]] = {}
    kinds: dict[str, str] = {}
    for page in pages.values():
        for box in page["boxes"]:
            items[box["box_id"]], kinds[box["box_id"]] = box, "box"
        for figure in page.get("figures", []):
            items[figure["figure_id"]], kinds[figure["figure_id"]] = figure, "figure"
            if figure.get("caption_box_id") is None and figure.get("candidate_title_bbox"):
                items[figure["figure_id"] + "-title"] = figure
                kinds[figure["figure_id"] + "-title"] = "caption"
    records = prior.get("records")
    if not isinstance(records, list):
        raise ConversionError("AI review records must be an array")
    migrated: dict[str, dict[str, Any]] = {}
    for record in records:
        if not isinstance(record, dict):
            raise ConversionError("AI review record must be an object")
        item_id = record.get("box_or_figure_id")
        if (
            item_id not in items
            or item_id in migrated
            or record.get("page_id") not in pages
            or not item_id.startswith(record["page_id"] + "-")
            or record.get("kind") != kinds[item_id]
            or record.get("review_origin") != "ai_assisted"
            or record.get("verification_state") != "inferred"
            or record.get("evidence") != "scan_level_ai_review"
            or record.get("requires_human_confirmation") is not True
        ):
            raise ConversionError("only matching AI suggestions can be migrated")
        _bbox(record)
        migrated[item_id] = copy.deepcopy(record)

    additions = proposal.get("regions")
    if not isinstance(additions, list) or not additions:
        raise ConversionError("revision requires supplemental regions")
    ordered = {}
    for page_id, page in pages.items():
        prior_orders = {
            box["box_id"]: migrated.get(box["box_id"], {}).get(
                "reading_order", box["reading_order"]
            )
            for box in page["boxes"]
        }
        if sorted(prior_orders.values()) != list(range(1, len(prior_orders) + 1)):
            raise ConversionError("prior AI reading order is not a complete permutation")
        ordered[page_id] = sorted(page["boxes"], key=lambda box: prior_orders[box["box_id"]])
    added_ids = []
    for addition in additions:
        page_id, item_id = addition.get("page_id"), addition.get("box_id")
        if (
            page_id not in pages
            or not isinstance(item_id, str)
            or not re.fullmatch(re.escape(page_id) + r"-b\d{3}", item_id)
            or item_id in items
            or addition.get("category") not in {"text", "annotation", "unknown"}
            or not isinstance(addition.get("role"), str)
            or not isinstance(addition.get("note"), str)
            or not addition["note"].strip()
        ):
            raise ConversionError("invalid or duplicate supplemental region")
        bbox = _bbox(addition)
        page = pages[page_id]
        scan = scans[page_id]
        x, y = bbox["x"] * scan["width"], bbox["y"] * scan["height"]
        w, h = bbox["width"] * scan["width"], bbox["height"] * scan["height"]
        box = {
            "box_id": item_id,
            "original_box_index": None,
            "origin": "ai_supplemental_region",
            "raw_text": None,
            "bbox": bbox,
            "polygon": [[x, y], [x + w, y], [x + w, y + h], [x, y + h]],
            "category_candidate": addition["category"],
            "role_candidate": addition["role"],
            "category_confidence": 0.5,
            "server_ocr": None,
            "reference_candidate": None,
            "normalized_candidate": None,
            "verification_state": "inferred",
            "needs_review": True,
        }
        after = addition.get("insert_after")
        anchors = [i for i, old in enumerate(ordered[page_id]) if old["box_id"] == after]
        if len(anchors) != 1:
            raise ConversionError("supplement reading-order anchor is missing")
        ordered[page_id].insert(anchors[0] + 1, box)
        page["boxes"].append(box)
        items[item_id], kinds[item_id] = box, "box"
        added_ids.append(item_id)
        migrated[item_id] = {
            "box_or_figure_id": item_id,
            "page_id": page_id,
            "kind": "box",
            "category": addition["category"],
            "role": addition["role"],
            "bbox": bbox,
            "corrected_text": None,
            "review_note": addition["note"],
            "reviewer": "Codex AI 辅助复核",
            "confirmed": False,
            "reviewed_at": None,
            "review_origin": "ai_assisted",
            "verification_state": "inferred",
            "evidence": "scan_level_ai_review",
            "requires_human_confirmation": True,
            "raw_text": None,
        }
    changed_orders = []
    for page_id, boxes in ordered.items():
        for order, box in enumerate(boxes, 1):
            box["reading_order"] = order
            decision = migrated.get(box["box_id"])
            if decision:
                if box["box_id"] not in added_ids:
                    decision["previous_ai_review"] = copy.deepcopy(decision)
                    if decision["reading_order"] != order:
                        changed_orders.append(box["box_id"])
                        decision["confirmed"], decision["reviewed_at"] = False, None
                decision["reading_order"] = order
                decision["original_reading_order"] = order
                decision["original_bbox"] = box["bbox"]
        pages[page_id]["boxes"] = boxes
    for item_id, decision in migrated.items():
        field = "title_ai_review_hint" if kinds[item_id] == "caption" else "ai_review_hint"
        items[item_id][field] = decision
    revised["revision"] = {
        "revision_id": version,
        "base_candidate_sha256": base_hash,
        "prior_ai_review_sha256": _sha256(ai_path),
        "proposal_sha256": _sha256(proposal_path),
        "selection_sha256": _sha256(selection_path),
        "review_template_sha256": _sha256(TEMPLATE_PATH),
        "added_ids": added_ids,
        "reading_order_recheck_ids": changed_orders,
        "requires_human_confirmation": True,
    }
    revised["ai_review_seed"] = list(migrated.values())
    revised.setdefault("statistics", {})["supplemental_region_candidates"] = len(added_ids)
    candidate_bytes = (json.dumps(revised, ensure_ascii=False, indent=2) + "\n").encode("utf-8")
    candidate_hash = hashlib.sha256(candidate_bytes).hexdigest()
    directory = output_root / f"{version}-{candidate_hash[:12]}"
    directory.mkdir(parents=True, exist_ok=True)
    new_candidate = directory / "annotations.candidates.json"
    _save_preserving(new_candidate, revised)
    scope = prepare_scope(
        selection_path=selection_path,
        candidate_path=new_candidate,
        inventory_path=inventory_path,
        project_root=project_root,
        output_path=directory / "competition_scope.json",
    )
    migrated_export = {
        **prior,
        "source_candidate_sha256": candidate_hash,
        "records": list(migrated.values()),
        "page_reviews": [],
        "page_inventory_reviews": [],
        "migration": revised["revision"],
    }
    _save_preserving(directory / "ai-review-seed.json", migrated_export)
    for origin, suffix in (("human", ""), ("ai_assisted", ".ai")):
        html = directory / f"model_review_queue{suffix}.html"
        manifest = directory / f"model_review_queue{suffix}.json"
        if not html.exists() or not manifest.exists():
            build_review_queue(
                candidate_path=new_candidate,
                output_path=html,
                manifest_path=manifest,
                asset_dir=directory / "model_review_assets",
                project_root=project_root,
                scope_path=directory / "competition_scope.json",
                review_origin=origin,
            )
    report = {
        "dataset_kind": "historical_review_revision_report",
        "revision_path": str(directory),
        "source_candidate_sha256": candidate_hash,
        "migrated_prior_suggestions": len(records),
        "added_regions": len(added_ids),
        "reading_order_rechecks": len(changed_orders),
        "scope_statistics": scope["statistics"],
        "evaluation_status": "not_evaluated",
        "human_truth_ready": False,
    }
    _save_preserving(directory / "revision_report.json", report)
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--proposal", type=Path, default=PROPOSAL_PATH)
    args = parser.parse_args()
    try:
        report = prepare_revision(proposal_path=args.proposal)
    except (ConversionError, OSError, KeyError, TypeError) as exc:
        parser.error(str(exc))
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
