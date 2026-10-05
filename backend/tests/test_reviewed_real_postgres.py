"""Opt-in integration against a disposable, migrated PostgreSQL/pgvector database.

This uses isolated synthetic review inputs to exercise the real-data format.
It never imports test reviewer identities or invented text into the business database.
"""

from __future__ import annotations

import math
import os
from collections.abc import AsyncIterator
from pathlib import Path
from typing import Any
from uuid import UUID

import httpx
import pytest
from sqlalchemy import func, select
from sqlalchemy.engine import make_url
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from test_competition_ocr_evaluation import accept_truth, core_workspace  # noqa: F401
from test_domestic_ai_manifest import ai_workspace  # noqa: F401
from test_reviewed_real_export import real_workspace  # noqa: F401

import app.api.v1.router as api_router
from app.api.deps import session_dependency, settings_dependency
from app.core.config import Settings
from app.db.models import Asset, EmbeddingRecord, Evidence, Figure, TextChunk, Verification
from app.ingestion.loader import load_manifest
from app.main import create_app
from app.retrieval.providers.registry import ProviderRegistry
from app.schemas.common import SearchResponse
from app.services.ingestion_service import _figure_image_input, stable_id
from scripts.export_reviewed_real_manifest import export_reviewed_manifest
from scripts.prepare_domestic_ai_manifest import prepare as prepare_ai

DATABASE_URL = os.environ.get("TUJI_TEST_DATABASE_URL")
pytestmark = pytest.mark.skipif(
    not DATABASE_URL, reason="explicit disposable PostgreSQL URL required"
)


@pytest.mark.asyncio
async def test_model_spaces_coexist_in_actual_pgvector() -> None:
    from uuid import uuid4

    from app.retrieval.providers.base import VectorResult
    from app.services.ingestion_service import _upsert_embedding
    from app.services.search_service import SearchService

    assert DATABASE_URL is not None
    url = make_url(DATABASE_URL)
    assert url.host in {"localhost", "127.0.0.1"} and url.port == 55432
    assert url.database == "tuji_reviewed_real_test", "refuse any business database"
    engine = create_async_engine(DATABASE_URL)
    entity_id = uuid4()
    baseline = ProviderRegistry.create()
    neural = ProviderRegistry.create(Settings(retrieval_profile="neural"))
    old = baseline.text_embedding.encode("织机")
    new = VectorResult((1.0,) + (0.0,) * 511, neural.text_embedding.metadata())
    try:
        factory = async_sessionmaker(engine, expire_on_commit=False)
        async with factory() as session:
            for result in (old, new, new):
                await _upsert_embedding(session, entity_id, "figure", "text", result)
            await session.commit()
        async with factory() as session:
            records = (
                (
                    await session.execute(
                        select(EmbeddingRecord).where(EmbeddingRecord.entity_id == entity_id)
                    )
                )
                .scalars()
                .all()
            )
            assert len(records) == 2
            assert {record.dimension for record in records} == {256, 512}
            figure = Figure(id=entity_id, regions=[])
            old_map = await SearchService(Settings(), providers=baseline)._embedding_map(
                session, [figure]
            )
            new_map = await SearchService(Settings(), providers=neural)._embedding_map(
                session, [figure]
            )
            assert len(old_map[("figure", entity_id, "text")]) == 256
            assert new_map[("figure", entity_id, "text")] == list(new.vector)
            # Remove only this test's UUID-bound rows, allowing the existing count assertions.
            for record in records:
                await session.delete(record)
            await session.commit()
    finally:
        await engine.dispose()


@pytest.mark.asyncio
async def test_migrated_postgres_real_format_api_roundtrip(
    request: pytest.FixtureRequest,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    assert DATABASE_URL is not None
    url = make_url(DATABASE_URL)
    assert url.drivername == "postgresql+asyncpg"
    assert url.host in {"localhost", "127.0.0.1"} and url.port == 55432
    assert url.database == "tuji_reviewed_real_test", "refuse to write any business database"
    workspace: dict[str, Any] = request.getfixturevalue("real_workspace")
    accept_truth(workspace)
    report = export_reviewed_manifest(**workspace["export_args"])
    exports = workspace["export_args"]
    validated = load_manifest(
        report["manifest_name"],
        manifests_root=exports["manifests_root"],
        assets_root=exports["assets_root"],
    )
    engine = create_async_engine(DATABASE_URL)
    factory = async_sessionmaker(engine, expire_on_commit=False)
    settings = Settings(
        database_url=DATABASE_URL,
        manifest_root=exports["manifests_root"],
        asset_root=exports["assets_root"],
        data_root=workspace["args"]["project_root"] / "export",
    )
    application = create_app()

    async def test_session() -> AsyncIterator[AsyncSession]:
        async with factory() as session:
            yield session

    application.dependency_overrides[session_dependency] = test_session
    application.dependency_overrides[settings_dependency] = lambda: settings
    monkeypatch.setattr(api_router, "SessionFactory", factory)
    try:
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=application),
            base_url="http://test",
        ) as client:
            for _ in range(2):
                response = await client.post(
                    "/api/v1/ingestion/jobs",
                    json={
                        "manifest_name": report["manifest_name"],
                        "dry_run": False,
                    },
                )
                assert response.status_code == 202, response.text
                job = await client.get("/api/v1/ingestion/jobs/" + response.json()["id"])
                assert job.json()["status"] == "completed", job.text
                assert job.json()["stats"]["functional_assertions"] == 0
            async with factory() as session:
                assert await session.scalar(select(func.count()).select_from(Figure)) == 2
                assert await session.scalar(select(func.count()).select_from(EmbeddingRecord)) == 6
                chunk = (await session.scalars(select(TextChunk))).first()
                assert (
                    chunk is not None
                    and chunk.text == "冶絲圖"
                    and chunk.corrected_text == "治絲圖"
                )
                assert chunk.state == "Documented"
                db_figure_id = stable_id("figure", validated.manifest.figures[0].figure_id)
                stored_figure = await session.get(Figure, db_figure_id)
                assert stored_figure is not None
                assert stored_figure.provenance["dataset_kind"] == "human_reviewed_real_pilot"
                image_vector = await session.get(
                    EmbeddingRecord,
                    stable_id(
                        "embedding",
                        f"figure:{db_figure_id}:image",
                    ),
                )
                expected = ProviderRegistry.create().image_embedding.encode(
                    _figure_image_input(validated, validated.manifest.figures[0]),
                )
                assert image_vector is not None and image_vector.dimension == 256
                assert list(image_vector.vector) == pytest.approx(expected.vector, abs=1e-6)
            figure_id = stable_id("figure", validated.manifest.figures[0].figure_id)
            detail = await client.get(f"/api/v1/figures/{figure_id}")
            assert detail.status_code == 200, detail.text
            assert detail.json()["relations"] == []
            scan = Path(next(iter(validated.asset_paths.values()))).read_bytes()
            requests = [
                await client.post("/api/v1/search/text", json={"query": "治絲圖", "top_k": 2}),
                await client.post(
                    "/api/v1/search/image",
                    files={
                        "file": ("isolated.png", scan, "image/png"),
                    },
                    data={"top_k": "2", "filters": "{}"},
                ),
                await client.post(
                    "/api/v1/search/region",
                    json={
                        "figure_id": str(figure_id),
                        "bbox": {"x": 0.1, "y": 0.4, "width": 0.8, "height": 0.5},
                        "top_k": 2,
                        "coordinate_space": "normalized",
                    },
                ),
            ]
            searches = []
            for response in requests:
                assert response.status_code == 200, response.text
                parsed = SearchResponse.model_validate(response.json())
                assert parsed.results and all(math.isfinite(r.score) for r in parsed.results)
                assert all(not r.score_components.availability["function"] for r in parsed.results)
                assert all(
                    not r.score_components.availability["model_uncertainty"] for r in parsed.results
                )
                stored = await client.get(f"/api/v1/search/{parsed.search_id}")
                assert (
                    stored.status_code == 200
                    and stored.json()["results"] == response.json()["results"]
                )
                searches.append(parsed)
            image_components = searches[1].results[0].score_components
            assert image_components.availability["evidence"] is False
            candidate = searches[0].results[0]
            verified = await client.post(
                f"/api/v1/associations/{candidate.candidate_id}/verify",
                json={
                    "state": "verified",
                    "note": "isolated test; not a historical claim",
                },
            )
            assert verified.status_code == 200, verified.text
            assert (await client.get(f"/api/v1/associations/{candidate.candidate_id}")).json()[
                "verification_state"
            ] == "verified"
            assert candidate.image_ref is not None
            asset_id = candidate.image_ref.id
            allowed = await client.get(f"/api/v1/assets/{asset_id}")
            assert allowed.status_code == 200 and allowed.content.startswith(b"\x89PNG")
            async with factory() as session:
                asset = await session.get(Asset, asset_id)
                assert asset is not None
                asset.allow_redistribution = False
                await session.commit()
            denied = await client.get(f"/api/v1/assets/{asset_id}")
            assert (
                denied.status_code == 403 and denied.json()["error"]["code"] == "LICENSE_RESTRICTED"
            )
            verification_id = UUID(verified.json()["id"])
        await engine.dispose()
        # Reopen connections after disposal: committed raw/corrected and verification survive.
        async with factory() as session:
            assert (await session.get(Verification, verification_id)).state == "verified"
            statuses = (await session.scalars(select(Evidence.status))).all()
            assert statuses and "Verified" not in statuses
    finally:
        await engine.dispose()


@pytest.mark.asyncio
async def test_ai_real_format_has_separate_provenance_and_raw_text_in_postgres(
    request: pytest.FixtureRequest,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    assert DATABASE_URL is not None
    url = make_url(DATABASE_URL)
    assert url.drivername == "postgresql+asyncpg" and url.port == 55432
    assert url.host in {"localhost", "127.0.0.1"} and url.database == "tuji_reviewed_real_test"
    workspace: dict[str, Any] = request.getfixturevalue("ai_workspace")
    report = prepare_ai(**workspace)
    validated = load_manifest(
        report["manifest_name"],
        manifests_root=workspace["manifests_root"],
        assets_root=workspace["assets_root"],
    )
    engine = create_async_engine(DATABASE_URL)
    factory = async_sessionmaker(engine, expire_on_commit=False)
    settings = Settings(
        database_url=DATABASE_URL,
        manifest_root=workspace["manifests_root"],
        asset_root=workspace["assets_root"],
        data_root=workspace["project_root"] / "export",
    )
    application = create_app()

    async def test_session() -> AsyncIterator[AsyncSession]:
        async with factory() as session:
            yield session

    application.dependency_overrides[session_dependency] = test_session
    application.dependency_overrides[settings_dependency] = lambda: settings
    monkeypatch.setattr(api_router, "SessionFactory", factory)
    try:
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=application),
            base_url="http://test",
        ) as client:
            for _ in range(2):
                response = await client.post(
                    "/api/v1/ingestion/jobs",
                    json={
                        "manifest_name": report["manifest_name"],
                        "dry_run": False,
                    },
                )
                assert response.status_code == 202, response.text
                job = await client.get("/api/v1/ingestion/jobs/" + response.json()["id"])
                assert job.json()["status"] == "completed", job.text
            figure_id = stable_id("figure", "ai-test-left")
            detail = await client.get(f"/api/v1/figures/{figure_id}")
            assert detail.status_code == 200, detail.text
            body = detail.json()
            assert body["data_status"]["review_origin"] == "ai_assisted"
            assert body["data_status"]["human_reviewed"] is False
            assert all(
                c["corrected_text"] is None and c["state"] == "Inferred"
                for c in body["text_chunks"]
            )
            raw = next(c for c in body["text_chunks"] if c["origin"] == "raw_ocr")
            assert raw["text"] == "左raw错字"
            crop = _figure_image_input(validated, validated.manifest.figures[0])
            assert isinstance(crop, bytes)
            searches = [
                await client.post(
                    "/api/v1/search/text",
                    json={
                        "query": "AI场景",
                        "filters": {"dataset_kinds": ["ai_assisted_real_pilot"]},
                    },
                ),
                await client.post(
                    "/api/v1/search/image",
                    files={
                        "file": ("isolated.png", crop, "image/png"),
                    },
                    data={"filters": '{"dataset_kinds":["ai_assisted_real_pilot"]}'},
                ),
                await client.post(
                    "/api/v1/search/region",
                    json={
                        "figure_id": str(figure_id),
                        "bbox": {"x": 0.05, "y": 0.25, "width": 0.4, "height": 0.7},
                        "filters": {"dataset_kinds": ["ai_assisted_real_pilot"]},
                    },
                ),
            ]
            for response in searches:
                assert response.status_code == 200, response.text
                parsed = SearchResponse.model_validate(response.json())
                assert parsed.results and all(
                    r.data_status.dataset_kind == "ai_assisted_real_pilot"
                    and math.isfinite(r.score)
                    for r in parsed.results
                )
                stored = await client.get(f"/api/v1/search/{parsed.search_id}")
                assert stored.json()["results"] == response.json()["results"]
            async with factory() as session:
                ids = [stable_id("figure", f.figure_id) for f in validated.manifest.figures]
                assert (
                    await session.scalar(
                        select(func.count()).select_from(Figure).where(Figure.id.in_(ids))
                    )
                    == 2
                )
                stored_figure = await session.get(Figure, figure_id)
                assert stored_figure is not None and "human_review" not in stored_figure.provenance
                vector = await session.get(
                    EmbeddingRecord,
                    stable_id(
                        "embedding",
                        f"figure:{figure_id}:image",
                    ),
                )
                expected = ProviderRegistry.create().image_embedding.encode(crop)
                assert vector is not None and list(vector.vector) == pytest.approx(
                    expected.vector,
                    abs=1e-6,
                )
            await engine.dispose()
            reopened = await client.get(f"/api/v1/figures/{figure_id}")
            assert reopened.json()["text_chunks"] == body["text_chunks"]
    finally:
        await engine.dispose()
