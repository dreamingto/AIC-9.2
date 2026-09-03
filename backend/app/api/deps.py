from __future__ import annotations

from collections.abc import AsyncIterator

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings, get_settings
from app.db.session import get_session


def settings_dependency() -> Settings:
    return get_settings()


async def session_dependency() -> AsyncIterator[AsyncSession]:
    async for session in get_session():
        yield session
