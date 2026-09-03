from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db.models import (
    AssociationCandidate,
    Edition,
    EmbeddingRecord,
    Figure,
    Page,
    SearchSession,
    Verification,
)


async def embeddings_for_entities(
    session: AsyncSession, entity_ids: list[UUID]
) -> list[EmbeddingRecord]:
    if not entity_ids:
        return []
    result = await session.execute(
        select(EmbeddingRecord).where(EmbeddingRecord.entity_id.in_(entity_ids))
    )
    return list(result.scalars().all())


async def get_search_session(session: AsyncSession, search_id: UUID) -> SearchSession | None:
    result = await session.execute(
        select(SearchSession)
        .where(SearchSession.id == search_id)
        .options(
            selectinload(SearchSession.candidates)
            .selectinload(AssociationCandidate.figure)
            .selectinload(Figure.page)
            .selectinload(Page.edition)
            .selectinload(Edition.book)
        )
    )
    return result.scalar_one_or_none()


async def get_candidate(session: AsyncSession, candidate_id: UUID) -> AssociationCandidate | None:
    result = await session.execute(
        select(AssociationCandidate)
        .where(AssociationCandidate.id == candidate_id)
        .options(
            selectinload(AssociationCandidate.figure)
            .selectinload(Figure.page)
            .selectinload(Page.edition)
            .selectinload(Edition.book),
            selectinload(AssociationCandidate.figure).selectinload(Figure.asset),
            selectinload(AssociationCandidate.figure).selectinload(Figure.regions),
            selectinload(AssociationCandidate.figure).selectinload(Figure.text_chunks),
            selectinload(AssociationCandidate.figure).selectinload(Figure.assertions),
            selectinload(AssociationCandidate.figure).selectinload(Figure.evidences),
            selectinload(AssociationCandidate.verifications),
            selectinload(AssociationCandidate.search_session),
        )
    )
    return result.scalar_one_or_none()


async def latest_verification(session: AsyncSession, candidate_id: UUID) -> Verification | None:
    result = await session.execute(
        select(Verification)
        .where(Verification.candidate_id == candidate_id)
        .order_by(Verification.created_at.desc())
        .limit(1)
    )
    return result.scalar_one_or_none()
