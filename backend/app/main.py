"""FastAPI application entry point for 机图索隐 V1."""

from __future__ import annotations

import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy.exc import SQLAlchemyError
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.api.v1.demo import router as demo_router
from app.api.v1.router import router as v1_router
from app.core.config import get_settings
from app.core.errors import DomainError
from app.core.logging import configure_logging
from app.core.middleware import RequestIdMiddleware

logger = logging.getLogger(__name__)


def _request_id(request: Request) -> str:
    return str(getattr(request.state, "request_id", "-"))


def _error_response(
    request: Request,
    code: str,
    message: str,
    status_code: int,
    details: dict[str, Any] | None = None,
) -> JSONResponse:
    return JSONResponse(
        status_code=status_code,
        content={
            "error": {
                "code": code,
                "message": message,
                "request_id": _request_id(request),
                "details": details or {},
            }
        },
    )


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    settings = get_settings()
    configure_logging(settings.log_level)
    yield


def create_app() -> FastAPI:
    settings = get_settings()
    application = FastAPI(
        title="机图索隐后端",
        version=settings.app_version,
        description="面向传统技术图像的证据感知检索 V1 API（离线工程基线）",
        lifespan=lifespan,
    )
    application.add_middleware(RequestIdMiddleware)
    application.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=False,
        allow_methods=["GET", "POST", "OPTIONS"],
        allow_headers=["*"],
    )
    application.include_router(v1_router)
    application.include_router(demo_router)

    @application.exception_handler(DomainError)
    async def domain_error_handler(request: Request, exc: DomainError) -> JSONResponse:
        return _error_response(request, exc.code, exc.message, exc.status_code, exc.details)

    @application.exception_handler(RequestValidationError)
    async def validation_error_handler(
        request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        details = {
            "errors": [
                {
                    "loc": list(error.get("loc", ())),
                    "msg": str(error.get("msg", "请求参数不合法")),
                    "type": str(error.get("type", "value_error")),
                }
                for error in exc.errors()
            ]
        }
        text = str(exc).lower()
        code = (
            "COORDINATE_OUT_OF_RANGE" if "bbox" in text or "coordinate" in text else "INVALID_QUERY"
        )
        message = "框选坐标不合法" if code == "COORDINATE_OUT_OF_RANGE" else "请求参数不合法"
        return _error_response(request, code, message, 422, details)

    @application.exception_handler(StarletteHTTPException)
    async def http_error_handler(request: Request, exc: StarletteHTTPException) -> JSONResponse:
        if exc.status_code == 404:
            code, message = "RESOURCE_NOT_FOUND", "请求资源不存在"
        else:
            code, message = "INTERNAL_ERROR", str(exc.detail)
        return _error_response(request, code, message, exc.status_code)

    @application.exception_handler(SQLAlchemyError)
    async def sqlalchemy_error_handler(request: Request, exc: SQLAlchemyError) -> JSONResponse:
        logger.exception("database error", extra={"request_id": _request_id(request)})
        return _error_response(request, "DATABASE_UNAVAILABLE", "数据库暂不可用", 503)

    @application.exception_handler(Exception)
    async def unhandled_error_handler(request: Request, exc: Exception) -> JSONResponse:
        logger.exception("unhandled application error", extra={"request_id": _request_id(request)})
        return _error_response(request, "INTERNAL_ERROR", "服务内部错误", 500)

    return application


app = create_app()

__all__ = ["app", "create_app"]
