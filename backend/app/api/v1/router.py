"""Versioned REST API for the V1 offline retrieval loop."""

from __future__ import annotations

import asyncio
import json
import logging
from pathlib import Path
from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, Depends, File, Form, Request, UploadFile
from fastapi.responses import FileResponse
from pydantic import ValidationError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import session_dependency, settings_dependency
from app.core.config import Settings
from app.core.errors import DomainError, not_found
from app.core.security import resolve_safe_path, sanitize_image_bytes, validate_image_bytes
from app.db.models import Asset, AssociationCandidate, Book, Edition, IngestionJob, Verification
from app.db.session import SessionFactory
from app.domain.enums import EvidenceState, VerificationState
from app.ingestion.loader import ManifestValidationError, validate_manifest_name
from app.retrieval.providers.registry import ProviderRegistry
from app.schemas.common import (
    BookSummary,
    CandidateResponse,
    CapabilitiesResponse,
    EditionSummary,
    FigureResponse,
    HealthResponse,
    IngestionJobRequest,
    IngestionJobResponse,
    PageResponse,
    ProviderStatus,
    RegionSearchRequest,
    SearchFilters,
    SearchResponse,
    TextSearchRequest,
    VerificationRequest,
    VerificationResponse,
)
from app.services.ingestion_service import run_ingestion_job
from app.services.search_service import SearchService
from app.services.serializers import edition_summary, figure_response, page_response

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1")


def _request_id(request: Request) -> str:
    return str(getattr(request.state, "request_id", "-"))


def _enum_value(value: Any) -> str:
    return str(getattr(value, "value", value))


def _service(settings: Settings = Depends(settings_dependency)) -> SearchService:
    return SearchService(settings)


def _parse_filters(raw: str | None) -> SearchFilters:
    if not raw:
        return SearchFilters()
    try:
        value = json.loads(raw)
        if not isinstance(value, dict):
            raise ValueError("filters must be an object")
        return SearchFilters.model_validate(value)
    except (json.JSONDecodeError, ValidationError, ValueError) as exc:
        raise DomainError("INVALID_QUERY", "filters 参数格式不正确", 422) from exc


@router.get("/health", response_model=HealthResponse)
async def health(request: Request) -> HealthResponse:
    from app.db.session import ping_database

    settings = settings_dependency()
    if not await ping_database():
        raise DomainError("DATABASE_UNAVAILABLE", "数据库暂不可用", 503)
    return HealthResponse(
        status="ok", version=settings.app_version, database="ok", request_id=_request_id(request)
    )


@router.get("/capabilities", response_model=CapabilitiesResponse)
async def capabilities(settings: Settings = Depends(settings_dependency)) -> CapabilitiesResponse:
    providers = []
    health_items = await asyncio.to_thread(ProviderRegistry.create(settings).health)
    for health_item in health_items:
        providers.append(
            ProviderStatus(
                name=health_item.provider,
                provider=health_item.provider,
                model=health_item.model,
                version=health_item.version,
                available=health_item.available,
                dimension=health_item.dimension,
                detail=health_item.details,
            )
        )
    return CapabilitiesResponse(
        search_types=(
            ["text", "image", "region"] if all(item.available for item in health_items) else []
        ),
        verification_states=[
            VerificationState.WORTH_COMPARING,
            VerificationState.REJECTED,
            VerificationState.DISPUTED,
            VerificationState.VERIFIED,
            VerificationState.INSUFFICIENT_EVIDENCE,
        ],
        evidence_states=[
            EvidenceState.OBSERVED,
            EvidenceState.DOCUMENTED,
            EvidenceState.INFERRED,
            EvidenceState.VERIFIED,
        ],
        providers=providers,
        upload_limits={
            "max_upload_bytes": settings.max_upload_bytes,
            "max_image_pixels": settings.max_image_pixels,
        },
    )


@router.get("/books", response_model=list[BookSummary])
async def books(session: AsyncSession = Depends(session_dependency)) -> list[BookSummary]:
    result = await session.execute(select(Book).order_by(Book.title))
    return [BookSummary.model_validate(item) for item in result.scalars().all()]


@router.get("/books/{book_id}/editions", response_model=list[EditionSummary])
async def editions(
    book_id: UUID, session: AsyncSession = Depends(session_dependency)
) -> list[EditionSummary]:
    if await session.get(Book, book_id) is None:
        raise not_found("书籍")
    result = await session.execute(
        select(Edition).where(Edition.book_id == book_id).order_by(Edition.name)
    )
    return [edition_summary(item) for item in result.scalars().all()]


@router.get("/pages/{page_id}", response_model=PageResponse)
async def page_detail(
    page_id: UUID, session: AsyncSession = Depends(session_dependency)
) -> PageResponse:
    from app.repositories.catalog import get_page

    page = await get_page(session, page_id)
    if page is None:
        raise not_found("页面")
    return page_response(page)


@router.get("/figures/{figure_id}", response_model=FigureResponse)
async def figure_detail(
    figure_id: UUID, session: AsyncSession = Depends(session_dependency)
) -> FigureResponse:
    from app.repositories.catalog import get_figure

    figure = await get_figure(session, figure_id)
    if figure is None:
        raise not_found("技术图")
    return figure_response(figure)


@router.get("/assets/{asset_id}")
async def asset_detail(
    asset_id: UUID,
    session: AsyncSession = Depends(session_dependency),
    settings: Settings = Depends(settings_dependency),
) -> FileResponse:
    asset = await session.get(Asset, asset_id)
    if asset is None:
        raise not_found("资源")
    if not asset.allow_redistribution:
        raise DomainError("LICENSE_RESTRICTED", "该资源不允许公开再分发", 403)
    path = resolve_safe_path(settings.asset_root, asset.relative_path)
    if not path.is_file():
        raise not_found("资源文件")
    return FileResponse(path, media_type=asset.mime_type, filename=Path(asset.relative_path).name)


@router.post("/search/text", response_model=SearchResponse)
async def search_text(
    request: TextSearchRequest,
    session: AsyncSession = Depends(session_dependency),
    service: SearchService = Depends(_service),
) -> SearchResponse:
    return await service.search_text(session, request)


@router.post("/search/image", response_model=SearchResponse)
async def search_image(
    file: Annotated[UploadFile, File(...)],
    top_k: Annotated[int, Form()] = 10,
    filters: Annotated[str | None, Form()] = None,
    session: AsyncSession = Depends(session_dependency),
    settings: Settings = Depends(settings_dependency),
    service: SearchService = Depends(_service),
) -> SearchResponse:
    if top_k < 1 or top_k > 50:
        raise DomainError("INVALID_QUERY", "top_k 必须在 1 到 50 之间", 422)
    content = await file.read(settings.max_upload_bytes + 1)
    info = validate_image_bytes(content, file.content_type, settings)
    # Normalize EXIF orientation and strip metadata before feature extraction.
    safe_content = sanitize_image_bytes(content, info.mime_type)
    return await service.search_image(
        session,
        safe_content,
        "image/png" if safe_content != content or info.mime_type == "image/png" else info.mime_type,
        file.filename,
        top_k,
        _parse_filters(filters),
    )


@router.post("/search/region", response_model=SearchResponse)
async def search_region(
    request: RegionSearchRequest,
    session: AsyncSession = Depends(session_dependency),
    service: SearchService = Depends(_service),
) -> SearchResponse:
    return await service.search_region(session, request)


@router.get("/search/{search_id}", response_model=SearchResponse)
async def search_detail(
    search_id: UUID,
    session: AsyncSession = Depends(session_dependency),
    service: SearchService = Depends(_service),
) -> SearchResponse:
    return await service.get_search(session, search_id)


@router.get("/associations/{candidate_id}", response_model=CandidateResponse)
async def association_detail(
    candidate_id: UUID,
    session: AsyncSession = Depends(session_dependency),
    service: SearchService = Depends(_service),
) -> CandidateResponse:
    result = await service.get_candidate(session, candidate_id)
    candidate = await session.get(AssociationCandidate, candidate_id)
    if candidate is None:
        raise not_found("候选关联")
    return CandidateResponse(
        **result.model_dump(),
        search_id=candidate.search_session_id,
        created_at=candidate.created_at,
    )


@router.post("/associations/{candidate_id}/verify", response_model=VerificationResponse)
async def verify_association(
    candidate_id: UUID,
    payload: VerificationRequest,
    session: AsyncSession = Depends(session_dependency),
) -> VerificationResponse:
    candidate = await session.get(AssociationCandidate, candidate_id)
    if candidate is None:
        raise not_found("候选关联")
    state = _enum_value(payload.state)
    candidate.verification_state = state
    verification = Verification(
        candidate_id=candidate_id,
        state=state,
        note=payload.note,
    )
    session.add(verification)
    await session.commit()
    await session.refresh(verification)
    return VerificationResponse.model_validate(verification)


@router.post("/ingestion/jobs", response_model=IngestionJobResponse, status_code=202)
async def create_ingestion_job(
    payload: IngestionJobRequest,
    background_tasks: BackgroundTasks,
    session: AsyncSession = Depends(session_dependency),
    settings: Settings = Depends(settings_dependency),
) -> IngestionJobResponse:
    try:
        manifest_name = validate_manifest_name(payload.manifest_name)
    except ManifestValidationError as exc:
        raise DomainError(exc.code, str(exc), 422, exc.details) from exc
    job = IngestionJob(manifest_name=manifest_name, dry_run=payload.dry_run, status="queued")
    session.add(job)
    await session.flush()
    await session.commit()
    background_tasks.add_task(run_ingestion_job, job.id, settings, SessionFactory)
    await session.refresh(job)
    return IngestionJobResponse.model_validate(job)


@router.get("/ingestion/jobs/{job_id}", response_model=IngestionJobResponse)
async def ingestion_job_detail(
    job_id: UUID, session: AsyncSession = Depends(session_dependency)
) -> IngestionJobResponse:
    job = await session.get(IngestionJob, job_id)
    if job is None:
        raise not_found("导入任务")
    return IngestionJobResponse.model_validate(job)


__all__ = ["router"]
