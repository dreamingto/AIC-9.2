from __future__ import annotations

import math
from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.domain.enums import EvidenceState, VerificationState


class APIModel(BaseModel):
    model_config = ConfigDict(from_attributes=True, use_enum_values=True)


class ErrorBody(APIModel):
    code: str
    message: str
    request_id: str
    details: dict[str, Any] = Field(default_factory=dict)


class ErrorResponse(APIModel):
    error: ErrorBody


class AssetRef(APIModel):
    id: UUID
    url: str
    mime_type: str
    width: int | None = None
    height: int | None = None
    license_status: str
    allow_redistribution: bool


class SourceSummary(APIModel):
    book_title: str
    edition: str
    source_name: str | None = None
    volume: str | None = None
    page_or_folio: str
    source_url: str | None = None
    license_status: str


class BookSummary(APIModel):
    id: UUID
    title: str
    author: str | None = None
    era: str | None = None
    description: str | None = None


class EditionSummary(APIModel):
    id: UUID
    book_id: UUID
    name: str
    edition_note: str | None = None
    source_name: str | None = None
    license_status: str
    allow_redistribution: bool


class RegionResponse(APIModel):
    id: UUID
    label: str | None = None
    x: float
    y: float
    width: float
    height: float


class TextChunkResponse(APIModel):
    id: UUID
    chunk_type: str
    text: str
    corrected_text: str | None = None
    source_pointer: str | None = None
    state: EvidenceState


class EvidenceResponse(APIModel):
    id: UUID
    evidence_type: str
    status: EvidenceState
    content: str
    pointer: str | None = None
    support_confidence: float


class FunctionalAssertionResponse(APIModel):
    id: UUID
    slot: str
    concept: str
    confidence: float
    state: EvidenceState
    evidence_pointer: str | None = None


class RelationResponse(APIModel):
    id: UUID
    subject: str
    predicate: str
    object: str
    weight: float
    confidence: float


class FigureResponse(APIModel):
    id: UUID
    page_id: UUID
    title: str | None = None
    asset: AssetRef | None = None
    bbox: dict[str, float] | None = None
    regions: list[RegionResponse] = Field(default_factory=list)
    text_chunks: list[TextChunkResponse] = Field(default_factory=list)
    assertions: list[FunctionalAssertionResponse] = Field(default_factory=list)
    relations: list[RelationResponse] = Field(default_factory=list)
    evidences: list[EvidenceResponse] = Field(default_factory=list)


class PageResponse(APIModel):
    id: UUID
    edition_id: UUID
    volume: str | None = None
    page_or_folio: str
    width: int | None = None
    height: int | None = None
    asset: AssetRef | None = None
    figures: list[FigureResponse] = Field(default_factory=list)


class HealthResponse(APIModel):
    status: str
    version: str
    database: str
    request_id: str


class ProviderStatus(APIModel):
    name: str
    provider: str
    model: str
    version: str
    available: bool
    dimension: int | None = None
    detail: str | None = None


class CapabilitiesResponse(APIModel):
    search_types: list[str]
    verification_states: list[VerificationState]
    evidence_states: list[EvidenceState]
    providers: list[ProviderStatus]
    upload_limits: dict[str, int]


class SearchFilters(APIModel):
    book_ids: list[UUID] = Field(default_factory=list, max_length=50)
    edition_ids: list[UUID] = Field(default_factory=list, max_length=50)


class TextSearchRequest(APIModel):
    query: str = Field(min_length=1, max_length=1000)
    top_k: int = Field(default=10, ge=1, le=50)
    filters: SearchFilters = Field(default_factory=SearchFilters)


class ImageQuerySummary(APIModel):
    filename: str | None = None
    mime_type: str
    byte_size: int


class ImageSearchRequest(APIModel):
    """Metadata portion of a multipart image search request.

    The binary ``file`` field is represented by FastAPI's ``UploadFile`` in
    the route; this schema remains useful for clients and OpenAPI examples.
    """

    top_k: int = Field(default=10, ge=1, le=50)
    filters: SearchFilters = Field(default_factory=SearchFilters)


class BBox(APIModel):
    x: float = Field(ge=0.0, le=1.0)
    y: float = Field(ge=0.0, le=1.0)
    width: float = Field(gt=0.0, le=1.0)
    height: float = Field(gt=0.0, le=1.0)

    @model_validator(mode="after")
    def validate_finite(self) -> BBox:
        if not all(math.isfinite(value) for value in (self.x, self.y, self.width, self.height)):
            raise ValueError("bbox 坐标必须是有限数")
        if self.x + self.width > 1.0 or self.y + self.height > 1.0:
            raise ValueError("bbox 范围超出页面")
        return self


class RegionSearchRequest(APIModel):
    page_id: UUID | None = None
    figure_id: UUID | None = None
    bbox: BBox
    coordinate_space: str = Field(default="normalized", pattern="^normalized$")
    top_k: int = Field(default=10, ge=1, le=50)
    filters: SearchFilters = Field(default_factory=SearchFilters)

    @model_validator(mode="after")
    def validate_source(self) -> RegionSearchRequest:
        if bool(self.page_id) == bool(self.figure_id):
            raise ValueError("page_id 与 figure_id 必须且只能提供一个")
        return self


class CFRSummary(APIModel):
    assertions: list[FunctionalAssertionResponse] = Field(default_factory=list)
    uncertainty: float = Field(ge=0.0, le=1.0)


class ScoreComponents(APIModel):
    sv: float = 0.0
    st: float = 0.0
    sr: float = 0.0
    sf: float = 0.0
    sg: float = 0.0
    se: float = 0.0
    u_model: float = 0.0
    availability: dict[str, bool] = Field(default_factory=dict)
    reliability: dict[str, float] = Field(default_factory=dict)
    missing_modalities: list[str] = Field(default_factory=list)
    weights: dict[str, float] = Field(default_factory=dict)
    contributions: dict[str, float] = Field(default_factory=dict)


class SearchResult(APIModel):
    candidate_id: UUID
    figure_id: UUID
    source: SourceSummary
    image_ref: AssetRef | None = None
    matched_regions: list[RegionResponse] = Field(default_factory=list)
    score: float
    score_components: ScoreComponents
    cfr_summary: CFRSummary
    evidence: list[EvidenceResponse] = Field(default_factory=list)
    uncertainty: dict[str, float] = Field(default_factory=dict)
    verification_state: VerificationState


class SearchResponse(APIModel):
    search_id: UUID
    query_summary: dict[str, Any]
    results: list[SearchResult]
    latency_ms: float
    model_versions: dict[str, Any]


class CandidateResponse(SearchResult):
    search_id: UUID
    created_at: datetime


class VerificationRequest(APIModel):
    state: VerificationState
    note: str | None = Field(default=None, max_length=2000)


class VerificationResponse(APIModel):
    id: UUID
    candidate_id: UUID
    state: VerificationState
    note: str | None = None
    created_at: datetime


class IngestionJobRequest(APIModel):
    manifest_name: str = Field(min_length=1, max_length=500, pattern=r"^[A-Za-z0-9_.-]+\.json$")
    dry_run: bool = False


class IngestionJobResponse(APIModel):
    id: UUID
    manifest_name: str
    status: str
    dry_run: bool
    stats: dict[str, Any] = Field(default_factory=dict)
    error_message: str | None = None
    created_at: datetime
    updated_at: datetime
