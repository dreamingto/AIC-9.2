"""Create the initial evidence-aware retrieval schema.

The migration is intentionally explicit.  ``Base.metadata.create_all`` is not
used here so that a fresh database and a future downgrade remain auditable.
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from pgvector.sqlalchemy import Vector

revision = "0001_initial"
down_revision = None
branch_labels = None
depends_on = None


def _timestamps() -> tuple[sa.Column, sa.Column]:
    return (
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")

    op.create_table(
        "books",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("title", sa.String(500), nullable=False),
        sa.Column("author", sa.String(300)),
        sa.Column("era", sa.String(100)),
        sa.Column("description", sa.Text()),
        *_timestamps(),
    )
    op.create_index("ix_books_title", "books", ["title"])

    op.create_table(
        "editions",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("book_id", sa.Uuid(), sa.ForeignKey("books.id", ondelete="CASCADE"), nullable=False),
        sa.Column("name", sa.String(500), nullable=False),
        sa.Column("edition_note", sa.Text()),
        sa.Column("source_url", sa.String(2000)),
        sa.Column("source_name", sa.String(500)),
        sa.Column("license_status", sa.String(100), nullable=False, server_default="unknown"),
        sa.Column("license_note", sa.Text()),
        sa.Column("allow_training", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("allow_redistribution", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("retrieved_at", sa.DateTime(timezone=True)),
        sa.Column("sha256", sa.String(64)),
        sa.Column("original_path", sa.String(2000)),
        sa.Column("pipeline_version", sa.String(100)),
        *_timestamps(),
    )
    op.create_index("ix_editions_book_id", "editions", ["book_id"])

    op.create_table(
        "assets",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("relative_path", sa.String(2000), nullable=False, unique=True),
        sa.Column("mime_type", sa.String(100), nullable=False),
        sa.Column("byte_size", sa.Integer(), nullable=False),
        sa.Column("width", sa.Integer()),
        sa.Column("height", sa.Integer()),
        sa.Column("source_url", sa.String(2000)),
        sa.Column("source_name", sa.String(500)),
        sa.Column("license_status", sa.String(100), nullable=False, server_default="unknown"),
        sa.Column("license_note", sa.Text()),
        sa.Column("allow_training", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("allow_redistribution", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("retrieved_at", sa.DateTime(timezone=True)),
        sa.Column("sha256", sa.String(64)),
        sa.Column("pipeline_version", sa.String(100)),
        *_timestamps(),
    )

    op.create_table(
        "pages",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("edition_id", sa.Uuid(), sa.ForeignKey("editions.id", ondelete="CASCADE"), nullable=False),
        sa.Column("volume", sa.String(100)),
        sa.Column("page_or_folio", sa.String(100), nullable=False),
        sa.Column("asset_id", sa.Uuid(), sa.ForeignKey("assets.id", ondelete="SET NULL")),
        sa.Column("width", sa.Integer()),
        sa.Column("height", sa.Integer()),
        sa.Column("provenance", sa.JSON(), nullable=False, server_default=sa.text("'{}'::json")),
        *_timestamps(),
    )
    op.create_index("ix_pages_edition_id", "pages", ["edition_id"])

    op.create_table(
        "figures",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("page_id", sa.Uuid(), sa.ForeignKey("pages.id", ondelete="CASCADE"), nullable=False),
        sa.Column("title", sa.String(500)),
        sa.Column("asset_id", sa.Uuid(), sa.ForeignKey("assets.id", ondelete="SET NULL")),
        sa.Column("bbox_x", sa.Float()),
        sa.Column("bbox_y", sa.Float()),
        sa.Column("bbox_width", sa.Float()),
        sa.Column("bbox_height", sa.Float()),
        sa.Column("provenance", sa.JSON(), nullable=False, server_default=sa.text("'{}'::json")),
        *_timestamps(),
    )
    op.create_index("ix_figures_page_id", "figures", ["page_id"])

    op.create_table(
        "regions",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("figure_id", sa.Uuid(), sa.ForeignKey("figures.id", ondelete="CASCADE"), nullable=False),
        sa.Column("label", sa.String(300)),
        sa.Column("x", sa.Float(), nullable=False),
        sa.Column("y", sa.Float(), nullable=False),
        sa.Column("width", sa.Float(), nullable=False),
        sa.Column("height", sa.Float(), nullable=False),
        sa.Column("provenance", sa.JSON(), nullable=False, server_default=sa.text("'{}'::json")),
        *_timestamps(),
    )
    op.create_index("ix_regions_figure_id", "regions", ["figure_id"])

    op.create_table(
        "text_chunks",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("figure_id", sa.Uuid(), sa.ForeignKey("figures.id", ondelete="CASCADE"), nullable=False),
        sa.Column("chunk_type", sa.String(50), nullable=False, server_default="context"),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("corrected_text", sa.Text()),
        sa.Column("source_pointer", sa.String(1000)),
        sa.Column("state", sa.String(30), nullable=False, server_default="Documented"),
        *_timestamps(),
    )
    op.create_index("ix_text_chunks_figure_id", "text_chunks", ["figure_id"])

    op.create_table(
        "functional_assertions",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("figure_id", sa.Uuid(), sa.ForeignKey("figures.id", ondelete="CASCADE"), nullable=False),
        sa.Column("slot", sa.String(100), nullable=False),
        sa.Column("concept", sa.String(300), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=False),
        sa.Column("state", sa.String(30), nullable=False, server_default="Inferred"),
        sa.Column("evidence_pointer", sa.String(1000)),
        *_timestamps(),
    )
    op.create_index("ix_functional_assertions_figure_id", "functional_assertions", ["figure_id"])

    op.create_table(
        "relations",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("figure_id", sa.Uuid(), sa.ForeignKey("figures.id", ondelete="CASCADE"), nullable=False),
        sa.Column("predicate", sa.String(100), nullable=False),
        sa.Column("subject", sa.String(300), nullable=False),
        sa.Column("object", sa.String(300), nullable=False),
        sa.Column("weight", sa.Float(), nullable=False, server_default="1.0"),
        sa.Column("confidence", sa.Float(), nullable=False, server_default="1.0"),
        *_timestamps(),
    )
    op.create_index("ix_relations_figure_id", "relations", ["figure_id"])

    op.create_table(
        "evidences",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("figure_id", sa.Uuid(), sa.ForeignKey("figures.id", ondelete="CASCADE"), nullable=False),
        sa.Column("evidence_type", sa.String(50), nullable=False),
        sa.Column("status", sa.String(30), nullable=False, server_default="Inferred"),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("pointer", sa.String(1000)),
        sa.Column("support_confidence", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("source_weight", sa.Float(), nullable=False, server_default="1.0"),
        *_timestamps(),
    )
    op.create_index("ix_evidences_figure_id", "evidences", ["figure_id"])

    op.create_table(
        "embedding_records",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("entity_type", sa.String(50), nullable=False),
        sa.Column("entity_id", sa.Uuid(), nullable=False),
        sa.Column("modality", sa.String(50), nullable=False),
        sa.Column("vector", Vector(), nullable=False),
        sa.Column("dimension", sa.Integer(), nullable=False),
        sa.Column("provider", sa.String(200), nullable=False),
        sa.Column("model", sa.String(200), nullable=False),
        sa.Column("version", sa.String(100), nullable=False),
        sa.Column("preprocessing_hash", sa.String(64), nullable=False),
        *_timestamps(),
    )
    op.create_index("ix_embedding_records_entity_id", "embedding_records", ["entity_id"])
    op.create_index("ix_embedding_entity_modality", "embedding_records", ["entity_type", "entity_id", "modality"], unique=True)

    op.create_table(
        "search_sessions",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("search_type", sa.String(30), nullable=False),
        sa.Column("query_summary", sa.JSON(), nullable=False, server_default=sa.text("'{}'::json")),
        sa.Column("config", sa.JSON(), nullable=False, server_default=sa.text("'{}'::json")),
        sa.Column("model_versions", sa.JSON(), nullable=False, server_default=sa.text("'{}'::json")),
        sa.Column("latency_ms", sa.Float()),
        sa.Column("status", sa.String(30), nullable=False, server_default="completed"),
        sa.Column("error_code", sa.String(100)),
        *_timestamps(),
    )

    op.create_table(
        "association_candidates",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("search_session_id", sa.Uuid(), sa.ForeignKey("search_sessions.id", ondelete="CASCADE"), nullable=False),
        sa.Column("figure_id", sa.Uuid(), sa.ForeignKey("figures.id", ondelete="CASCADE"), nullable=False),
        sa.Column("rank", sa.Integer(), nullable=False),
        sa.Column("score", sa.Float(), nullable=False),
        sa.Column("score_components", sa.JSON(), nullable=False, server_default=sa.text("'{}'::json")),
        sa.Column("cfr_summary", sa.JSON(), nullable=False, server_default=sa.text("'{}'::json")),
        sa.Column("evidence_summary", sa.JSON(), nullable=False, server_default=sa.text("'{}'::json")),
        sa.Column("uncertainty", sa.JSON(), nullable=False, server_default=sa.text("'{}'::json")),
        sa.Column("verification_state", sa.String(40), nullable=False, server_default="pending"),
        *_timestamps(),
    )
    op.create_index("ix_association_candidates_search_session_id", "association_candidates", ["search_session_id"])
    op.create_index("ix_association_candidates_figure_id", "association_candidates", ["figure_id"])

    op.create_table(
        "verifications",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("candidate_id", sa.Uuid(), sa.ForeignKey("association_candidates.id", ondelete="CASCADE"), nullable=False),
        sa.Column("state", sa.String(40), nullable=False),
        sa.Column("note", sa.Text()),
        *_timestamps(),
    )
    op.create_index("ix_verifications_candidate_id", "verifications", ["candidate_id"])

    op.create_table(
        "ingestion_jobs",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("manifest_name", sa.String(500), nullable=False),
        sa.Column("manifest_sha256", sa.String(64)),
        sa.Column("status", sa.String(30), nullable=False, server_default="queued"),
        sa.Column("dry_run", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("stats", sa.JSON(), nullable=False, server_default=sa.text("'{}'::json")),
        sa.Column("error_message", sa.Text()),
        *_timestamps(),
    )
    op.create_index("ix_ingestion_jobs_manifest_name", "ingestion_jobs", ["manifest_name"])


def downgrade() -> None:
    for table in (
        "ingestion_jobs",
        "verifications",
        "association_candidates",
        "search_sessions",
        "embedding_records",
        "evidences",
        "relations",
        "functional_assertions",
        "text_chunks",
        "regions",
        "figures",
        "pages",
        "assets",
        "editions",
        "books",
    ):
        op.drop_table(table)
