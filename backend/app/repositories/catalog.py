from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db.models import Book, Edition, Figure, Page


async def list_books(session: AsyncSession) -> list[Book]:
    result = await session.execute(select(Book).order_by(Book.title))
    return list(result.scalars().all())


async def list_editions(session: AsyncSession, book_id: UUID) -> list[Edition]:
    result = await session.execute(
        select(Edition).where(Edition.book_id == book_id).order_by(Edition.name)
    )
    return list(result.scalars().all())


async def get_page(session: AsyncSession, page_id: UUID) -> Page | None:
    statement = (
        select(Page)
        .where(Page.id == page_id)
        .options(
            selectinload(Page.asset),
            selectinload(Page.figures).selectinload(Figure.asset),
            selectinload(Page.figures).selectinload(Figure.regions),
            selectinload(Page.figures).selectinload(Figure.text_chunks),
            selectinload(Page.figures).selectinload(Figure.assertions),
            selectinload(Page.figures).selectinload(Figure.relations),
            selectinload(Page.figures).selectinload(Figure.evidences),
            selectinload(Page.edition).selectinload(Edition.book),
        )
    )
    result = await session.execute(statement)
    return result.scalar_one_or_none()


async def get_figure(session: AsyncSession, figure_id: UUID) -> Figure | None:
    statement = (
        select(Figure)
        .where(Figure.id == figure_id)
        .options(
            selectinload(Figure.asset),
            selectinload(Figure.regions),
            selectinload(Figure.text_chunks),
            selectinload(Figure.assertions),
            selectinload(Figure.evidences),
            selectinload(Figure.relations),
            selectinload(Figure.page).selectinload(Page.edition).selectinload(Edition.book),
        )
    )
    result = await session.execute(statement)
    return result.scalar_one_or_none()


async def list_figures_for_search(session: AsyncSession) -> list[Figure]:
    statement = select(Figure).options(
        selectinload(Figure.asset),
        selectinload(Figure.regions),
        selectinload(Figure.text_chunks),
        selectinload(Figure.assertions),
        selectinload(Figure.evidences),
        selectinload(Figure.relations),
        selectinload(Figure.page).selectinload(Page.edition).selectinload(Edition.book),
    )
    result = await session.execute(statement.order_by(Figure.id))
    return list(result.unique().scalars().all())
