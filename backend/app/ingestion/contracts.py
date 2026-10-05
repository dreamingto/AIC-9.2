"""Pydantic contracts for portable fixture ingestion manifests.

The contracts deliberately do not import database models. A validated
manifest is a portable, foreign-key-like data set consumed by the service
layer before persistence.
"""

from __future__ import annotations

import math
from datetime import datetime
from enum import StrEnum
from pathlib import Path, PurePosixPath
from typing import Annotated, Any, ClassVar, Literal

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, model_validator

Identifier = Annotated[
    str,
    StringConstraints(
        strip_whitespace=True,
        min_length=1,
        max_length=96,
        pattern=r"^[a-z0-9][a-z0-9_-]*$",
    ),
]
NonEmptyText = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]
Sha256 = Annotated[str, StringConstraints(pattern=r"^[0-9a-fA-F]{64}$")]
Confidence = Annotated[float, Field(ge=0.0, le=1.0)]


class StrictModel(BaseModel):
    """Reject misspelled or future unknown fields in manifests."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class EvidenceState(StrEnum):
    OBSERVED = "Observed"
    DOCUMENTED = "Documented"
    INFERRED = "Inferred"
    VERIFIED = "Verified"


class LicenseStatus(StrEnum):
    SYNTHETIC_FIXTURE = "synthetic_fixture"
    PUBLIC_DOMAIN = "public_domain"
    PERMISSION_GRANTED = "permission_granted"
    RESTRICTED = "restricted"
    UNKNOWN = "unknown"


class EvidenceKind(StrEnum):
    IMAGE = "image"
    TEXT = "text"
    METADATA = "metadata"


class FunctionalSlot(StrEnum):
    POWER_SOURCE = "power_source"
    TRANSMISSION = "transmission"
    MOTION = "motion"
    ACTION = "action"
    OBJECT = "object"
    # Backwards-compatible alias for early fixture consumers.  The canonical
    # representation follows the CFR vocabulary's separate action/object
    # slots.
    ACTION_OBJECT = "object"
    PURPOSE = "purpose"


class RelationPredicate(StrEnum):
    DRIVES = "drives"
    TRANSMITS = "transmits"
    CONNECTS = "connects"
    ACTS_ON = "acts_on"
    SUPPORTS = "supports"


class BenchmarkLabel(StrEnum):
    SAME_FUNCTION = "same_function"
    RELATED_MECHANISM = "related_mechanism"
    SIMILAR_FORM_DIFFERENT_FUNCTION = "similar_form_different_function"


class TextKind(StrEnum):
    TITLE = "title"
    CAPTION = "caption"
    CONTEXT = "context"
    OCR = "ocr"
    CORRECTED = "corrected"


class NormalizedBBox(StrictModel):
    """A finite, normalized bounding box entirely inside its source image."""

    x: float = Field(ge=0.0, le=1.0)
    y: float = Field(ge=0.0, le=1.0)
    width: float = Field(gt=0.0, le=1.0)
    height: float = Field(gt=0.0, le=1.0)

    @model_validator(mode="after")
    def validate_bounds(self) -> NormalizedBBox:
        values = (self.x, self.y, self.width, self.height)
        if not all(math.isfinite(value) for value in values):
            raise ValueError("bbox values must be finite")
        if self.x + self.width > 1.0 + 1e-9:
            raise ValueError("bbox exceeds image width")
        if self.y + self.height > 1.0 + 1e-9:
            raise ValueError("bbox exceeds image height")
        return self


class AssetRecord(StrictModel):
    asset_id: Identifier
    relative_path: NonEmptyText
    mime_type: Literal["image/png"] = "image/png"
    sha256: Sha256
    width: int = Field(gt=0, le=20_000)
    height: int = Field(gt=0, le=20_000)

    @model_validator(mode="after")
    def validate_relative_path(self) -> AssetRecord:
        if "\\" in self.relative_path:
            raise ValueError("asset paths must use '/' separators")
        path = PurePosixPath(self.relative_path)
        if path.is_absolute() or ".." in path.parts or "." in path.parts:
            raise ValueError("asset path must be a clean relative path")
        if not path.parts or path.suffix.lower() != ".png":
            raise ValueError("fixture assets must be clean relative PNG paths")
        return self


class SourceRecord(StrictModel):
    source_id: Identifier
    source_url: NonEmptyText
    source_name: NonEmptyText
    book_title: NonEmptyText
    author: NonEmptyText
    era: NonEmptyText
    edition: NonEmptyText
    volume: NonEmptyText
    page_or_folio: NonEmptyText
    license_status: LicenseStatus
    license_note: NonEmptyText
    allow_training: bool
    allow_redistribution: bool
    retrieved_at: datetime
    pipeline_version: NonEmptyText
    original_sha256: Sha256 | None = None
    source_category: Literal[
        "domestic_publication", "domestic_holding", "overseas_holding", "unspecified"
    ] = "unspecified"

    @model_validator(mode="after")
    def validate_source(self) -> SourceRecord:
        from urllib.parse import urlparse

        parsed = urlparse(self.source_url)
        if parsed.scheme not in {"http", "https", "file"} or (
            not parsed.netloc and parsed.scheme != "file"
        ):
            raise ValueError("source_url must be an absolute HTTP(S) or file URL")
        if self.retrieved_at.tzinfo is None or self.retrieved_at.utcoffset() is None:
            raise ValueError("retrieved_at must include a timezone")
        if self.license_status == LicenseStatus.UNKNOWN and (
            self.allow_training or self.allow_redistribution
        ):
            raise ValueError("unknown licenses cannot permit training or redistribution")
        if self.license_status == LicenseStatus.RESTRICTED and self.allow_redistribution:
            raise ValueError("restricted sources cannot permit redistribution")
        return self


class PageRecord(StrictModel):
    page_id: Identifier
    source_id: Identifier
    volume: NonEmptyText
    page_or_folio: NonEmptyText


class FigureRecord(StrictModel):
    figure_id: Identifier
    page_id: Identifier
    asset_id: Identifier
    title: NonEmptyText
    caption: NonEmptyText
    bbox: NormalizedBBox
    original_path: NonEmptyText


class RegionRecord(StrictModel):
    region_id: Identifier
    figure_id: Identifier
    label: NonEmptyText
    role: NonEmptyText
    bbox: NormalizedBBox
    evidence_state: Literal[EvidenceState.OBSERVED, EvidenceState.INFERRED] = EvidenceState.OBSERVED


class HumanConfirmation(StrictModel):
    confirmed: Literal[True]
    reviewer: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=200)]
    reviewed_at: datetime

    @model_validator(mode="after")
    def require_timezone(self) -> HumanConfirmation:
        if self.reviewed_at.utcoffset() is None:
            raise ValueError("human review requires timezone-aware reviewed_at")
        return self


class TranscriptionTrace(StrictModel):
    box_id: Identifier
    bbox: NormalizedBBox
    raw_text: str | None
    confirmation: HumanConfirmation


class AIRawLine(StrictModel):
    line_index: int = Field(ge=0)
    bbox: NormalizedBBox
    text: NonEmptyText
    confidence: Confidence
    reading_order: int = Field(ge=0)


class AITextTrace(StrictModel):
    origin: Literal["raw_ocr", "ai_visual_description", "ai_visual_transcription"]
    page_id: Identifier
    bbox: NormalizedBBox
    provider: NonEmptyText
    model: NonEmptyText
    version: NonEmptyText
    raw_lines: list[AIRawLine] = Field(default_factory=list)


class TextChunkRecord(StrictModel):
    text_id: Identifier
    figure_id: Identifier
    kind: TextKind
    content: NonEmptyText
    evidence_state: EvidenceState
    transcription_review: TranscriptionTrace | None = None
    ai_trace: AITextTrace | None = None


class EvidenceRecord(StrictModel):
    evidence_id: Identifier
    figure_id: Identifier
    kind: EvidenceKind
    state: EvidenceState
    source_ref: Identifier
    excerpt: str | None = Field(default=None, max_length=1_000)

    @model_validator(mode="after")
    def validate_excerpt(self) -> EvidenceRecord:
        if self.kind == EvidenceKind.TEXT and not self.excerpt:
            raise ValueError("text evidence requires an excerpt")
        return self


class FunctionalAssertionRecord(StrictModel):
    assertion_id: Identifier
    figure_id: Identifier
    slot: FunctionalSlot
    concept: NonEmptyText
    confidence: Confidence
    evidence_ids: list[Identifier] = Field(min_length=1)
    state: EvidenceState


class RelationRecord(StrictModel):
    relation_id: Identifier
    figure_id: Identifier
    subject: NonEmptyText
    predicate: RelationPredicate
    object: NonEmptyText
    confidence: Confidence
    evidence_ids: list[Identifier] = Field(min_length=1)
    state: EvidenceState


class BenchmarkPairRecord(StrictModel):
    pair_id: Identifier
    query_figure_id: Identifier
    candidate_figure_id: Identifier
    label: BenchmarkLabel
    rationale: NonEmptyText
    evidence_ids: list[Identifier] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_pair(self) -> BenchmarkPairRecord:
        if self.query_figure_id == self.candidate_figure_id:
            raise ValueError("benchmark pairs must reference two different figures")
        return self


class ManifestRecords(StrictModel):
    schema_version: Literal["1.0"] = "1.0"
    fixture_id: Identifier
    title: NonEmptyText
    description: NonEmptyText
    dataset_kind: str
    evaluation_status: Literal["not_evaluated"] = "not_evaluated"
    generated_at: datetime
    generator_version: NonEmptyText
    disclaimer: NonEmptyText
    sources: list[SourceRecord] = Field(min_length=1)
    assets: list[AssetRecord] = Field(min_length=1)
    pages: list[PageRecord] = Field(min_length=1)
    figures: list[FigureRecord] = Field(min_length=1)
    regions: list[RegionRecord] = Field(min_length=1)
    text_chunks: list[TextChunkRecord] = Field(min_length=1)
    evidence: list[EvidenceRecord] = Field(min_length=1)
    functional_assertions: list[FunctionalAssertionRecord] = Field(default_factory=list)
    relations: list[RelationRecord] = Field(default_factory=list)
    benchmark_pairs: list[BenchmarkPairRecord] = Field(default_factory=list)
    REQUIRED_COVERAGE: ClassVar[tuple[str, ...]] = ("region", "text", "evidence")

    @model_validator(mode="after")
    def validate_references(self) -> ManifestRecords:
        if self.generated_at.tzinfo is None or self.generated_at.utcoffset() is None:
            raise ValueError("generated_at must include a timezone")
        if "not_evaluated" not in self.disclaimer:
            raise ValueError("fixture disclaimer must explicitly contain 'not_evaluated'")

        collections: dict[str, list[object]] = {
            "source_id": list(self.sources),
            "asset_id": list(self.assets),
            "page_id": list(self.pages),
            "figure_id": list(self.figures),
            "region_id": list(self.regions),
            "text_id": list(self.text_chunks),
            "evidence_id": list(self.evidence),
            "assertion_id": list(self.functional_assertions),
            "relation_id": list(self.relations),
            "pair_id": list(self.benchmark_pairs),
        }
        for field_name, records in collections.items():
            values = [getattr(record, field_name) for record in records]
            if len(values) != len(set(values)):
                raise ValueError(f"duplicate {field_name} values")

        source_ids = {record.source_id for record in self.sources}
        asset_ids = {record.asset_id for record in self.assets}
        page_ids = {record.page_id for record in self.pages}
        figure_ids = {record.figure_id for record in self.figures}
        figures = {record.figure_id: record for record in self.figures}
        pages = {record.page_id: record for record in self.pages}
        chunks = {record.text_id: record for record in self.text_chunks}
        text_ids = {record.text_id for record in self.text_chunks}
        evidence_by_id = {record.evidence_id: record for record in self.evidence}

        for page in self.pages:
            self._require_reference("page.source_id", page.source_id, source_ids)
        for figure in self.figures:
            self._require_reference("figure.page_id", figure.page_id, page_ids)
            self._require_reference("figure.asset_id", figure.asset_id, asset_ids)
        asset_owners: dict[str, str] = {}
        for figure in self.figures:
            source_id = pages[figure.page_id].source_id
            previous = asset_owners.setdefault(figure.asset_id, source_id)
            if previous != source_id:
                raise ValueError("one asset cannot belong to different source licenses")
        for region in self.regions:
            self._require_reference("region.figure_id", region.figure_id, figure_ids)
        for chunk in self.text_chunks:
            self._require_reference("text_chunk.figure_id", chunk.figure_id, figure_ids)
        for item in self.evidence:
            self._require_reference("evidence.figure_id", item.figure_id, figure_ids)
            valid_refs = asset_ids if item.kind == EvidenceKind.IMAGE else text_ids
            if item.kind == EvidenceKind.METADATA:
                valid_refs = source_ids
            self._require_reference("evidence.source_ref", item.source_ref, valid_refs)
            owner = figures[item.figure_id]
            if (
                item.kind == EvidenceKind.TEXT
                and chunks[item.source_ref].figure_id != item.figure_id
            ):
                raise ValueError("text evidence belongs to a different figure")
            if item.kind == EvidenceKind.IMAGE and item.source_ref != owner.asset_id:
                raise ValueError("image evidence must reference the figure asset")
            if (
                item.kind == EvidenceKind.METADATA
                and item.source_ref != pages[owner.page_id].source_id
            ):
                raise ValueError("metadata evidence must reference the figure source")
        for assertion in self.functional_assertions:
            self._require_reference("assertion.figure_id", assertion.figure_id, figure_ids)
            self._validate_evidence_ownership(
                assertion.figure_id, assertion.evidence_ids, evidence_by_id
            )
        for relation in self.relations:
            self._require_reference("relation.figure_id", relation.figure_id, figure_ids)
            self._validate_evidence_ownership(
                relation.figure_id, relation.evidence_ids, evidence_by_id
            )

        seen_pairs: set[tuple[str, str]] = set()
        for pair in self.benchmark_pairs:
            self._require_reference("pair.query_figure_id", pair.query_figure_id, figure_ids)
            self._require_reference(
                "pair.candidate_figure_id", pair.candidate_figure_id, figure_ids
            )
            normalized_pair: tuple[str, str] = (
                min(pair.query_figure_id, pair.candidate_figure_id),
                max(pair.query_figure_id, pair.candidate_figure_id),
            )
            if normalized_pair in seen_pairs:
                raise ValueError("duplicate unordered benchmark pair")
            seen_pairs.add(normalized_pair)
            for evidence_id in pair.evidence_ids:
                self._require_reference("pair.evidence_id", evidence_id, set(evidence_by_id))

        self._validate_per_figure_coverage(figure_ids)
        return self

    @staticmethod
    def _require_reference(label: str, value: str, allowed: set[str]) -> None:
        if value not in allowed:
            raise ValueError(f"unknown {label}: {value}")

    @staticmethod
    def _validate_evidence_ownership(
        figure_id: str, evidence_ids: list[str], evidence_by_id: dict[str, EvidenceRecord]
    ) -> None:
        for evidence_id in evidence_ids:
            evidence = evidence_by_id.get(evidence_id)
            if evidence is None:
                raise ValueError(f"unknown evidence_id: {evidence_id}")
            if evidence.figure_id != figure_id:
                raise ValueError(
                    f"evidence {evidence_id} belongs to {evidence.figure_id}, not {figure_id}"
                )

    def _validate_per_figure_coverage(self, figure_ids: set[str]) -> None:
        coverage = {
            figure_id: {"region": 0, "text": 0, "evidence": 0, "assertion": 0, "relation": 0}
            for figure_id in figure_ids
        }
        for region_record in self.regions:
            coverage[region_record.figure_id]["region"] += 1
        for text_record in self.text_chunks:
            coverage[text_record.figure_id]["text"] += 1
        for evidence_record in self.evidence:
            coverage[evidence_record.figure_id]["evidence"] += 1
        for assertion_record in self.functional_assertions:
            coverage[assertion_record.figure_id]["assertion"] += 1
        for relation_record in self.relations:
            coverage[relation_record.figure_id]["relation"] += 1
        for figure_id, counts in coverage.items():
            missing = [name for name in self.REQUIRED_COVERAGE if counts[name] == 0]
            if missing:
                raise ValueError(
                    f"figure {figure_id} is missing required records: {', '.join(missing)}"
                )


class FixtureManifest(ManifestRecords):
    """Synthetic fixture keeps its original full annotation requirements."""

    dataset_kind: Literal["synthetic_fixture"] = "synthetic_fixture"
    functional_assertions: list[FunctionalAssertionRecord] = Field(min_length=1)
    relations: list[RelationRecord] = Field(min_length=1)
    benchmark_pairs: list[BenchmarkPairRecord] = Field(min_length=1)
    REQUIRED_COVERAGE: ClassVar[tuple[str, ...]] = (
        "region",
        "text",
        "evidence",
        "assertion",
        "relation",
    )


class FigureReview(StrictModel):
    figure_id: Identifier
    page_id: Identifier
    title_box_id: Identifier
    region_confirmation: HumanConfirmation
    title_confirmation: HumanConfirmation


class RealReviewAudit(StrictModel):
    review_scope: Literal["figure_extent_and_title_only"]
    snapshot_id: Identifier
    snapshot_manifest_sha256: Sha256
    annotation_sha256: Sha256
    override_sha256: Sha256
    candidate_sha256: Sha256
    scope_sha256: Sha256
    source_registry_sha256: Sha256
    figures: list[FigureReview] = Field(min_length=1)


class RealManifest(ManifestRecords):
    """Accepted scan-level geometry/transcription, without invented semantics."""

    dataset_kind: Literal["human_reviewed_real_pilot"]
    review_audit: RealReviewAudit

    @model_validator(mode="after")
    def validate_human_review(self) -> RealManifest:
        if any(c.ai_trace is not None for c in self.text_chunks):
            raise ValueError("AI traces cannot substitute independent human confirmation")
        if self.functional_assertions or self.relations or self.benchmark_pairs:
            raise ValueError("title-only real import cannot claim function/graph/relevance labels")
        if any(s.license_status == LicenseStatus.SYNTHETIC_FIXTURE for s in self.sources):
            raise ValueError("real sources cannot be synthetic fixtures")
        if any(s.original_sha256 is None for s in self.sources):
            raise ValueError("real sources require original PDF SHA-256")
        reviews = {r.figure_id: r for r in self.review_audit.figures}
        if len(reviews) != len(self.review_audit.figures) or set(reviews) != {
            f.figure_id for f in self.figures
        }:
            raise ValueError("real figures require unique complete human review audit")
        page_assets: dict[str, str] = {}
        for figure in self.figures:
            review = reviews[figure.figure_id]
            if review.page_id != figure.page_id:
                raise ValueError("figure review page mismatch")
            if page_assets.setdefault(figure.page_id, figure.asset_id) != figure.asset_id:
                raise ValueError("real figures on one page must share its scan asset")
            titles = [c for c in self.text_chunks if c.figure_id == figure.figure_id]
            if len(titles) != 1 or titles[0].kind != TextKind.TITLE:
                raise ValueError("title-only import requires exactly one title chunk per figure")
            title = titles[0]
            trace = title.transcription_review
            if (
                trace is None
                or trace.box_id != review.title_box_id
                or trace.confirmation != review.title_confirmation
                or title.content != figure.title
                or title.content != figure.caption
                or title.evidence_state != EvidenceState.DOCUMENTED
            ):
                raise ValueError("real title must retain its confirmed scan transcription")
        if any(e.state == EvidenceState.VERIFIED for e in self.evidence):
            raise ValueError("transcription review must not verify historical evidence claims")
        return self


class AIPageAudit(StrictModel):
    page_id: Identifier
    source_id: Identifier
    image_sha256: Sha256


class AIFigureAudit(StrictModel):
    figure_id: Identifier
    page_id: Identifier
    bbox: NormalizedBBox
    title_origin: Literal["ai_visual_description", "ai_visual_transcription"]
    visual_checked: Literal[True]
    note: NonEmptyText


class AIReviewAudit(StrictModel):
    review_origin: Literal["ai_assisted"] = "ai_assisted"
    human_review: Literal[False] = False
    human_review_status: Literal["skipped_by_user_for_competition"]
    independent_ground_truth: Literal[False] = False
    source_registry_sha256: Sha256
    inventory_sha256: Sha256
    raw_ocr_sha256: Sha256
    selection_sha256: Sha256
    pages: list[AIPageAudit] = Field(min_length=1)
    figures: list[AIFigureAudit] = Field(min_length=1)


class AIRealManifest(ManifestRecords):
    """Competition demo input, kept separate from human evaluation truth."""

    dataset_kind: Literal["ai_assisted_real_pilot"]
    ai_audit: AIReviewAudit

    @model_validator(mode="after")
    def validate_ai_origin(self) -> AIRealManifest:
        if self.functional_assertions or self.relations or self.benchmark_pairs:
            raise ValueError("AI scene import cannot claim independent function/graph/qrels labels")
        if any(
            s.original_sha256 is None or s.license_status == LicenseStatus.SYNTHETIC_FIXTURE
            for s in self.sources
        ):
            raise ValueError("AI real sources require original PDF hashes and real licenses")
        audits = {f.figure_id: f for f in self.ai_audit.figures}
        pages = {p.page_id: p for p in self.pages}
        assets = {a.asset_id: a for a in self.assets}
        page_audits = {p.page_id: p for p in self.ai_audit.pages}
        if len(audits) != len(self.ai_audit.figures) or set(audits) != {
            f.figure_id for f in self.figures
        }:
            raise ValueError("AI figures require complete unique origin audit")
        if len(page_audits) != len(self.ai_audit.pages) or set(page_audits) != set(pages):
            raise ValueError("AI pages require complete unique origin audit")
        page_assets: dict[str, str] = {}
        for figure in self.figures:
            audit = audits[figure.figure_id]
            page = pages[figure.page_id]
            page_audit = page_audits[figure.page_id]
            if audit.page_id != figure.page_id or audit.bbox != figure.bbox:
                raise ValueError("AI figure extent differs from visual audit")
            if (
                page_audit.source_id != page.source_id
                or page_audit.image_sha256 != assets[figure.asset_id].sha256
                or page_assets.setdefault(figure.page_id, figure.asset_id) != figure.asset_id
            ):
                raise ValueError("AI page asset/source/hash mismatch")
            titles = [c for c in self.text_chunks if c.figure_id == figure.figure_id
                      and c.kind == TextKind.TITLE]
            if len(titles) != 1 or titles[0].content != figure.title:
                raise ValueError("AI figure requires exactly one traced title")
            if titles[0].ai_trace is None or titles[0].ai_trace.origin != audit.title_origin:
                raise ValueError("AI title origin mismatch")
        for chunk in self.text_chunks:
            trace = chunk.ai_trace
            if chunk.transcription_review is not None or chunk.kind == TextKind.CORRECTED:
                raise ValueError("AI text cannot impersonate human corrected text")
            if trace is None or chunk.evidence_state != EvidenceState.INFERRED:
                raise ValueError("all AI text requires Inferred state and trace")
            owner = next(f for f in self.figures if f.figure_id == chunk.figure_id)
            if trace.page_id != owner.page_id:
                raise ValueError("AI text trace belongs to another page")
            if trace.origin == "raw_ocr":
                indexes = [line.line_index for line in trace.raw_lines]
                if (
                    chunk.kind != TextKind.OCR or not indexes or len(indexes) != len(set(indexes))
                    or chunk.content != "\n".join(line.text for line in trace.raw_lines)
                ):
                    raise ValueError("raw OCR must preserve exact traced line content")
            elif trace.raw_lines:
                raise ValueError("visual descriptions must not be represented as raw OCR")
        if any(r.evidence_state != EvidenceState.INFERRED for r in self.regions):
            raise ValueError("AI region geometry must remain Inferred")
        if any(
            e.state != {
                EvidenceKind.IMAGE: EvidenceState.OBSERVED,
                EvidenceKind.TEXT: EvidenceState.INFERRED,
                EvidenceKind.METADATA: EvidenceState.DOCUMENTED,
            }[e.kind]
            for e in self.evidence
        ):
            raise ValueError("AI evidence states must distinguish scan/text/catalog")
        return self


class ValidatedFixture(StrictModel):
    """Portable return value after schema and on-disk validation."""

    manifest: FixtureManifest | RealManifest | AIRealManifest
    manifest_path: Path
    asset_paths: dict[str, Path]
    counts: dict[str, int]

    @classmethod
    def from_manifest(
        cls,
        manifest: FixtureManifest | RealManifest | AIRealManifest,
        manifest_path: Path,
        asset_paths: dict[str, Path],
    ) -> ValidatedFixture:
        return cls(
            manifest=manifest,
            manifest_path=manifest_path,
            asset_paths=asset_paths,
            counts={
                "sources": len(manifest.sources),
                "assets": len(manifest.assets),
                "pages": len(manifest.pages),
                "figures": len(manifest.figures),
                "regions": len(manifest.regions),
                "text_chunks": len(manifest.text_chunks),
                "evidence": len(manifest.evidence),
                "functional_assertions": len(manifest.functional_assertions),
                "relations": len(manifest.relations),
                "benchmark_pairs": len(manifest.benchmark_pairs),
            },
        )

    def normalized_records(self) -> dict[str, list[dict[str, Any]]]:
        """Return JSON-safe, persistence-agnostic record groups.

        The ingestion service can map these groups to SQLAlchemy entities (or
        another store) without importing database models here.  Enum values
        and datetimes are serialized in their wire representation, while
        verified on-disk paths remain available through ``asset_paths``.
        """

        payload = self.manifest.model_dump(mode="python")

        def json_safe(value: Any) -> Any:
            if isinstance(value, datetime):
                # Keep an explicit offset in normalized records.  This is
                # easier for importers and humans to audit than a bare ``Z``.
                return value.isoformat()
            if isinstance(value, dict):
                return {str(key): json_safe(item) for key, item in value.items()}
            if isinstance(value, list):
                return [json_safe(item) for item in value]
            if isinstance(value, tuple):
                return [json_safe(item) for item in value]
            if isinstance(value, StrEnum):
                return value.value
            return value

        payload = json_safe(payload)
        group_names = (
            "sources",
            "assets",
            "pages",
            "figures",
            "regions",
            "text_chunks",
            "evidence",
            "functional_assertions",
            "relations",
            "benchmark_pairs",
        )
        return {name: [dict(record) for record in payload[name]] for name in group_names}
