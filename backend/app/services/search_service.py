from __future__ import annotations

import asyncio
import io
import logging
import time
from collections.abc import Iterable
from dataclasses import dataclass
from typing import Any
from uuid import UUID

from PIL import Image
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.config import Settings
from app.core.errors import DomainError, not_found
from app.core.security import resolve_safe_path
from app.db.models import (
    AssociationCandidate,
    Edition,
    EmbeddingRecord,
    Figure,
    Page,
    SearchSession,
)
from app.domain.enums import SearchType, VerificationState
from app.repositories.catalog import get_figure, get_page, list_figures_for_search
from app.retrieval.baseline.bm25 import tokenize_zh
from app.retrieval.evidence.spatial import scoped_region_context
from app.retrieval.providers.registry import ProviderRegistry
from app.retrieval.rerank.scoring import (
    EAFRWeights,
    cosine_similarity,
    cosine_to_unit,
    evidence_coverage,
    model_uncertainty,
    score_candidate,
)
from app.schemas.common import (
    BBox,
    CFRSummary,
    FunctionalAssertionResponse,
    RegionResponse,
    ScoreComponents,
    SearchFilters,
    SearchResponse,
    SearchResult,
    TextSearchRequest,
)
from app.services.serializers import (
    asset_ref,
    data_status,
    evidence_response,
    source_summary,
)

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class QueryContext:
    search_type: SearchType
    text: str | None
    image_bytes: bytes | None
    query_assertions: list[dict[str, Any]]
    query_relations: list[dict[str, Any]]
    claims: list[str]
    summary: dict[str, Any]


@dataclass(slots=True)
class RankedCandidate:
    figure: Figure
    score: float
    score_components: dict[str, Any]
    cfr_summary: dict[str, Any]
    evidence_summary: dict[str, Any]
    uncertainty: dict[str, float]
    matched_regions: list[RegionResponse]


class SearchService:
    """Application service for text, image and region retrieval."""

    def __init__(
        self,
        settings: Settings,
        providers: ProviderRegistry | None = None,
        weights: EAFRWeights | None = None,
    ) -> None:
        self.settings = settings
        self.providers = providers or ProviderRegistry.create(settings)
        self.weights = weights or EAFRWeights(**settings.eafr_weights.model_dump())

    async def search_text(
        self, session: AsyncSession, request: TextSearchRequest
    ) -> SearchResponse:
        query_cfr = self.providers.cfr.extract(request.query)
        query_assertions = self._cfr_to_dicts(query_cfr)
        claims = self._claims_from_text(request.query, query_assertions)
        return await self._run_search(
            session,
            QueryContext(
                search_type=SearchType.TEXT,
                text=request.query,
                image_bytes=None,
                query_assertions=query_assertions,
                query_relations=[],
                claims=claims,
                summary={"type": "text", "query": request.query},
            ),
            request.top_k,
            request.filters,
        )

    async def search_image(
        self,
        session: AsyncSession,
        content: bytes,
        mime_type: str,
        filename: str | None,
        top_k: int,
        filters: SearchFilters,
    ) -> SearchResponse:
        return await self._run_search(
            session,
            QueryContext(
                search_type=SearchType.IMAGE,
                text=None,
                image_bytes=content,
                query_assertions=[],
                query_relations=[],
                claims=[],
                summary={
                    "type": "image",
                    "filename": filename,
                    "mime_type": mime_type,
                    "byte_size": len(content),
                },
            ),
            top_k,
            filters,
        )

    async def search_region(self, session: AsyncSession, request: Any) -> SearchResponse:
        source_figure: Figure | None = None
        if request.figure_id:
            source_figure = await get_figure(session, request.figure_id)
        elif request.page_id:
            source_page = await get_page(session, request.page_id)
            if source_page and source_page.figures:
                source_figure = source_page.figures[0]
        if source_figure is None:
            raise not_found("区域来源图")
        asset = source_figure.asset or source_figure.page.asset
        if asset is None:
            raise DomainError("INVALID_REGION_SOURCE", "区域来源没有可读取的图像", 422)
        image_path = resolve_safe_path(self.settings.asset_root, asset.relative_path)
        if not image_path.is_file():
            raise DomainError("INVALID_REGION_SOURCE", "区域来源图像文件不存在", 422)
        image_bytes = self._crop_image(image_path.read_bytes(), request.bbox)
        scoped_text, query_assertions, scoped_relations = scoped_region_context(
            source_figure, request.bbox.model_dump()
        )
        claims = self._claims_from_text(scoped_text, query_assertions)
        return await self._run_search(
            session,
            QueryContext(
                search_type=SearchType.REGION,
                text=None,
                image_bytes=image_bytes,
                query_assertions=query_assertions,
                query_relations=scoped_relations,
                claims=claims,
                summary={
                    "type": "region",
                    "source_figure_id": str(source_figure.id),
                    "bbox": request.bbox.model_dump(),
                    "coordinate_space": "normalized",
                    "claim_scope": "spatial_supports_contained_in_crop",
                },
            ),
            request.top_k,
            request.filters,
            exclude_figure_id=source_figure.id,
        )

    async def _run_search(
        self,
        session: AsyncSession,
        query: QueryContext,
        top_k: int,
        filters: SearchFilters,
        exclude_figure_id: UUID | None = None,
    ) -> SearchResponse:
        started = time.perf_counter()
        figures = await list_figures_for_search(session)
        figures = [
            figure
            for figure in figures
            if figure.id != exclude_figure_id and self._matches_filters(figure, filters)
        ]
        embedding_map = await self._embedding_map(session, figures)
        documents = {str(figure.id): self._figure_text(figure) for figure in figures}
        self.providers.bm25.fit(documents)
        bm25_result = self.providers.bm25.search(query.text or "", top_k=max(top_k * 5, 50))
        bm25_scores = {hit.document_id: hit.score for hit in bm25_result.hits}
        max_bm25 = max(bm25_scores.values(), default=0.0)
        query_text_vector = (
            (await asyncio.to_thread(self.providers.text_embedding.encode_query, query.text)).vector
            if query.text
            else None
        )
        query_image_vector = (
            (
                await asyncio.to_thread(self.providers.image_embedding.encode, query.image_bytes)
            ).vector
            if query.image_bytes
            else None
        )
        # Text/image cross-modal comparisons use ONLY the shared Chinese-CLIP space.
        query_clip_vector = (
            (await asyncio.to_thread(self.providers.clip_text.encode, query.text)).vector
            if query.text and self.providers.clip_text
            else None
        )
        ranked: list[RankedCandidate] = []
        for figure in figures:
            item = await asyncio.to_thread(self._candidate_features, figure, embedding_map)
            scores, matched_regions = self._component_scores(
                query,
                figure,
                item,
                query_text_vector,
                query_image_vector,
                bm25_scores.get(str(figure.id), 0.0) / max_bm25 if max_bm25 else 0.0,
                query_clip_vector,
            )
            evidence_items = [self._evidence_dict(evidence) for evidence in figure.evidences]
            evidence_score = (
                evidence_coverage(query.claims, evidence_items) if query.claims else None
            )
            uncertainty_score = self._candidate_uncertainty(figure)
            result = score_candidate(
                scores,
                evidence_score=evidence_score,
                model_uncertainty_score=uncertainty_score,
                weights=self.weights,
            )
            cfr_summary = {
                "assertions": [self._assertion_dict(assertion) for assertion in figure.assertions],
                "uncertainty": uncertainty_score if uncertainty_score is not None else 1.0,
            }
            material_missingness = self._material_missingness(figure)
            evidence_summary: dict[str, Any] = {
                "coverage": evidence_score,
                "matched_region_ids": [str(region.id) for region in matched_regions],
                "material_missingness": material_missingness,
            }
            ranked.append(
                RankedCandidate(
                    figure=figure,
                    score=result.score,
                    score_components=result.score_components,
                    cfr_summary=cfr_summary,
                    evidence_summary=evidence_summary,
                    uncertainty={
                        "model": uncertainty_score if uncertainty_score is not None else 1.0,
                        "model_available": float(uncertainty_score is not None),
                        "material_missingness": material_missingness,
                    },
                    matched_regions=matched_regions,
                )
            )
        ranked.sort(key=lambda item: (-item.score, str(item.figure.id)))
        ranked = ranked[:top_k]
        latency_ms = (time.perf_counter() - started) * 1000
        versions = [health.as_dict() for health in await asyncio.to_thread(self.providers.health)]
        version_map: dict[str, Any] = {str(metadata["provider"]): metadata for metadata in versions}
        session_record = SearchSession(
            search_type=query.search_type.value,
            query_summary=query.summary,
            config={
                "weights": self.weights.as_dict(),
                "scoring_policy_version": "eafr-v2-spatial",
                "top_k": top_k,
                "filters": filters.model_dump(mode="json"),
                "retrieval_profile": self.settings.retrieval_profile,
                "text_fusion": {"semantic": 0.7, "bm25": 0.3},
                "cross_modal_space": "chinese_clip" if self.providers.clip_text else None,
            },
            model_versions=version_map,
            latency_ms=latency_ms,
            status="completed",
        )
        session.add(session_record)
        await session.flush()
        candidate_records: list[AssociationCandidate] = []
        for rank, ranked_item in enumerate(ranked, start=1):
            candidate = AssociationCandidate(
                search_session_id=session_record.id,
                figure_id=ranked_item.figure.id,
                rank=rank,
                score=ranked_item.score,
                score_components=ranked_item.score_components,
                cfr_summary=ranked_item.cfr_summary,
                evidence_summary=ranked_item.evidence_summary,
                uncertainty=ranked_item.uncertainty,
                verification_state=VerificationState.PENDING.value,
            )
            session.add(candidate)
            candidate_records.append(candidate)
        await session.flush()
        await session.commit()
        return SearchResponse(
            search_id=session_record.id,
            query_summary=query.summary,
            results=[
                self._search_result(item, session_record.id, candidate_records[index].id)
                for index, item in enumerate(ranked)
            ],
            latency_ms=latency_ms,
            model_versions=version_map,
        )

    async def get_search(self, session: AsyncSession, search_id: UUID) -> SearchResponse:
        statement = (
            select(SearchSession)
            .where(SearchSession.id == search_id)
            .options(
                selectinload(SearchSession.candidates)
                .selectinload(AssociationCandidate.figure)
                .selectinload(Figure.asset),
                selectinload(SearchSession.candidates)
                .selectinload(AssociationCandidate.figure)
                .selectinload(Figure.regions),
                selectinload(SearchSession.candidates)
                .selectinload(AssociationCandidate.figure)
                .selectinload(Figure.assertions),
                selectinload(SearchSession.candidates)
                .selectinload(AssociationCandidate.figure)
                .selectinload(Figure.evidences),
                selectinload(SearchSession.candidates)
                .selectinload(AssociationCandidate.figure)
                .selectinload(Figure.page)
                .selectinload(Page.edition)
                .selectinload(Edition.book),
            )
        )
        result = await session.execute(statement)
        record = result.scalar_one_or_none()
        if record is None:
            raise not_found("搜索会话")
        results: list[SearchResult] = []
        for candidate in sorted(record.candidates, key=lambda item: item.rank):
            results.append(self._stored_result(candidate, record.id))
        return SearchResponse(
            search_id=record.id,
            query_summary=record.query_summary,
            results=results,
            latency_ms=record.latency_ms or 0.0,
            model_versions=record.model_versions,
        )

    async def get_candidate(self, session: AsyncSession, candidate_id: UUID) -> SearchResult:
        statement = (
            select(AssociationCandidate)
            .where(AssociationCandidate.id == candidate_id)
            .options(
                selectinload(AssociationCandidate.figure).selectinload(Figure.asset),
                selectinload(AssociationCandidate.figure).selectinload(Figure.regions),
                selectinload(AssociationCandidate.figure).selectinload(Figure.assertions),
                selectinload(AssociationCandidate.figure).selectinload(Figure.evidences),
                selectinload(AssociationCandidate.figure)
                .selectinload(Figure.page)
                .selectinload(Page.edition)
                .selectinload(Edition.book),
            )
        )
        result = await session.execute(statement)
        candidate = result.scalar_one_or_none()
        if candidate is None:
            raise not_found("候选关联")
        return self._stored_result(candidate, candidate.search_session_id)

    @staticmethod
    def _matches_filters(figure: Figure, filters: SearchFilters) -> bool:
        if filters.book_ids and figure.page.edition.book_id not in filters.book_ids:
            return False
        if filters.edition_ids and figure.page.edition_id not in filters.edition_ids:
            return False
        if (
            filters.dataset_kinds
            and figure.provenance.get("dataset_kind", "synthetic_fixture")
            not in filters.dataset_kinds
        ):
            return False
        return True

    async def _embedding_map(
        self, session: AsyncSession, figures: list[Figure]
    ) -> dict[tuple[str, UUID, str], list[float]]:
        entity_ids = [figure.id for figure in figures]
        entity_ids.extend(region.id for figure in figures for region in figure.regions)
        if not entity_ids:
            return {}
        result = await session.execute(
            select(EmbeddingRecord).where(EmbeddingRecord.entity_id.in_(entity_ids))
        )
        records = result.scalars().all()
        provider_map = {
            "text": self.providers.text_embedding,
            "image": self.providers.image_embedding,
            "clip_text": self.providers.clip_text,
        }
        compatible: dict[tuple[str, UUID, str], list[float]] = {}
        for record in records:
            provider = provider_map.get(record.modality)
            if provider is None:
                continue
            metadata = provider.metadata()
            if (
                record.provider == metadata.provider
                and record.model == metadata.model
                and record.version == metadata.version
                and record.dimension == metadata.dimension
                and record.preprocessing_hash == metadata.preprocessing_hash
                and len(record.vector) == metadata.dimension
            ):
                compatible[(record.entity_type, record.entity_id, record.modality)] = list(
                    record.vector
                )
        return compatible

    def _candidate_features(
        self,
        figure: Figure,
        embedding_map: dict[tuple[str, UUID, str], list[float]],
    ) -> dict[str, Any]:
        text = self._figure_text(figure)
        image_vector = embedding_map.get(("figure", figure.id, "image"))
        text_vector = embedding_map.get(("figure", figure.id, "text"))
        clip_text_vector = embedding_map.get(("figure", figure.id, "clip_text"))
        region_vectors = [
            (region, embedding_map.get(("region", region.id, "image"))) for region in figure.regions
        ]
        if self.providers.clip_text is not None:
            if (
                (text and (text_vector is None or clip_text_vector is None))
                or (figure.asset is not None and image_vector is None)
                or any(vector is None for _, vector in region_vectors)
            ):
                raise DomainError(
                    "MODEL_UNAVAILABLE",
                    "当前语料尚未完成所选模型的向量索引，请执行重建索引",
                    503,
                    {"reason": "compatible_index_missing", "figure_id": str(figure.id)},
                )
            return {
                "text": text,
                "image": image_vector,
                "text_vector": text_vector,
                "clip_text_vector": clip_text_vector,
                "region_vectors": region_vectors,
            }
        if text_vector is None:
            text_vector = list(self.providers.text_embedding.encode(text).vector)
        if image_vector is None and figure.asset is not None:
            path = resolve_safe_path(self.settings.asset_root, figure.asset.relative_path)
            if path.is_file():
                try:
                    image_input: Any = path
                    if figure.provenance.get("dataset_kind") in {
                        "human_reviewed_real_pilot",
                        "ai_assisted_real_pilot",
                    }:
                        if (
                            figure.bbox_x is None
                            or figure.bbox_y is None
                            or figure.bbox_width is None
                            or figure.bbox_height is None
                        ):
                            raise ValueError("real figure has no confirmed extent")
                        image_input = self._crop_image(
                            path.read_bytes(),
                            BBox(
                                x=figure.bbox_x,
                                y=figure.bbox_y,
                                width=figure.bbox_width,
                                height=figure.bbox_height,
                            ),
                        )
                    image_vector = list(self.providers.image_embedding.encode(image_input).vector)
                except Exception:
                    logger.warning("无法读取候选图像", extra={"request_id": "-"}, exc_info=True)
        return {
            "text": text,
            "image": image_vector,
            "text_vector": text_vector,
            "clip_text_vector": None,
            "region_vectors": region_vectors,
        }

    def _component_scores(
        self,
        query: QueryContext,
        figure: Figure,
        item: dict[str, Any],
        query_text_vector: Iterable[float] | None,
        query_image_vector: Iterable[float] | None,
        bm25_score: float,
        query_clip_vector: Iterable[float] | None = None,
    ) -> tuple[dict[str, float | None], list[RegionResponse]]:
        sv: float | None = None
        st: float | None = None
        sr: float | None = None
        if query_image_vector is not None and item["image"] is not None:
            sv = cosine_to_unit(cosine_similarity(query_image_vector, item["image"]))
        elif query_clip_vector is not None and item["image"] is not None:
            sv = cosine_to_unit(cosine_similarity(query_clip_vector, item["image"]))
        if query_text_vector is not None and item["text_vector"] is not None:
            semantic = cosine_to_unit(cosine_similarity(query_text_vector, item["text_vector"]))
            st = 0.7 * semantic + 0.3 * bm25_score
        elif query_image_vector is not None and item.get("clip_text_vector") is not None:
            st = cosine_to_unit(cosine_similarity(query_image_vector, item["clip_text_vector"]))
        matched_regions: list[RegionResponse] = []
        visual_query = query_image_vector if query_image_vector is not None else query_clip_vector
        if visual_query is not None:
            scored_regions = []
            for region, vector in item["region_vectors"]:
                if vector is not None:
                    scored_regions.append(
                        (cosine_to_unit(cosine_similarity(visual_query, vector)), region)
                    )
            scored_regions.sort(key=lambda pair: (-pair[0], str(pair[1].id)))
            if scored_regions:
                sr = scored_regions[0][0]
                matched_regions = [
                    RegionResponse.model_validate(region) for _, region in scored_regions[:3]
                ]
        sf = self._functional_similarity(query.query_assertions, figure.assertions)
        sg: float | None = None
        if query.query_relations and figure.relations:
            sg = self.providers.graph.similarity(
                query.query_relations,
                [self._relation_dict(item) for item in figure.relations],
            ).score
        if not matched_regions:
            matched_regions = [
                RegionResponse.model_validate(region) for region in figure.regions[:3]
            ]
        return {"sv": sv, "st": st, "sr": sr, "sf": sf, "sg": sg}, matched_regions

    def _functional_similarity(
        self, query: list[dict[str, Any]], candidate: Iterable[Any]
    ) -> float | None:
        if not query:
            return None
        query_map: dict[tuple[str, str], float] = {}
        for item in query:
            concept = item.get("concept")
            if concept in {None, "unknown"}:
                continue
            slot = str(item.get("slot"))
            confidence = float(item.get("confidence", 0.0))
            aliases = [str(concept), *[str(term) for term in item.get("matched_terms", ())]]
            for alias in aliases:
                key = (slot, self._canonical_function_concept(slot, alias))
                query_map[key] = max(query_map.get(key, 0.0), confidence)
        candidate_map = {
            (
                item.slot,
                self._canonical_function_concept(item.slot, item.concept),
            ): max(0.0, min(1.0, float(item.confidence)))
            for item in candidate
            if item.concept != "unknown"
        }
        if not query_map or not candidate_map:
            return None
        keys = query_map.keys() | candidate_map.keys()
        numerator = sum(min(query_map.get(key, 0.0), candidate_map.get(key, 0.0)) for key in keys)
        denominator = sum(max(query_map.get(key, 0.0), candidate_map.get(key, 0.0)) for key in keys)
        return numerator / denominator if denominator else 0.0

    def _canonical_function_concept(self, slot: str, value: str) -> str:
        """Map fixture labels and controlled vocabulary terms to one ID."""

        normalized = value.strip().casefold()
        vocabulary = getattr(self.providers.cfr, "_vocabulary", {})
        for candidate_slot, concepts in vocabulary.items():
            if candidate_slot != slot:
                continue
            for concept_id, terms in concepts.items():
                if normalized == str(concept_id).casefold() or any(
                    normalized == str(term).casefold() for term in terms
                ):
                    return str(concept_id)
        return normalized

    @staticmethod
    def _figure_text(figure: Figure) -> str:
        parts = [figure.title or ""]
        parts.extend(chunk.corrected_text or chunk.text for chunk in figure.text_chunks)
        return " ".join(part for part in parts if part).strip()

    @staticmethod
    def _claims_from_text(text: str, assertions: list[dict[str, Any]]) -> list[str]:
        concepts = [
            str(item["concept"])
            for item in assertions
            if item.get("concept") not in {None, "unknown"}
        ]
        tokens = [token for token in tokenize_zh(text) if len(token) >= 2]
        result: list[str] = []
        for value in concepts + tokens[:12]:
            if value not in result:
                result.append(value)
        return result

    @staticmethod
    def _cfr_to_dicts(cfr_result: Any) -> list[dict[str, Any]]:
        values: list[dict[str, Any]] = []
        for concepts in cfr_result.slots.values():
            for concept in concepts:
                if concept.concept != "unknown":
                    values.append(
                        {
                            "slot": concept.slot,
                            "concept": concept.concept,
                            "confidence": concept.confidence,
                            "status": "Inferred",
                            "matched_terms": list(concept.matched_terms),
                        }
                    )
        return values

    @staticmethod
    def _assertion_dict(assertion: Any) -> dict[str, Any]:
        return {
            "id": str(assertion.id),
            "slot": assertion.slot,
            "concept": assertion.concept,
            "confidence": assertion.confidence,
            "state": assertion.state,
            "evidence_pointer": assertion.evidence_pointer,
        }

    @staticmethod
    def _evidence_dict(evidence: Any) -> dict[str, Any]:
        return {
            "id": str(evidence.id),
            "status": evidence.status,
            "text": evidence.content,
            "claim_id": evidence.pointer,
            "supports": [evidence.pointer] if evidence.pointer else [],
        }

    @staticmethod
    def _relation_dict(relation: Any) -> dict[str, Any]:
        return {
            "subject": relation.subject,
            "predicate": relation.predicate,
            "object": relation.object,
            "confidence": relation.confidence,
        }

    @staticmethod
    def _candidate_uncertainty(figure: Figure) -> float | None:
        scores = [float(assertion.confidence) for assertion in figure.assertions]
        return model_uncertainty(scores) if scores else None

    @staticmethod
    def _material_missingness(figure: Figure) -> float:
        missing = 0
        total = 3
        if not figure.asset:
            missing += 1
        if not figure.text_chunks:
            missing += 1
        if not figure.assertions:
            missing += 1
        return missing / total

    def _search_result(
        self, item: RankedCandidate, search_id: UUID, candidate_id: UUID
    ) -> SearchResult:
        return SearchResult(
            candidate_id=candidate_id,
            figure_id=item.figure.id,
            source=source_summary(item.figure),
            image_ref=asset_ref(item.figure.asset),
            matched_regions=item.matched_regions,
            score=item.score,
            score_components=ScoreComponents.model_validate(item.score_components),
            cfr_summary=CFRSummary(
                assertions=[
                    FunctionalAssertionResponse.model_validate(value)
                    for value in item.cfr_summary["assertions"]
                ],
                uncertainty=float(item.cfr_summary["uncertainty"]),
            ),
            evidence=[evidence_response(evidence) for evidence in item.figure.evidences],
            uncertainty=item.uncertainty,
            verification_state=VerificationState.PENDING,
            title=item.figure.title,
            data_status=data_status(item.figure),
        )

    def _stored_result(self, candidate: AssociationCandidate, search_id: UUID) -> SearchResult:
        matched_ids = candidate.evidence_summary.get("matched_region_ids", [])
        regions_by_id = {str(r.id): r for r in candidate.figure.regions}
        regions = (
            [
                RegionResponse.model_validate(regions_by_id[region_id])
                for region_id in matched_ids
                if region_id in regions_by_id
            ][:3]
            if matched_ids
            else [RegionResponse.model_validate(region) for region in candidate.figure.regions[:3]]
        )
        assertions = [
            FunctionalAssertionResponse.model_validate(value)
            for value in candidate.cfr_summary.get("assertions", [])
        ]
        return SearchResult(
            candidate_id=candidate.id,
            figure_id=candidate.figure.id,
            source=source_summary(candidate.figure),
            image_ref=asset_ref(candidate.figure.asset),
            matched_regions=regions,
            score=candidate.score,
            score_components=ScoreComponents.model_validate(candidate.score_components),
            cfr_summary=CFRSummary(
                assertions=assertions,
                uncertainty=float(candidate.cfr_summary.get("uncertainty", 0.0)),
            ),
            evidence=[evidence_response(evidence) for evidence in candidate.figure.evidences],
            uncertainty={key: float(value) for key, value in candidate.uncertainty.items()},
            verification_state=VerificationState(candidate.verification_state),
            title=candidate.figure.title,
            data_status=data_status(candidate.figure),
        )

    @staticmethod
    def _crop_image(content: bytes, bbox: BBox) -> bytes:
        try:
            with Image.open(io.BytesIO(content)) as source:
                source.load()
                width, height = source.size
                left = max(0, min(width - 1, int(bbox.x * width)))
                top = max(0, min(height - 1, int(bbox.y * height)))
                right = max(left + 1, min(width, int((bbox.x + bbox.width) * width)))
                bottom = max(top + 1, min(height, int((bbox.y + bbox.height) * height)))
                cropped = source.crop((left, top, right, bottom)).convert("RGB")
                output = io.BytesIO()
                cropped.save(output, format="PNG")
                cropped.close()
                return output.getvalue()
        except Exception as exc:
            raise DomainError("INVALID_REGION_SOURCE", "无法裁剪区域图像", 422) from exc
