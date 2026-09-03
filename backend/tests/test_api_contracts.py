from __future__ import annotations

import io
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient
from PIL import Image

from app.core.config import Settings
from app.core.errors import DomainError
from app.core.security import sanitize_image_bytes, validate_image_bytes
from app.main import app
from app.services.search_service import SearchService


def test_openapi_contains_complete_v1_surface() -> None:
    paths = set(app.openapi()["paths"])
    assert paths == {
        "/api/v1/health",
        "/api/v1/capabilities",
        "/api/v1/books",
        "/api/v1/books/{book_id}/editions",
        "/api/v1/pages/{page_id}",
        "/api/v1/figures/{figure_id}",
        "/api/v1/assets/{asset_id}",
        "/api/v1/search/text",
        "/api/v1/search/image",
        "/api/v1/search/region",
        "/api/v1/search/{search_id}",
        "/api/v1/associations/{candidate_id}",
        "/api/v1/associations/{candidate_id}/verify",
        "/api/v1/ingestion/jobs",
        "/api/v1/ingestion/jobs/{job_id}",
    }


def test_capabilities_and_default_422_use_stable_contract() -> None:
    with TestClient(app) as client:
        capabilities = client.get("/api/v1/capabilities")
        assert capabilities.status_code == 200
        body = capabilities.json()
        assert body["search_types"] == ["text", "image", "region"]
        assert all(provider["available"] for provider in body["providers"])

        invalid = client.post(
            "/api/v1/search/region",
            json={
                "figure_id": "00000000-0000-0000-0000-000000000001",
                "bbox": {"x": 0.9, "y": 0, "width": 0.2, "height": 0.2},
            },
        )
        assert invalid.status_code == 422
        error = invalid.json()["error"]
        assert error["code"] == "COORDINATE_OUT_OF_RANGE"
        assert error["request_id"] == invalid.headers["x-request-id"]
        assert error["details"]["errors"]


def test_health_reports_database_unavailable(monkeypatch: pytest.MonkeyPatch) -> None:
    async def unavailable() -> bool:
        return False

    monkeypatch.setattr("app.db.session.ping_database", unavailable)
    with TestClient(app) as client:
        response = client.get("/api/v1/health")
    assert response.status_code == 503
    assert response.json()["error"]["code"] == "DATABASE_UNAVAILABLE"


def _png_bytes() -> bytes:
    output = io.BytesIO()
    image = Image.new("RGB", (32, 24), "white")
    image.save(output, format="PNG", pnginfo=None)
    image.close()
    return output.getvalue()


def test_image_validation_checks_mime_and_sanitizes() -> None:
    settings = Settings(max_upload_bytes=100_000, max_image_pixels=10_000)
    content = _png_bytes()
    info = validate_image_bytes(content, "image/png", settings)
    assert (info.mime_type, info.width, info.height) == ("image/png", 32, 24)
    sanitized = sanitize_image_bytes(content, info.mime_type)
    assert validate_image_bytes(sanitized, "image/png", settings).width == 32

    with pytest.raises(DomainError) as mime_error:
        validate_image_bytes(content, "image/jpeg", settings)
    assert mime_error.value.code == "INVALID_IMAGE"
    with pytest.raises(DomainError):
        validate_image_bytes(b"\x89PNG\r\n\x1a\nnot-an-image", "image/png", settings)


def test_functional_similarity_normalizes_fixture_labels() -> None:
    service = SearchService(Settings())
    cfr = service.providers.cfr.extract("流水带动轮轴旋转，用于提水灌溉")
    query = service._cfr_to_dicts(cfr)
    candidate = [
        SimpleNamespace(slot="power_source", concept="流水", confidence=0.94),
        SimpleNamespace(slot="motion", concept="旋转", confidence=0.78),
        SimpleNamespace(slot="purpose", concept="提水灌溉", confidence=0.94),
    ]
    score = service._functional_similarity(query, candidate)
    assert score is not None and score > 0.0
