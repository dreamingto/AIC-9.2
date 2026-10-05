from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from uuid import UUID, uuid4

from pgvector.sqlalchemy import Vector
from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    Uuid,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


def new_uuid() -> UUID:
    return uuid4()


def now_utc() -> datetime:
    return datetime.now(UTC)


class Timestamped:
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=now_utc, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=now_utc, onupdate=now_utc, nullable=False
    )


class Book(Timestamped, Base):
    __tablename__ = "books"

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=new_uuid)
    title: Mapped[str] = mapped_column(String(500), nullable=False, index=True)
    author: Mapped[str | None] = mapped_column(String(300))
    era: Mapped[str | None] = mapped_column(String(100))
    description: Mapped[str | None] = mapped_column(Text)

    editions: Mapped[list[Edition]] = relationship(
        back_populates="book", cascade="all, delete-orphan"
    )


class Edition(Timestamped, Base):
    __tablename__ = "editions"

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=new_uuid)
    book_id: Mapped[UUID] = mapped_column(
        ForeignKey("books.id", ondelete="CASCADE"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(500), nullable=False)
    edition_note: Mapped[str | None] = mapped_column(Text)
    source_url: Mapped[str | None] = mapped_column(String(2000))
    source_name: Mapped[str | None] = mapped_column(String(500))
    license_status: Mapped[str] = mapped_column(String(100), nullable=False, default="unknown")
    license_note: Mapped[str | None] = mapped_column(Text)
    allow_training: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    allow_redistribution: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    retrieved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    sha256: Mapped[str | None] = mapped_column(String(64))
    original_path: Mapped[str | None] = mapped_column(String(2000))
    pipeline_version: Mapped[str | None] = mapped_column(String(100))

    book: Mapped[Book] = relationship(back_populates="editions")
    pages: Mapped[list[Page]] = relationship(back_populates="edition", cascade="all, delete-orphan")


class Asset(Timestamped, Base):
    __tablename__ = "assets"

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=new_uuid)
    relative_path: Mapped[str] = mapped_column(String(2000), nullable=False, unique=True)
    mime_type: Mapped[str] = mapped_column(String(100), nullable=False)
    byte_size: Mapped[int] = mapped_column(Integer, nullable=False)
    width: Mapped[int | None] = mapped_column(Integer)
    height: Mapped[int | None] = mapped_column(Integer)
    source_url: Mapped[str | None] = mapped_column(String(2000))
    source_name: Mapped[str | None] = mapped_column(String(500))
    license_status: Mapped[str] = mapped_column(String(100), nullable=False, default="unknown")
    license_note: Mapped[str | None] = mapped_column(Text)
    allow_training: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    allow_redistribution: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    retrieved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    sha256: Mapped[str | None] = mapped_column(String(64))
    pipeline_version: Mapped[str | None] = mapped_column(String(100))


class Page(Timestamped, Base):
    __tablename__ = "pages"

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=new_uuid)
    edition_id: Mapped[UUID] = mapped_column(
        ForeignKey("editions.id", ondelete="CASCADE"), nullable=False, index=True
    )
    volume: Mapped[str | None] = mapped_column(String(100))
    page_or_folio: Mapped[str] = mapped_column(String(100), nullable=False)
    asset_id: Mapped[UUID | None] = mapped_column(ForeignKey("assets.id", ondelete="SET NULL"))
    width: Mapped[int | None] = mapped_column(Integer)
    height: Mapped[int | None] = mapped_column(Integer)
    provenance: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)

    edition: Mapped[Edition] = relationship(back_populates="pages")
    asset: Mapped[Asset | None] = relationship()
    figures: Mapped[list[Figure]] = relationship(
        back_populates="page", cascade="all, delete-orphan"
    )


class Figure(Timestamped, Base):
    __tablename__ = "figures"

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=new_uuid)
    page_id: Mapped[UUID] = mapped_column(
        ForeignKey("pages.id", ondelete="CASCADE"), nullable=False, index=True
    )
    title: Mapped[str | None] = mapped_column(String(500))
    asset_id: Mapped[UUID | None] = mapped_column(ForeignKey("assets.id", ondelete="SET NULL"))
    bbox_x: Mapped[float | None] = mapped_column(Float)
    bbox_y: Mapped[float | None] = mapped_column(Float)
    bbox_width: Mapped[float | None] = mapped_column(Float)
    bbox_height: Mapped[float | None] = mapped_column(Float)
    provenance: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)

    page: Mapped[Page] = relationship(back_populates="figures")
    asset: Mapped[Asset | None] = relationship()
    regions: Mapped[list[Region]] = relationship(
        back_populates="figure", cascade="all, delete-orphan"
    )
    text_chunks: Mapped[list[TextChunk]] = relationship(
        back_populates="figure", cascade="all, delete-orphan"
    )
    assertions: Mapped[list[FunctionalAssertion]] = relationship(
        back_populates="figure", cascade="all, delete-orphan"
    )
    relations: Mapped[list[Relation]] = relationship(
        back_populates="figure", cascade="all, delete-orphan"
    )
    evidences: Mapped[list[Evidence]] = relationship(
        back_populates="figure", cascade="all, delete-orphan"
    )


class Region(Timestamped, Base):
    __tablename__ = "regions"

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=new_uuid)
    figure_id: Mapped[UUID] = mapped_column(
        ForeignKey("figures.id", ondelete="CASCADE"), nullable=False, index=True
    )
    label: Mapped[str | None] = mapped_column(String(300))
    x: Mapped[float] = mapped_column(Float, nullable=False)
    y: Mapped[float] = mapped_column(Float, nullable=False)
    width: Mapped[float] = mapped_column(Float, nullable=False)
    height: Mapped[float] = mapped_column(Float, nullable=False)
    provenance: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)

    figure: Mapped[Figure] = relationship(back_populates="regions")


class TextChunk(Timestamped, Base):
    __tablename__ = "text_chunks"

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=new_uuid)
    figure_id: Mapped[UUID] = mapped_column(
        ForeignKey("figures.id", ondelete="CASCADE"), nullable=False, index=True
    )
    chunk_type: Mapped[str] = mapped_column(String(50), nullable=False, default="context")
    text: Mapped[str] = mapped_column(Text, nullable=False)
    corrected_text: Mapped[str | None] = mapped_column(Text)
    source_pointer: Mapped[str | None] = mapped_column(String(1000))
    state: Mapped[str] = mapped_column(String(30), nullable=False, default="Documented")

    figure: Mapped[Figure] = relationship(back_populates="text_chunks")


class FunctionalAssertion(Timestamped, Base):
    __tablename__ = "functional_assertions"

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=new_uuid)
    figure_id: Mapped[UUID] = mapped_column(
        ForeignKey("figures.id", ondelete="CASCADE"), nullable=False, index=True
    )
    slot: Mapped[str] = mapped_column(String(100), nullable=False)
    concept: Mapped[str] = mapped_column(String(300), nullable=False)
    confidence: Mapped[float] = mapped_column(Float, nullable=False)
    state: Mapped[str] = mapped_column(String(30), nullable=False, default="Inferred")
    evidence_pointer: Mapped[str | None] = mapped_column(String(1000))

    figure: Mapped[Figure] = relationship(back_populates="assertions")


class Relation(Timestamped, Base):
    __tablename__ = "relations"

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=new_uuid)
    figure_id: Mapped[UUID] = mapped_column(
        ForeignKey("figures.id", ondelete="CASCADE"), nullable=False, index=True
    )
    predicate: Mapped[str] = mapped_column(String(100), nullable=False)
    subject: Mapped[str] = mapped_column(String(300), nullable=False)
    object: Mapped[str] = mapped_column(String(300), nullable=False)
    weight: Mapped[float] = mapped_column(Float, nullable=False, default=1.0)
    confidence: Mapped[float] = mapped_column(Float, nullable=False, default=1.0)

    figure: Mapped[Figure] = relationship(back_populates="relations")


class Evidence(Timestamped, Base):
    __tablename__ = "evidences"

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=new_uuid)
    figure_id: Mapped[UUID] = mapped_column(
        ForeignKey("figures.id", ondelete="CASCADE"), nullable=False, index=True
    )
    evidence_type: Mapped[str] = mapped_column(String(50), nullable=False)
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="Inferred")
    content: Mapped[str] = mapped_column(Text, nullable=False)
    pointer: Mapped[str | None] = mapped_column(String(1000))
    support_confidence: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    source_weight: Mapped[float] = mapped_column(Float, nullable=False, default=1.0)

    figure: Mapped[Figure] = relationship(back_populates="evidences")


class EmbeddingRecord(Timestamped, Base):
    __tablename__ = "embedding_records"

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=new_uuid)
    entity_type: Mapped[str] = mapped_column(String(50), nullable=False)
    entity_id: Mapped[UUID] = mapped_column(Uuid, nullable=False, index=True)
    modality: Mapped[str] = mapped_column(String(50), nullable=False)
    vector: Mapped[list[float]] = mapped_column(Vector(), nullable=False)
    dimension: Mapped[int] = mapped_column(Integer, nullable=False)
    provider: Mapped[str] = mapped_column(String(200), nullable=False)
    model: Mapped[str] = mapped_column(String(200), nullable=False)
    version: Mapped[str] = mapped_column(String(100), nullable=False)
    preprocessing_hash: Mapped[str] = mapped_column(String(64), nullable=False)

    __table_args__ = (
        Index("ix_embedding_entity_modality", "entity_type", "entity_id", "modality"),
        Index(
            "ix_embedding_model_space",
            "entity_type",
            "entity_id",
            "modality",
            "provider",
            "model",
            "version",
            "dimension",
            "preprocessing_hash",
            unique=True,
        ),
    )


class SearchSession(Timestamped, Base):
    __tablename__ = "search_sessions"

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=new_uuid)
    search_type: Mapped[str] = mapped_column(String(30), nullable=False)
    query_summary: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    config: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    model_versions: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    latency_ms: Mapped[float | None] = mapped_column(Float)
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="completed")
    error_code: Mapped[str | None] = mapped_column(String(100))

    candidates: Mapped[list[AssociationCandidate]] = relationship(
        back_populates="search_session", cascade="all, delete-orphan"
    )


class AssociationCandidate(Timestamped, Base):
    __tablename__ = "association_candidates"

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=new_uuid)
    search_session_id: Mapped[UUID] = mapped_column(
        ForeignKey("search_sessions.id", ondelete="CASCADE"), nullable=False, index=True
    )
    figure_id: Mapped[UUID] = mapped_column(
        ForeignKey("figures.id", ondelete="CASCADE"), nullable=False, index=True
    )
    rank: Mapped[int] = mapped_column(Integer, nullable=False)
    score: Mapped[float] = mapped_column(Float, nullable=False)
    score_components: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    cfr_summary: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    evidence_summary: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    uncertainty: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    verification_state: Mapped[str] = mapped_column(String(40), nullable=False, default="pending")

    search_session: Mapped[SearchSession] = relationship(back_populates="candidates")
    figure: Mapped[Figure] = relationship()
    verifications: Mapped[list[Verification]] = relationship(
        back_populates="candidate", cascade="all, delete-orphan"
    )


class Verification(Timestamped, Base):
    __tablename__ = "verifications"

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=new_uuid)
    candidate_id: Mapped[UUID] = mapped_column(
        ForeignKey("association_candidates.id", ondelete="CASCADE"), nullable=False, index=True
    )
    state: Mapped[str] = mapped_column(String(40), nullable=False)
    note: Mapped[str | None] = mapped_column(Text)

    candidate: Mapped[AssociationCandidate] = relationship(back_populates="verifications")


class IngestionJob(Timestamped, Base):
    __tablename__ = "ingestion_jobs"

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=new_uuid)
    manifest_name: Mapped[str] = mapped_column(String(500), nullable=False, index=True)
    manifest_sha256: Mapped[str | None] = mapped_column(String(64))
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="queued")
    dry_run: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    stats: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    error_message: Mapped[str | None] = mapped_column(Text)
