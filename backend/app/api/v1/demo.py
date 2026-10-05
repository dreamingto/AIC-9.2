"""Domestic competition cases resolved from the real catalogue on every request."""

from __future__ import annotations

from typing import Literal

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import session_dependency, settings_dependency
from app.core.config import Settings
from app.core.errors import DomainError
from app.domain.demo_cases import DOMESTIC_CASES
from app.repositories.catalog import get_figure
from app.schemas.common import (
    APIModel,
    BBox,
    FigureResponse,
    RegionSearchRequest,
    SearchFilters,
    SearchResponse,
    TextSearchRequest,
)
from app.services.ingestion_service import stable_id
from app.services.search_service import SearchService
from app.services.serializers import figure_response

router = APIRouter(prefix="/api/v1/demo", tags=["competition demo"])


class DemoCaseResponse(APIModel):
    id: str
    title: str
    description: str
    source_note: str
    text_query: str
    figures: list[FigureResponse]
    region_query: RegionSearchRequest | None
    ready: bool
    limitations: list[str]
    evaluation_status: Literal["not_evaluated"] = "not_evaluated"


class DemoSearchRequest(BaseModel):
    mode: Literal["text", "region"]


async def resolve_case(case_id: str, session: AsyncSession) -> DemoCaseResponse:
    spec = next((item for item in DOMESTIC_CASES if item["id"] == case_id), None)
    if spec is None:
        raise DomainError("RESOURCE_NOT_FOUND", "演示案例不存在", 404)
    figures = []
    for key in spec["figure_keys"]:
        figure = await get_figure(session, stable_id("figure", key))
        if figure and figure.provenance.get("dataset_kind") == "ai_assisted_real_pilot":
            figures.append(figure_response(figure))
    ready = len(figures) == len(spec["figure_keys"])
    return DemoCaseResponse(
        id=spec["id"],
        title=spec["title"],
        description=spec["description"],
        source_note=spec["source_note"],
        text_query=spec["text_query"],
        figures=figures,
        region_query=(
            RegionSearchRequest(
                figure_id=figures[0].id,
                bbox=BBox(**spec["bbox"]),
                coordinate_space="normalized",
                top_k=10,
                filters=SearchFilters(dataset_kinds=["ai_assisted_real_pilot"]),
            )
            if ready
            else None
        ),
        ready=ready,
        limitations=list(spec["limitations"]),
    )


@router.get("/cases", response_model=list[DemoCaseResponse])
async def cases(session: AsyncSession = Depends(session_dependency)) -> list[DemoCaseResponse]:
    return [await resolve_case(spec["id"], session) for spec in DOMESTIC_CASES]


@router.post("/cases/{case_id}/search", response_model=SearchResponse)
async def case_search(
    case_id: str,
    payload: DemoSearchRequest,
    session: AsyncSession = Depends(session_dependency),
    settings: Settings = Depends(settings_dependency),
) -> SearchResponse:
    case = await resolve_case(case_id, session)
    if not case.ready or case.region_query is None:
        raise DomainError("DEMO_DATA_UNAVAILABLE", "请先导入国内古籍比赛语料", 409)
    service = SearchService(settings)
    if payload.mode == "region":
        return await service.search_region(session, case.region_query)
    return await service.search_text(
        session,
        TextSearchRequest(
            query=case.text_query,
            top_k=10,
            filters=SearchFilters(dataset_kinds=["ai_assisted_real_pilot"]),
        ),
    )
