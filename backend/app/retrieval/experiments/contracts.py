from __future__ import annotations

from typing import Literal

from pydantic import Field, model_validator

from app.ingestion.contracts import Identifier, NonEmptyText, Sha256, StrictModel
from app.schemas.common import BBox

Method = Literal[
    "bm25",
    "bge",
    "chinese_clip",
    "hybrid",
    "hybrid_no_region",
    "eafr_current",
    "eafr_drafts",
    "eafr_drafts_no_evidence",
]
METHODS: tuple[Method, ...] = (
    "bm25",
    "bge",
    "chinese_clip",
    "hybrid",
    "hybrid_no_region",
    "eafr_current",
    "eafr_drafts",
    "eafr_drafts_no_evidence",
)


class FixedQuery(StrictModel):
    id: Identifier
    kind: Literal["text", "image", "region"]
    category: NonEmptyText
    purpose: NonEmptyText
    text: NonEmptyText | None = None
    source_figure_key: Identifier | None = None
    bbox: BBox | None = None
    exclude_source: Literal[True] = True
    relevance_labels: None = None

    @model_validator(mode="after")
    def validate_input(self) -> FixedQuery:
        if self.kind == "text":
            if self.text is None or self.source_figure_key is not None or self.bbox is not None:
                raise ValueError("text query requires text only")
        elif self.source_figure_key is None or self.text is not None:
            raise ValueError("visual query requires a source figure, not a generated caption")
        elif (self.kind == "region") != (self.bbox is not None):
            raise ValueError("region requires bbox; image uses the figure extent")
        return self


class QueryProtocol(StrictModel):
    schema_version: Literal["1.0"]
    protocol_id: Identifier
    manifest_name: str = Field(pattern=r"^ai-real-[A-Za-z0-9_.-]+\.json$")
    manifest_sha256: Sha256
    dataset_kind: Literal["ai_assisted_real_pilot"]
    evaluation_status: Literal["not_evaluated"]
    independent_ground_truth: Literal[False]
    disclaimer: NonEmptyText
    top_k: int = Field(ge=1, le=50)
    warm_repeats: int = Field(ge=1, le=10)
    queries: list[FixedQuery] = Field(min_length=1, max_length=100)

    @model_validator(mode="after")
    def unique_queries(self) -> QueryProtocol:
        if len({q.id for q in self.queries}) != len(self.queries):
            raise ValueError("duplicate query ID")
        return self


class DraftSupport(StrictModel):
    kind: Literal["scan_region", "ai_visual_description", "ai_visual_transcription", "raw_ocr"]
    reference_id: Identifier
    quote: NonEmptyText | None = None
    note: NonEmptyText

    @model_validator(mode="after")
    def validate_quote(self) -> DraftSupport:
        if (self.kind == "scan_region") != (self.quote is None):
            raise ValueError("scan support has no quotation; text support requires an exact quote")
        return self


class FunctionDraft(StrictModel):
    slot: Literal["power_source", "motion", "transmission", "action", "object", "purpose"]
    concept: Identifier
    label: NonEmptyText
    rationale: NonEmptyText
    supports: list[DraftSupport]
    state: Literal["Inferred"] = "Inferred"
    confidence: None = None

    @model_validator(mode="after")
    def check_support(self) -> FunctionDraft:
        if self.concept != "unknown" and not self.supports:
            raise ValueError("non-unknown function draft needs evidence")
        if self.concept == "unknown" and self.supports:
            raise ValueError("unknown retains a reason, not invented evidence")
        return self


class RelationDraft(StrictModel):
    subject: NonEmptyText
    predicate: NonEmptyText
    object: NonEmptyText
    rationale: NonEmptyText
    supports: list[DraftSupport] = Field(min_length=1)
    state: Literal["Inferred"] = "Inferred"
    confidence: None = None
    eligible_for_graph_rerank: Literal[False] = False


class FigureDraft(StrictModel):
    figure_key: Identifier
    case_id: Identifier
    functions: list[FunctionDraft] = Field(min_length=1)
    relations: list[RelationDraft]
    unresolved: list[NonEmptyText] = Field(min_length=1)

    @model_validator(mode="after")
    def unique_slots(self) -> FigureDraft:
        if len({f.slot for f in self.functions}) != len(self.functions):
            raise ValueError("one draft concept per slot in this pilot")
        return self


class EvidencePlan(StrictModel):
    schema_version: Literal["1.0"]
    plan_id: Identifier
    review_origin: Literal["ai_assisted"]
    evaluation_status: Literal["not_evaluated"]
    independent_ground_truth: Literal[False]
    confidence_policy: Literal["uncalibrated_null"]
    disclaimer: NonEmptyText
    figures: list[FigureDraft] = Field(min_length=1)

    @model_validator(mode="after")
    def unique_figures(self) -> EvidencePlan:
        if len({f.figure_key for f in self.figures}) != len(self.figures):
            raise ValueError("duplicate draft figure")
        return self
