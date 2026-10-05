"""Bind AI function drafts to immutable scans and attributed text, never to qrels."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from app.ingestion.contracts import AIRealManifest
from app.retrieval.experiments.contracts import DraftSupport, EvidencePlan
from app.services.ingestion_service import stable_id


def canonical_hash(value: Any) -> str:
    return hashlib.sha256(
        json.dumps(value, ensure_ascii=False, sort_keys=True, allow_nan=False).encode("utf-8")
    ).hexdigest()


def file_hash(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def json_bytes(value: Any) -> bytes:
    return (json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + "\n").encode()


def immutable_write(path: Path, content: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        if path.read_bytes() != content:
            raise ValueError(f"refuse to overwrite existing artifact: {path.name}")
        return
    with path.open("xb") as stream:
        stream.write(content)


def resolve_support(
    support: DraftSupport,
    owner_key: str,
    manifest: AIRealManifest,
) -> dict[str, Any]:
    owner = next(f for f in manifest.figures if f.figure_id == owner_key)
    asset = next(a for a in manifest.assets if a.asset_id == owner.asset_id)
    page = next(p for p in manifest.pages if p.page_id == owner.page_id)
    source = next(s for s in manifest.sources if s.source_id == page.source_id)
    bbox = owner.bbox
    content = None
    if support.kind == "scan_region":
        region = next((r for r in manifest.regions if r.region_id == support.reference_id), None)
        if region is None or region.figure_id != owner_key:
            raise ValueError("draft region reference is missing or belongs to another figure")
        bbox = region.bbox
    else:
        chunk = next((c for c in manifest.text_chunks if c.text_id == support.reference_id), None)
        if chunk is None or chunk.figure_id != owner_key or chunk.ai_trace is None:
            raise ValueError("draft text reference is missing or belongs to another figure")
        if chunk.ai_trace.origin != support.kind:
            raise ValueError("draft must not misattribute AI description/transcription/raw OCR")
        if support.quote is None or support.quote not in chunk.content:
            raise ValueError("draft quote is not an exact substring of its attributed source")
        bbox = chunk.ai_trace.bbox
        content = chunk.content
    if bbox is None:
        raise ValueError("draft requires a scan location")
    return {
        **support.model_dump(mode="json"),
        "content": content,
        "support_state": "Observed" if support.kind == "scan_region" else "Inferred",
        "ancient_prose_verified": False,
        "page_key": page.page_id,
        "page_or_folio": page.page_or_folio,
        "bbox": bbox.model_dump(),
        "asset_sha256": asset.sha256,
        "asset_relative_path": asset.relative_path,
        "asset_url": f"/api/v1/assets/{stable_id('asset', asset.asset_id)}",
        "source_url": source.source_url,
        "source_name": source.source_name,
        "book_title": source.book_title,
        "edition": source.edition,
        "source_category": source.source_category,
        "original_pdf_sha256": source.original_sha256,
        "license_status": str(source.license_status),
        "allow_redistribution": source.allow_redistribution,
    }


def bind_drafts(plan: EvidencePlan, manifest: AIRealManifest) -> dict[str, Any]:
    keys = {f.figure_id for f in manifest.figures}
    if not {f.figure_key for f in plan.figures}.issubset(keys):
        raise ValueError("draft figure is outside the locked corpus")
    figures: list[dict[str, Any]] = []
    for draft in plan.figures:
        owner = next(f for f in manifest.figures if f.figure_id == draft.figure_key)
        value = draft.model_dump(mode="json")
        value.update(figure_id=str(stable_id("figure", draft.figure_key)), title=owner.title)
        for group in ("functions", "relations"):
            for item in value[group]:
                item["supports"] = [
                    resolve_support(DraftSupport.model_validate(s), draft.figure_key, manifest)
                    for s in item["supports"]
                ]
        figures.append(value)
    return {
        "schema_version": "1.0",
        "artifact_kind": "ai_function_evidence_drafts",
        "plan_id": plan.plan_id,
        "review_origin": "ai_assisted",
        "evaluation_status": "not_evaluated",
        "independent_ground_truth": False,
        "confidence_policy": "uncalibrated_null",
        "disclaimer": plan.disclaimer,
        "figures": figures,
        "counts": {
            "figures": len(figures),
            "known_functions": sum(
                f["concept"] != "unknown" for d in figures for f in d["functions"]
            ),
            "unknown_functions": sum(
                f["concept"] == "unknown" for d in figures for f in d["functions"]
            ),
            "relations": sum(len(d["relations"]) for d in figures),
            "graph_rerank_eligible": 0,
        },
    }


def inside(inner: dict[str, float], outer: dict[str, float]) -> bool:
    return (
        inner["x"] >= outer["x"] - 1e-9
        and inner["y"] >= outer["y"] - 1e-9
        and inner["x"] + inner["width"] <= outer["x"] + outer["width"] + 1e-9
        and inner["y"] + inner["height"] <= outer["y"] + outer["height"] + 1e-9
    )


def scoped_functions(
    draft: dict[str, Any] | None,
    bbox: dict[str, float] | None = None,
) -> list[dict[str, Any]]:
    if draft is None:
        return []
    # A region gets a claim only if ALL its spatial supports lie inside the crop.
    # Whole-figure/image captions cannot smuggle out-of-crop function into a query.
    return [
        f
        for f in draft["functions"]
        if f["concept"] != "unknown"
        and (bbox is None or all(inside(s["bbox"], bbox) for s in f["supports"]))
    ]


def draft_markdown(artifact: dict[str, Any]) -> str:
    lines = [
        "# 国内古籍案例功能证据草稿",
        "",
        artifact["disclaimer"],
        "",
        "全部功能与关系保持 Inferred，confidence=null；不是人工真值，不写入业务标签。",
        "图像位置可见，动态功能与因果仍是AI推断。关系均不参与高置信度图重排。",
        "",
    ]
    for draft in artifact["figures"]:
        lines.extend([f"## {draft['title']}", "", f"图ID：`{draft['figure_id']}`", ""])
        for f in draft["functions"]:
            lines.extend(
                [
                    f"- {f['slot']}：{f['label']}（{f['state']}，置信度未标定）",
                    f"  - 依据：{f['rationale']}",
                ]
            )
            for s in f["supports"]:
                lines.append(
                    f"  - {s['kind']} / `{s['reference_id']}` / {s['page_or_folio']} / "
                    f"bbox={json.dumps(s['bbox'], ensure_ascii=False)} / "
                    f"[扫描](http://localhost{s['asset_url']})；{s['note']}"
                )
                if s["quote"]:
                    lines.append(f"    - 引用（AI来源，非已核实古文）：{s['quote']}")
        lines.extend(["", "关系草稿（confidence=null，图评分不可用）：", ""])
        for relation in draft["relations"]:
            lines.append(
                f"- {relation['subject']} → {relation['predicate']} → {relation['object']}："
                f"{relation['rationale']}（支持指针见JSON）"
            )
        lines.extend(["", "未决项：", "", *[f"- {s}" for s in draft["unresolved"]], ""])
    lines.extend(["完整的扫描/PDF哈希、来源、许可与逐条支持指针见同目录JSON。", ""])
    return "\n".join(lines)
