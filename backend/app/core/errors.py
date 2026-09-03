from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(slots=True)
class DomainError(Exception):
    """Expected application error exposed through the stable API envelope."""

    code: str
    message: str
    status_code: int = 400
    details: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        # slots dataclasses can replace the class object and invalidate the
        # zero-argument super closure.  Initialize the concrete base directly.
        Exception.__init__(self, self.message)


def not_found(resource: str) -> DomainError:
    return DomainError(
        code="RESOURCE_NOT_FOUND",
        message=f"未找到{resource}",
        status_code=404,
    )


def database_unavailable(message: str = "数据库暂不可用") -> DomainError:
    return DomainError(
        code="DATABASE_UNAVAILABLE",
        message=message,
        status_code=503,
    )
