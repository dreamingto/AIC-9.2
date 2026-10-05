"""Controlled rankings from actual PostgreSQL model vectors, with no database writes."""

from __future__ import annotations

import asyncio
import hashlib
import math
import time
from dataclasses import dataclass, replace
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings
from app.core.security import resolve_safe_path
from app.db.models import EmbeddingRecord, Figure
from app.domain.enums import SearchType
from app.ingestion.contracts import AIRealManifest
from app.retrieval.cfr.rule_based import DEFAULT_VOCABULARY, RuleBasedCFRProvider
from app.retrieval.evidence.spatial import scoped_region_context
from app.retrieval.experiments.contracts import FixedQuery, Method
from app.retrieval.experiments.evidence import canonical_hash, file_hash, inside, scoped_functions
from app.retrieval.rerank.scoring import (
    cosine_similarity,
    cosine_to_unit,
    evidence_coverage,
    score_candidate,
)
from app.schemas.common import BBox
from app.services.ingestion_service import stable_id
from app.services.search_service import QueryContext, SearchService

VERSION = "domestic-comparison-v2-spatial"
# This is an explicit engineering policy, NOT an estimated confidence/probability.
DRAFT_RELIABILITY = 0.5


def experiment_cfr() -> RuleBasedCFRProvider:
    vocabulary = {slot: dict(concepts) for slot, concepts in DEFAULT_VOCABULARY.items()}
    vocabulary["action"]["pounding"] = ("舂捣", "舂米", "舂击")
    vocabulary["action"]["grinding"] = ("磨粉", "碾磨", "研磨", "磨粮", "磨盘")
    vocabulary["action"]["weaving"] += ("织机", "织布")
    vocabulary["purpose"]["textile_production"] += ("织布", "织造")
    return RuleBasedCFRProvider(vocabulary)


def applicable(method: Method, query: FixedQuery) -> bool:
    return query.kind == "text" or method not in {"bm25", "bge"}


def validate_locked_figures(
    service: SearchService,
    manifest: AIRealManifest,
    figures: list[Figure],
) -> list[dict[str, Any]]:
    expected = {stable_id("figure", f.figure_id): f for f in manifest.figures}
    if {f.id for f in figures} != set(expected):
        raise ValueError("locked corpus is missing or contains extra figures")
    rows: list[dict[str, Any]] = []
    for figure in figures:
        spec = expected[figure.id]
        asset = next(a for a in manifest.assets if a.asset_id == spec.asset_id)
        page = next(p for p in manifest.pages if p.page_id == spec.page_id)
        source = next(s for s in manifest.sources if s.source_id == page.source_id)
        chunks = sorted(
            (c.text_id, c.kind.value, c.content, None, str(c.evidence_state))
            for c in manifest.text_chunks
            if c.figure_id == spec.figure_id
        )
        stored_chunks = sorted(
            (c.source_pointer, c.chunk_type, c.text, c.corrected_text, c.state)
            for c in figure.text_chunks
        )
        regions = sorted(
            (str(stable_id("region", r.region_id)), r.bbox.x, r.bbox.y, r.bbox.width, r.bbox.height)
            for r in manifest.regions
            if r.figure_id == spec.figure_id
        )
        stored_regions = sorted((str(r.id), r.x, r.y, r.width, r.height) for r in figure.regions)
        evidence_rows = sorted(
            (
                str(stable_id("evidence", e.evidence_id)),
                e.kind.value,
                str(e.state),
                e.source_ref,
                e.excerpt or f"{e.kind.value} evidence: {e.source_ref}",
            )
            for e in manifest.evidence
            if e.figure_id == spec.figure_id
        )
        stored_evidence = sorted(
            (str(e.id), e.evidence_type, e.status, e.pointer, e.content) for e in figure.evidences
        )
        if (
            figure.provenance.get("dataset_kind") != "ai_assisted_real_pilot"
            or figure.title != spec.title
            or figure.asset is None
            or figure.asset.sha256 != asset.sha256
            or figure.asset.relative_path != asset.relative_path
            or figure.asset.id != stable_id("asset", asset.asset_id)
            or figure.asset.allow_redistribution != source.allow_redistribution
            or figure.page_id != stable_id("page", page.page_id)
            or figure.page.edition.source_url != source.source_url
            or figure.page.edition.name != source.edition
            or figure.page.edition.book.title != source.book_title
            or figure.provenance.get("original_pdf_sha256") != source.original_sha256
            or stored_chunks != chunks
            or stored_regions != regions
            or stored_evidence != evidence_rows
            or figure.assertions
            or figure.relations
            or (figure.bbox_x, figure.bbox_y, figure.bbox_width, figure.bbox_height)
            != (spec.bbox.x, spec.bbox.y, spec.bbox.width, spec.bbox.height)
        ):
            raise ValueError("database corpus differs from locked manifest; comparison refused")
        path = resolve_safe_path(service.settings.asset_root, asset.relative_path)
        if file_hash(path) != asset.sha256:
            raise ValueError("scan hash changed")
        rows.append(
            {
                "figure_id": str(figure.id),
                "figure_key": spec.figure_id,
                "title": figure.title,
                "bbox": spec.bbox.model_dump(),
                "asset_sha256": asset.sha256,
                "chunks": chunks,
                "regions": regions,
                "provenance": figure.provenance,
                "evidence": sorted(
                    [
                        {
                            "id": str(e.id),
                            "status": e.status,
                            "content": e.content,
                            "pointer": e.pointer,
                        }
                        for e in figure.evidences
                    ],
                    key=lambda e: e["id"],
                ),
            }
        )
    return rows


async def corpus_snapshot(
    session: AsyncSession,
    service: SearchService,
    manifest: AIRealManifest,
    figures: list[Figure],
) -> tuple[dict[tuple[str, UUID, str], list[float]], dict[str, Any]]:
    rows = validate_locked_figures(service, manifest, figures)
    vectors = await service._embedding_map(session, figures)
    required = {
        ("figure", f.id, modality) for f in figures for modality in ("text", "image", "clip_text")
    } | {("region", r.id, "image") for f in figures for r in f.regions}
    if set(vectors) != required or any(
        len(v) != 512
        or any(not math.isfinite(n) for n in v)
        or not 0.98 <= sum(n * n for n in v) <= 1.02
        for v in vectors.values()
    ):
        raise ValueError("missing, stale, non-finite or incompatible neural vectors")
    vector_rows = [
        {"entity_type": k[0], "entity_id": str(k[1]), "modality": k[2], "vector": v}
        for k, v in sorted(vectors.items(), key=lambda pair: tuple(map(str, pair[0])))
    ]
    result = await session.execute(
        select(EmbeddingRecord).where(EmbeddingRecord.entity_id.in_([k[1] for k in required]))
    )
    compatible_models = {
        (r.provider, r.model, r.version, r.dimension, r.preprocessing_hash)
        for r in result.scalars()
        if (r.entity_type, r.entity_id, r.modality) in vectors and r.dimension == 512
    }
    snapshot = {
        "figures": sorted(rows, key=lambda r: r["figure_id"]),
        "figure_count": len(figures),
        "vector_count": len(vectors),
        "vector_sha256": canonical_hash(vector_rows),
        "model_spaces": sorted(compatible_models),
        "synthetic_figure_count": 0,
        "source": "PostgreSQL/pgvector",
    }
    snapshot["sha256"] = canonical_hash(snapshot)
    return vectors, snapshot


@dataclass
class Inputs:
    query: QueryContext
    bge_vector: list[float] | None
    visual_vector: list[float] | None
    clip_vector: list[float] | None
    bm25_scores: dict[str, float]
    bm25_raw: dict[str, float]
    draft_query_functions: list[dict[str, Any]]
    input_sha256: str | None


class ComparisonRunner:
    def __init__(
        self,
        settings: Settings,
        figures: list[Figure],
        vectors: dict[tuple[str, UUID, str], list[float]],
        drafts: dict[str, Any],
        keys: dict[str, UUID],
        service: SearchService | None = None,
    ) -> None:
        self.service = service or SearchService(settings)
        self.figures = figures
        self.keys = keys
        self.by_id = {f.id: f for f in figures}
        self.features = {f.id: self.service._candidate_features(f, vectors) for f in figures}
        self.drafts = {UUID(d["figure_id"]): d for d in drafts["figures"]}
        self.draft_cfr = experiment_cfr()

    def candidates(self, query: FixedQuery) -> list[Figure]:
        source_id = self.keys.get(query.source_figure_key or "")
        if query.source_figure_key and source_id is None:
            raise ValueError("visual query source is outside corpus")
        return [f for f in self.figures if f.id != source_id]

    async def inputs(self, query: FixedQuery, method: Method) -> Inputs:
        text = query.text
        bge = visual = clip = None
        image_bytes = None
        input_hash = None
        assertions: list[dict[str, Any]] = []
        claims: list[str] = []
        draft_functions: list[dict[str, Any]] = []
        if text:
            assertions = self.service._cfr_to_dicts(self.service.providers.cfr.extract(text))
            claims = self.service._claims_from_text(text, assertions)
            if method not in {"bm25", "chinese_clip"}:
                bge = list(
                    (
                        await asyncio.to_thread(
                            self.service.providers.text_embedding.encode_query, text
                        )
                    ).vector
                )
            if method not in {"bm25", "bge"}:
                provider = self.service.providers.clip_text
                if provider is None:
                    raise ValueError("comparison requires Chinese-CLIP text provider")
                clip = list((await asyncio.to_thread(provider.encode, text)).vector)
            draft_functions = self.service._cfr_to_dicts(self.draft_cfr.extract(text))
            # Rule confidence is not a calibrated probability either. Use the same
            # constant policy strength on query and candidate, independent of results.
            for item in draft_functions:
                item["confidence"] = 1.0
                item.pop("matched_terms", None)
        else:
            source = self.by_id[self.keys[str(query.source_figure_key)]]
            if source.asset is None:
                raise ValueError("query scan missing")
            content = resolve_safe_path(
                self.service.settings.asset_root, source.asset.relative_path
            ).read_bytes()
            if (
                source.bbox_x is None
                or source.bbox_y is None
                or source.bbox_width is None
                or source.bbox_height is None
            ):
                raise ValueError("query figure extent missing")
            box = query.bbox or BBox(
                x=source.bbox_x, y=source.bbox_y, width=source.bbox_width, height=source.bbox_height
            )
            extent = {
                "x": source.bbox_x,
                "y": source.bbox_y,
                "width": source.bbox_width,
                "height": source.bbox_height,
            }
            if not inside(box.model_dump(), extent):
                raise ValueError("fixed query crop escapes source figure")
            image_bytes = self.service._crop_image(content, box)
            input_hash = canonical_hash(
                {"crop_sha256": hashlib.sha256(image_bytes).hexdigest(), "bbox": box.model_dump()}
            )
            visual = list(
                (
                    await asyncio.to_thread(
                        self.service.providers.image_embedding.encode, image_bytes
                    )
                ).vector
            )
            if query.kind == "region":
                # Experimental overlay: only spatially contained draft supports.
                draft_functions = scoped_functions(self.drafts.get(source.id), box.model_dump())
                if method == "eafr_current":
                    scoped_text, assertions, _ = scoped_region_context(source, box.model_dump())
                    claims = self.service._claims_from_text(scoped_text, assertions)
        documents = {str(f.id): self.features[f.id]["text"] for f in self.candidates(query)}
        self.service.providers.bm25.fit(documents)
        raw = {
            hit.document_id: hit.score
            for hit in self.service.providers.bm25.search(
                text or "", top_k=max(1, len(documents))
            ).hits
        }
        maximum = max(raw.values(), default=0.0)
        normalized = {key: score / maximum for key, score in raw.items()} if maximum else {}
        context = QueryContext(
            SearchType(query.kind),
            text,
            image_bytes,
            assertions,
            [],
            claims,
            {"query_id": query.id},
        )
        return Inputs(context, bge, visual, clip, normalized, raw, draft_functions, input_hash)

    @staticmethod
    def function_similarity(
        query: list[dict[str, Any]],
        candidate: list[dict[str, Any]],
    ) -> float | None:
        a = {(f["slot"], f["concept"]) for f in query if f["concept"] != "unknown"}
        b = {(f["slot"], f["concept"]) for f in candidate if f["concept"] != "unknown"}
        return len(a & b) / len(a | b) if a and b else None

    @staticmethod
    def function_evidence_coverage(
        query: list[dict[str, Any]],
        candidate: list[dict[str, Any]],
    ) -> float | None:
        keys = {(f["slot"], f["concept"]) for f in query if f["concept"] != "unknown"}
        if not keys:
            return None
        supported = {(f["slot"], f["concept"]) for f in candidate if f["supports"]}
        # Only query/candidate claim matches count, never document length.
        return DRAFT_RELIABILITY * len(keys & supported) / len(keys)

    async def run(self, query: FixedQuery, method: Method, top_k: int) -> dict[str, Any]:
        if not applicable(method, query):
            return {
                "query_id": query.id,
                "method": method,
                "status": "not_applicable",
                "reason": "visual input has no text; no synthetic caption supplied",
            }
        started = time.perf_counter()
        inputs = await self.inputs(query, method)
        feature_ms = (time.perf_counter() - started) * 1000
        ranking_started = time.perf_counter()
        ranked: list[dict[str, Any]] = []
        for figure in self.candidates(query):
            item = self.features[figure.id]
            scores, matched = self.service._component_scores(
                inputs.query,
                figure,
                item,
                inputs.bge_vector,
                inputs.visual_vector,
                inputs.bm25_scores.get(str(figure.id), 0.0),
                inputs.clip_vector,
            )
            evidence = uncertainty = None
            draft = self.drafts.get(figure.id)
            functions = scoped_functions(draft)
            components: dict[str, Any]
            if method in {"bm25", "bge", "chinese_clip"}:
                if method == "bm25":
                    score = inputs.bm25_scores.get(str(figure.id), 0.0)
                    components = {
                        "bm25_raw": inputs.bm25_raw.get(str(figure.id), 0.0),
                        "bm25_normalized": score,
                    }
                elif method == "bge":
                    score = cosine_to_unit(
                        cosine_similarity(inputs.bge_vector or [], item["text_vector"])
                    )
                    components = {"bge_cosine_unit": score}
                else:
                    score = float(scores["sv"] or 0.0)
                    components = {"clip_image_cosine_unit": score}
                contributed = method != "bm25" or score > 0
            else:
                current = self.service.weights
                if method in {"hybrid", "hybrid_no_region"}:
                    # Keep identical coefficients across ablations; no tuned weights.
                    current = replace(current, beta_f=0.0, beta_g=0.0, lambda_e=0.0, lambda_u=0.0)
                    if method == "hybrid_no_region":
                        scores["sr"] = None
                elif method == "eafr_current":
                    evidence = (
                        evidence_coverage(
                            inputs.query.claims,
                            [self.service._evidence_dict(e) for e in figure.evidences],
                        )
                        if inputs.query.claims
                        else None
                    )
                    uncertainty = self.service._candidate_uncertainty(figure)
                else:
                    scores["sf"] = self.function_similarity(inputs.draft_query_functions, functions)
                    scores["sg"] = None  # No independently high-confidence relations.
                    evidence = (
                        self.function_evidence_coverage(inputs.draft_query_functions, functions)
                        if method == "eafr_drafts"
                        else None
                    )
                    # Do not convert null draft confidence into entropy or certainty.
                    uncertainty = None
                scored = score_candidate(
                    scores,
                    evidence_score=evidence,
                    model_uncertainty_score=uncertainty,
                    weights=current,
                    modality_reliability={"function": DRAFT_RELIABILITY},
                )
                score, components = scored.score, scored.score_components
                contributed = any(components["contributions"].values())
            ranked.append(
                {
                    "figure_id": str(figure.id),
                    "title": figure.title,
                    "score": score,
                    "score_components": components,
                    "has_scoring_signal": contributed,
                    "matched_region_ids": [str(r.id) for r in matched],
                    "draft_available": draft is not None,
                }
            )
        ranked.sort(key=lambda row: (-row["score"], row["figure_id"]))
        ranking_ms = (time.perf_counter() - ranking_started) * 1000
        signature = [
            {"figure_id": r["figure_id"], "score": r["score"], "components": r["score_components"]}
            for r in ranked
        ]
        return {
            "query_id": query.id,
            "method": method,
            "status": "completed",
            "candidate_count": len(ranked),
            "results": ranked[:top_k],
            "zero_signal_candidates": sum(not r["has_scoring_signal"] for r in ranked),
            "ranking_sha256": canonical_hash(signature),
            "latency_ms": (time.perf_counter() - started) * 1000,
            "feature_ms": feature_ms,
            "ranking_ms": ranking_ms,
            "input_sha256": inputs.input_sha256,
            "query_draft_functions": [
                {"slot": f["slot"], "concept": f["concept"]} for f in inputs.draft_query_functions
            ]
            if method.startswith("eafr_drafts")
            else [],
            "model_uncertainty": None,
            "method_note": (
                "eafr_current: production signals; region uses whole-source text claims"
                if method == "eafr_current"
                else "AI draft overlay; no independent truth; cropped claims only"
                if method.startswith("eafr_drafts")
                else "controlled baseline/ablation"
            ),
        }
