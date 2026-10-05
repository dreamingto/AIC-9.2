"""Prepare hash-bound AI evidence drafts without creating human truth or qrels."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, ValidationError

from scripts.annotation_errors import ConversionError
from scripts.apply_historical_review_overrides import _bbox
from scripts.convert_ppocrlabel_annotations import (
    INVENTORY_PATH,
    PROJECT_ROOT,
    _read_json_object,
    _sha256,
    _write_json_atomic,
)

DATA_ROOT = PROJECT_ROOT / "backend/data/real_pilot"
LINKS_PATH = DATA_ROOT / "competition_evidence_links.json"
PIPELINE_VERSION = "competition-ai-evidence-drafts-v1"


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class Support(StrictModel):
    item_id: str
    quote: str = Field(min_length=1, max_length=200)


class FunctionalDraft(StrictModel):
    slot: Literal["input", "operation", "mechanism", "output"]
    concept: str = Field(min_length=1, max_length=100)
    rationale: str = Field(min_length=1, max_length=1000)
    supports: list[Support] = Field(min_length=1)


class ContextLink(StrictModel):
    item_ids: list[str] = Field(min_length=1)
    rationale: str = Field(min_length=1, max_length=1000)


class FigureLink(StrictModel):
    figure_id: str
    title_id: str
    label_ids: list[str]
    contexts: list[ContextLink]
    functional_drafts: list[FunctionalDraft]
    unresolved: list[str]


class CaseDraft(StrictModel):
    case_id: str
    name: str
    figure_ids: list[str] = Field(min_length=1)
    aim: str


class LinkPlan(StrictModel):
    schema_version: Literal["1.0"]
    dataset_kind: Literal["ai_competition_evidence_link_plan"]
    source_id: str
    source_candidate_sha256: str = Field(pattern=r"^[a-f0-9]{64}$")
    review_filename: str
    figures: list[FigureLink] = Field(min_length=1)
    cases: list[CaseDraft]


def _inside(path: Path, root: Path) -> Path:
    resolved = path.resolve()
    if root.resolve() not in resolved.parents:
        raise ConversionError("evidence input/output path escapes the project")
    return resolved


def active_revision(project_root: Path = PROJECT_ROOT) -> Path:
    root = project_root / "backend/data/real_pilot/review_revisions"
    pointer = _read_json_object(root / "active_revision.json")
    name = pointer.get("revision_directory")
    if not isinstance(name, str) or not re.fullmatch(r"[a-z0-9-]+", name):
        raise ConversionError("invalid active review revision")
    revision = _inside(root / name, project_root)
    if _sha256(revision / "annotations.candidates.json") != pointer.get("source_candidate_sha256"):
        raise ConversionError("active revision candidate hash mismatch")
    return revision


def _items(candidate: dict[str, Any]) -> dict[str, dict[str, Any]]:
    result: dict[str, dict[str, Any]] = {}

    def add(item_id: str, item: dict[str, Any]) -> None:
        if item_id in result or item.get("verification_state") != "inferred":
            raise ConversionError("duplicate or non-inferred candidate item")
        result[item_id] = item

    for page in candidate["pages"]:
        for box in page["boxes"]:
            add(box["box_id"], {**box, "page_id": page["page_id"], "kind": "box"})
        for figure in page.get("figures", []):
            add(figure["figure_id"], {**figure, "page_id": page["page_id"], "kind": "figure"})
            if figure.get("caption_box_id") is None and figure.get("candidate_title_bbox"):
                add(
                    figure["figure_id"] + "-title",
                    {
                        "page_id": page["page_id"],
                        "kind": "caption",
                        "bbox": figure["candidate_title_bbox"],
                        "verification_state": "inferred",
                        "raw_text": None,
                        "reading_order": None,
                    },
                )
    return result


def _validate_review(
    review: dict[str, Any],
    candidate: dict[str, Any],
    candidate_hash: str,
    items: dict[str, dict[str, Any]],
    scope: dict[str, Any],
) -> dict[str, dict[str, Any]]:
    if (
        review.get("dataset_kind") != "ai_assisted_review_overrides"
        or review.get("review_origin") != "ai_assisted"
        or review.get("evaluation_status") != "not_evaluated"
        or review.get("source_candidate_sha256") != candidate_hash
        or review.get("source_id") != candidate["source_id"]
        or review.get("input_hashes") != candidate["input_hashes"]
    ):
        raise ConversionError("AI review origin or input hashes mismatch")
    required: set[str] = set()
    for page in scope["pages"]:
        for field in ("box_ids", "figure_ids", "missing_caption_ids"):
            required.update(page[field])
    decisions: dict[str, dict[str, Any]] = {}
    for record in review["records"]:
        item_id = record.get("box_or_figure_id")
        if item_id not in items or item_id in decisions:
            raise ConversionError("AI review has an unknown or duplicate item")
        original = items[item_id]
        if (
            record.get("page_id") != original["page_id"]
            or record.get("kind") != original["kind"]
            or record.get("review_origin") != "ai_assisted"
            or record.get("verification_state") != "inferred"
            or record.get("requires_human_confirmation") is not True
            or record.get("evidence") != "scan_level_ai_review"
            or record.get("confirmed") is not True
            or not record.get("reviewer")
            or not record.get("review_note")
        ):
            raise ConversionError("record must be an explicitly checked AI scan suggestion")
        try:
            timestamp = datetime.fromisoformat(record["reviewed_at"])
        except (TypeError, ValueError, KeyError) as exc:
            raise ConversionError("AI review requires a dated scan check") from exc
        if timestamp.tzinfo is None:
            raise ConversionError("AI review date requires a timezone")
        if (
            record.get("raw_text") != original.get("raw_text")
            or record.get("original_bbox") != original["bbox"]
            or record.get("original_reading_order") != original.get("reading_order")
        ):
            raise ConversionError("AI review must preserve original OCR and geometry")
        _bbox(record)
        if record.get("category") not in {"text", "caption", "annotation", "figure", "unknown"}:
            raise ConversionError("unsupported AI review category")
        text = record.get("corrected_text")
        if text is not None and (not isinstance(text, str) or not text.strip()):
            raise ConversionError("AI transcription must be null or non-empty text")
        decisions[item_id] = record
    if not required.issubset(decisions) or not required.issubset(items):
        raise ConversionError("all core items must have actual AI scan checks")
    for page in scope["pages"]:
        orders = [decisions[item_id]["reading_order"] for item_id in page["box_ids"]]
        if any(type(order) is not int for order in orders) or sorted(orders) != list(
            range(1, len(orders) + 1)
        ):
            raise ConversionError("AI reading order must be a complete permutation")
    return decisions


def _save_preserving(path: Path, payload: dict[str, Any]) -> None:
    if path.exists():
        if _read_json_object(path) != payload:
            raise ConversionError("existing evidence artifact differs; refusing overwrite")
    else:
        _write_json_atomic(path, payload)


def _worksheet(payload: dict[str, Any]) -> str:
    lines = [
        "# 机图索隐：比赛证据工作表",
        "",
        "这是逐项扫描复核后的 AI 证据草稿，不是独立人工真值、数据库导入 manifest 或相关性标签。",
        "功能概念与跨页归属均为 Inferred；CER/WER、图题召回和检索指标仍为 not_evaluated。",
        "",
        f"输入指纹：`{payload['artifact_fingerprint']}`",
        "",
    ]
    for figure in payload["figures"]:
        lines += [f"## {figure['title']['text_hint']}", "", f"图 ID：`{figure['figure_id']}`。"]
        lines += [
            f"PDF 第 {figure['pdf_page']} 页，来源：{figure['provenance']['source_name']}。",
            "",
        ]
        lines += [
            f"[原页扫描]({figure['scan_path']})",
            "",
            f"图题定位：`{figure['title']['item_id']}`，状态 Inferred。",
            "",
        ]
        labels = [f"{r['text_hint'] or '留空'}（{r['item_id']}）" for r in figure["labels"]]
        lines += ["部件/图内说明：" + ("；".join(labels) or "无可靠已转录标签。"), ""]
        for context in figure["contexts"]:
            lines += [f"正文归属依据：{context['rationale']}", ""]
            for evidence in context["evidence"]:
                lines += [f"- `{evidence['item_id']}`：{evidence['text_hint']}"]
            lines.append("")
        if not figure["contexts"]:
            lines += ["正文归属：暂无核心范围内可可靠归属的正文，不自动附加同页全文。", ""]
        for assertion in figure["functional_drafts"]:
            quotes = "；".join(f"{s['item_id']}「{s['quote']}」" for s in assertion["supports"])
            lines += [
                f"- 功能槽 `{assertion['slot']}`：{assertion['concept']}。{assertion['rationale']}",
                f"  支持片段：{quotes}；置信度未标定，待确认。",
            ]
        lines.append("")
        lines += ["待裁决：" + "；".join(figure["unresolved"]), ""]
    lines += ["## 两个演示案例草稿", ""]
    for case in payload["cases"]:
        lines += [f"- {case['name']}：{case['aim']}（关联类别未标注）。"]
    lines += [
        "",
        "## 下一步",
        "",
        "优先裁决留空与未知项，独立确认完整清单，再冻结 OCR 诊断集。",
        "候选查询可以用于演示准备，relevance_grade 全部为 null，不能作为检索评测 qrels。",
        "",
    ]
    return "\n".join(lines)


def prepare_evidence_drafts(
    *,
    revision_dir: Path,
    links_path: Path = LINKS_PATH,
    inventory_path: Path = INVENTORY_PATH,
    project_root: Path = PROJECT_ROOT,
) -> tuple[dict[str, Any], Path]:
    revision_dir = _inside(revision_dir, project_root)
    candidate_path = revision_dir / "annotations.candidates.json"
    scope_path = revision_dir / "competition_scope.json"
    candidate, scope, inventory = (
        _read_json_object(path) for path in (candidate_path, scope_path, inventory_path)
    )
    try:
        plan = LinkPlan.model_validate(_read_json_object(links_path))
    except ValidationError as exc:
        raise ConversionError(f"invalid evidence link plan: {exc}") from exc
    candidate_hash = _sha256(candidate_path)
    if (
        candidate.get("dataset_kind") != "real_pilot_model_assisted_review_candidates"
        or candidate.get("evaluation_status") != "not_evaluated"
        or scope.get("dataset_kind") != "competition_evaluation_scope"
        or scope.get("evaluation_status") != "not_evaluated"
        or scope.get("source_id") != candidate["source_id"]
        or scope.get("source_candidate_sha256") != candidate_hash
        or plan.source_candidate_sha256 != candidate_hash
        or plan.source_id != candidate["source_id"]
        or candidate["input_hashes"].get("inventory_sha256") != _sha256(inventory_path)
        or inventory.get("dataset_kind") != "real_pilot_page_inventory"
    ):
        raise ConversionError("candidate, scope, link plan, or inventory hash mismatch")
    if not re.fullmatch(r"[a-z0-9.-]+\.json", plan.review_filename):
        raise ConversionError("review_filename must be a controlled basename")
    review_path = _inside(revision_dir / plan.review_filename, project_root)
    review = _read_json_object(review_path)
    items = _items(candidate)
    decisions = _validate_review(review, candidate, candidate_hash, items, scope)
    scope_pages = {p["page_id"]: p for p in scope["pages"]}
    candidate_pages = {p["page_id"]: p for p in candidate["pages"]}
    scans = {p["page_id"]: p for p in inventory["pages"]}
    if len(scope_pages) != len(scope["pages"]):
        raise ConversionError("duplicate core scope page")
    for page_id, page in scope_pages.items():
        scan = scans[page_id]
        original_page = candidate_pages[page_id]
        for field, expected in (
            ("box_ids", [b["box_id"] for b in original_page["boxes"]]),
            ("figure_ids", [f["figure_id"] for f in original_page.get("figures", [])]),
            (
                "missing_caption_ids",
                [
                    f["figure_id"] + "-title"
                    for f in original_page.get("figures", [])
                    if f.get("caption_box_id") is None and f.get("candidate_title_bbox")
                ],
            ),
        ):
            if len(page[field]) != len(set(page[field])) or set(page[field]) != set(expected):
                raise ConversionError("scope must preserve the complete candidate page inventory")
        image_path = _inside(project_root / scan["image_path"], project_root)
        if (
            scan["sha256"] != page["image_sha256"]
            or original_page["image_sha256"] != scan["sha256"]
            or scan["image_path"] != page["image_path"]
            or original_page["image_path"] != scan["image_path"]
            or _sha256(image_path) != scan["sha256"]
            or scan["source_id"] != candidate["source_id"]
            or scan["provenance"]["pdf_sha256"] != page["pdf_sha256"]
        ):
            raise ConversionError("scan provenance or image hash mismatch")
        filename = scan["provenance"]["pdf_filename"]
        if (
            not isinstance(filename, str)
            or not re.fullmatch(r"[a-zA-Z0-9._-]+\.pdf", filename)
            or filename != page["pdf_filename"]
        ):
            raise ConversionError("invalid source PDF filename")
        pdf_path = _inside(
            project_root / "backend/data/assets/real_pilot_v1" / filename, project_root
        )
        if _sha256(pdf_path) != page["pdf_sha256"]:
            raise ConversionError("source PDF hash mismatch")
    expected_figures = {item_id for p in scope["pages"] for item_id in p["figure_ids"]}
    linked_figures = [f.figure_id for f in plan.figures]
    if len(set(linked_figures)) != len(linked_figures) or set(linked_figures) != expected_figures:
        raise ConversionError("link plan must cover each core figure exactly once")

    def evidence(item_id: str) -> dict[str, Any]:
        if item_id not in decisions or decisions[item_id]["page_id"] not in scope_pages:
            raise ConversionError("evidence pointer must reference a checked core item")
        record = decisions[item_id]
        scan = scans[record["page_id"]]
        return {
            "item_id": item_id,
            "page_id": record["page_id"],
            "bbox": record["bbox"],
            "raw_text": record["raw_text"],
            "text_hint": record["corrected_text"],
            "category": record["category"],
            "role": record["role"],
            "reading_order_hint": record["reading_order"],
            "review_note": record["review_note"],
            "state": "Inferred",
            "review_origin": "ai_assisted",
            "requires_human_confirmation": True,
            "scan_sha256": scan["sha256"],
        }

    figures = []
    for link in plan.figures:
        figure_record = decisions[link.figure_id]
        figure_page = figure_record["page_id"]
        original = items[link.figure_id]
        title = evidence(link.title_id)
        expected_title = original.get("caption_box_id") or (link.figure_id + "-title")
        if (
            link.title_id != expected_title
            or title["page_id"] != figure_page
            or title["category"] != "caption"
            or title["role"] != "figure_title"
            or not title["text_hint"]
            or figure_record["category"] != "figure"
        ):
            raise ConversionError("figure title must use its checked local caption pointer")
        attached_ids = [link.title_id, *link.label_ids]
        labels = [evidence(item_id) for item_id in link.label_ids]
        if any(
            r["page_id"] != figure_page
            or r["category"] != "caption"
            or r["role"] not in {"component_label", "figure_annotation"}
            for r in labels
        ):
            raise ConversionError("labels must be captions on the figure's page")
        contexts = []
        for context in link.contexts:
            attached_ids.extend(context.item_ids)
            records = [evidence(item_id) for item_id in context.item_ids]
            if any(
                r["category"] != "text"
                or r["role"] not in {"body", "body_text"}
                or not r["text_hint"]
                for r in records
            ):
                raise ConversionError("context must reference explicit non-empty body items")
            contexts.append(
                {
                    "rationale": context.rationale,
                    "evidence": records,
                    "state": "Inferred",
                    "requires_human_confirmation": True,
                }
            )
        if len(set(attached_ids)) != len(attached_ids):
            raise ConversionError("duplicate evidence attachment on a figure")
        assertions = []
        for assertion in link.functional_drafts:
            for support in assertion.supports:
                if support.item_id not in attached_ids:
                    raise ConversionError("function support is not attached to this figure")
                hint = decisions[support.item_id]["corrected_text"]
                if not hint or support.quote not in hint:
                    raise ConversionError(
                        "function quote is absent from the actual AI transcription"
                    )
            assertions.append(
                {
                    **assertion.model_dump(),
                    "state": "Inferred",
                    "confidence": None,
                    "requires_human_confirmation": True,
                    "review_origin": "ai_assisted",
                }
            )
        scan = scans[figure_page]
        figures.append(
            {
                "figure_id": link.figure_id,
                "page_id": figure_page,
                "pdf_page": scan["pdf_page"],
                "bbox": figure_record["bbox"],
                "scan_path": str((project_root / scan["image_path"]).resolve()).replace("\\", "/"),
                "provenance": scan["provenance"],
                "state": "Inferred",
                "review_origin": "ai_assisted",
                "requires_human_confirmation": True,
                "title": title,
                "labels": labels,
                "contexts": contexts,
                "functional_drafts": assertions,
                "unresolved": link.unresolved,
            }
        )
    for case in plan.cases:
        if not set(case.figure_ids).issubset(expected_figures):
            raise ConversionError("case points to a figure outside the core scope")
    hashes = {
        "candidate": candidate_hash,
        "scope": _sha256(scope_path),
        "review": _sha256(review_path),
        "link_plan": _sha256(links_path),
        "inventory": _sha256(inventory_path),
    }
    fingerprint = hashlib.sha256(
        json.dumps({"pipeline": PIPELINE_VERSION, "inputs": hashes}, sort_keys=True).encode()
    ).hexdigest()
    core_ids = {
        item_id
        for page in scope["pages"]
        for field in ("box_ids", "figure_ids", "missing_caption_ids")
        for item_id in page[field]
    }
    core_records = [decisions[item_id] for item_id in sorted(core_ids)]
    unresolved_text = [
        r["box_or_figure_id"]
        for r in core_records
        if r["category"] in {"text", "annotation", "caption"} and r["corrected_text"] is None
    ]
    payload = {
        "schema_version": "1.0",
        "dataset_kind": "ai_competition_evidence_drafts",
        "pipeline_version": PIPELINE_VERSION,
        "source_id": plan.source_id,
        "review_origin": "ai_assisted",
        "verification_state": "inferred",
        "requires_human_confirmation": True,
        "evaluation_status": "not_evaluated",
        "artifact_fingerprint": fingerprint,
        "input_hashes": hashes,
        "statistics": {
            "core_pages": len(scope_pages),
            "core_items": len(core_records),
            "ai_checked_items": len(core_records),
            "null_text_items": len(unresolved_text),
            "unknown_items": sum(r["category"] == "unknown" for r in core_records),
            "human_truth_pages": 0,
            "figures": len(figures),
            "functional_drafts": sum(len(f["functional_drafts"]) for f in figures),
            "category_counts": dict(Counter(r["category"] for r in core_records)),
        },
        "null_text_item_ids": unresolved_text,
        "unknown_item_ids": [
            r["box_or_figure_id"] for r in core_records if r["category"] == "unknown"
        ],
        "figures": figures,
        "cases": [
            {**c.model_dump(), "state": "Inferred", "relevance_labels": None} for c in plan.cases
        ],
        "query_drafts": [
            {
                "query_id": f"title-{index:02d}",
                "query_type": "text",
                "query": f["title"]["text_hint"],
                "review_origin": "ai_assisted",
                "comparison_figure_ids": [f["figure_id"]],
                "relevance_grade": None,
            }
            for index, f in enumerate(figures, 1)
        ],
        "metrics": {
            "cer": None,
            "wer": None,
            "caption_recall": None,
            "recall_at_k": None,
            "mrr": None,
            "ndcg": None,
        },
        "limitations": [
            "AI scan checks are not independent human truth or historical verification.",
            "Cross-page context and functional concepts are explicit AI drafts, not qrels.",
            "Missing body context is kept empty; same-page text is never attached wholesale.",
            "This artifact is not an ingestion manifest and cannot unlock human evaluation gates.",
        ],
    }
    output = revision_dir / f"evidence-drafts-{fingerprint[:16]}"
    _save_preserving(output / "evidence-drafts.json", payload)
    worksheet = output / "证据工作表.md"
    text = _worksheet(payload)
    if worksheet.exists() and worksheet.read_text(encoding="utf-8") != text:
        raise ConversionError("existing worksheet differs; refusing overwrite")
    if not worksheet.exists():
        worksheet.write_text(text, encoding="utf-8", newline="\n")
    return payload, output


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--revision", type=Path)
    parser.add_argument("--links", type=Path, default=LINKS_PATH)
    args = parser.parse_args()
    try:
        payload, output = prepare_evidence_drafts(
            revision_dir=args.revision or active_revision(),
            links_path=args.links,
        )
    except (ConversionError, OSError, KeyError, TypeError) as exc:
        parser.error(str(exc))
    print(json.dumps({"output": str(output), **payload["statistics"]}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
