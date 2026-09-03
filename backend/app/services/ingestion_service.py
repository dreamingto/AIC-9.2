"""Database persistence for the controlled, offline fixture manifest.

The importer is deliberately deterministic: every manifest identifier maps to a
stable UUID5.  Re-running the same manifest therefore updates the same rows
instead of creating duplicate books, figures or vectors.
"""

from __future__ import annotations

import hashlib
import io
import logging
from pathlib import Path
from typing import Any
from uuid import UUID, uuid5

from PIL import Image
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings
from app.db.models import (
    Asset,
    Book,
    Edition,
    EmbeddingRecord,
    Evidence,
    Figure,
    FunctionalAssertion,
    IngestionJob,
    Page,
    Region,
    Relation,
    TextChunk,
)
from app.ingestion.contracts import ValidatedFixture
from app.ingestion.loader import ManifestValidationError, load_manifest
from app.retrieval.providers.registry import ProviderRegistry

logger = logging.getLogger(__name__)

FIXTURE_NAMESPACE = UUID("7a75b1e8-9e6f-4b3d-9f11-5ea6d2d8e2b4")


def stable_id(kind: str, key: str) -> UUID:
    """Return a reproducible UUID for a fixture record."""

    return uuid5(FIXTURE_NAMESPACE, f"{kind}:{key}")


def _provenance(
    source: Any,
    *,
    volume: str | None = None,
    page_or_folio: str | None = None,
    original_path: str | None = None,
) -> dict[str, Any]:
    values: dict[str, Any] = {
        "source_url": source.source_url,
        "source_name": source.source_name,
        "book_title": source.book_title,
        "edition": source.edition,
        "volume": volume or source.volume,
        "page_or_folio": page_or_folio or source.page_or_folio,
        "license_status": str(source.license_status),
        "license_note": source.license_note,
        "allow_training": source.allow_training,
        "allow_redistribution": source.allow_redistribution,
        "retrieved_at": source.retrieved_at.isoformat(),
        "pipeline_version": source.pipeline_version,
    }
    if original_path is not None:
        values["original_path"] = original_path
    return values


async def _upsert(
    session: AsyncSession, model: type[Any], object_id: UUID, values: dict[str, Any]
) -> Any:
    obj = await session.get(model, object_id)
    if obj is None:
        obj = model(id=object_id, **values)
        session.add(obj)
    else:
        for key, value in values.items():
            setattr(obj, key, value)
    return obj


def _text_for_figure(figure: Any, chunks_by_figure: dict[str, list[Any]]) -> str:
    chunks = chunks_by_figure.get(figure.figure_id, [])
    return " ".join([figure.title, figure.caption] + [item.content for item in chunks])


def _crop_asset(path: Path, bbox: Any) -> bytes:
    with Image.open(path) as source:
        source.load()
        width, height = source.size
        left = max(0, min(width - 1, int(bbox.x * width)))
        top = max(0, min(height - 1, int(bbox.y * height)))
        right = max(left + 1, min(width, int((bbox.x + bbox.width) * width)))
        bottom = max(top + 1, min(height, int((bbox.y + bbox.height) * height)))
        crop = source.crop((left, top, right, bottom)).convert("RGB")
        output = io.BytesIO()
        crop.save(output, format="PNG", optimize=False)
        crop.close()
        return output.getvalue()


async def persist_fixture(
    session: AsyncSession,
    fixture: ValidatedFixture,
    settings: Settings,
    providers: ProviderRegistry | None = None,
) -> dict[str, int | bool | str]:
    """Validate relationships again and upsert all fixture entities."""

    manifest = fixture.manifest
    providers = providers or ProviderRegistry.create()
    source_by_id = {item.source_id: item for item in manifest.sources}
    asset_by_id = {item.asset_id: item for item in manifest.assets}
    page_by_id = {item.page_id: item for item in manifest.pages}
    figure_by_id = {item.figure_id: item for item in manifest.figures}
    chunks_by_figure: dict[str, list[Any]] = {}
    for chunk in manifest.text_chunks:
        chunks_by_figure.setdefault(chunk.figure_id, []).append(chunk)

    book_ids: dict[str, UUID] = {}
    edition_ids: dict[str, UUID] = {}
    for source in manifest.sources:
        book_id = stable_id("book", source.source_id)
        edition_id = stable_id("edition", source.source_id)
        book_ids[source.source_id] = book_id
        edition_ids[source.source_id] = edition_id
        await _upsert(
            session,
            Book,
            book_id,
            {
                "title": source.book_title,
                "author": source.author,
                "era": source.era,
                "description": manifest.description,
            },
        )
        await _upsert(
            session,
            Edition,
            edition_id,
            {
                "book_id": book_id,
                "name": source.edition,
                "edition_note": source.license_note,
                "source_url": source.source_url,
                "source_name": source.source_name,
                "license_status": str(source.license_status),
                "license_note": source.license_note,
                "allow_training": source.allow_training,
                "allow_redistribution": source.allow_redistribution,
                "retrieved_at": source.retrieved_at,
                "pipeline_version": source.pipeline_version,
            },
        )

    asset_ids: dict[str, UUID] = {}
    for asset in manifest.assets:
        asset_id = stable_id("asset", asset.asset_id)
        asset_ids[asset.asset_id] = asset_id
        source_default = next(iter(manifest.sources), None)
        # Asset records in V1 do not repeat source_id; the owning figure/page
        # supplies the precise source below.  Defaults are overwritten when
        # the figure is persisted.
        await _upsert(
            session,
            Asset,
            asset_id,
            {
                "relative_path": asset.relative_path,
                "mime_type": asset.mime_type,
                "byte_size": asset_paths_size(fixture.asset_paths[asset.asset_id]),
                "width": asset.width,
                "height": asset.height,
                "source_url": source_default.source_url if source_default else None,
                "source_name": source_default.source_name if source_default else None,
                "license_status": str(source_default.license_status)
                if source_default
                else "unknown",
                "license_note": source_default.license_note if source_default else None,
                "allow_training": source_default.allow_training if source_default else False,
                "allow_redistribution": source_default.allow_redistribution
                if source_default
                else False,
                "retrieved_at": source_default.retrieved_at if source_default else None,
                "sha256": asset.sha256,
                "pipeline_version": source_default.pipeline_version if source_default else None,
            },
        )

    page_ids: dict[str, UUID] = {}
    for page in manifest.pages:
        source = source_by_id[page.source_id]
        page_id = stable_id("page", page.page_id)
        page_ids[page.page_id] = page_id
        owning_figure = next((f for f in manifest.figures if f.page_id == page.page_id), None)
        page_asset_id = asset_ids[owning_figure.asset_id] if owning_figure else None
        dimensions = asset_by_id[owning_figure.asset_id] if owning_figure else None
        await _upsert(
            session,
            Page,
            page_id,
            {
                "edition_id": edition_ids[page.source_id],
                "volume": page.volume,
                "page_or_folio": page.page_or_folio,
                "asset_id": page_asset_id,
                "width": dimensions.width if dimensions else None,
                "height": dimensions.height if dimensions else None,
                "provenance": _provenance(
                    source, volume=page.volume, page_or_folio=page.page_or_folio
                ),
            },
        )

    figure_ids: dict[str, UUID] = {}
    for figure in manifest.figures:
        source = source_by_id[page_by_id[figure.page_id].source_id]
        figure_id = stable_id("figure", figure.figure_id)
        figure_ids[figure.figure_id] = figure_id
        await _upsert(
            session,
            Figure,
            figure_id,
            {
                "page_id": page_ids[figure.page_id],
                "title": figure.title,
                "asset_id": asset_ids[figure.asset_id],
                "bbox_x": figure.bbox.x,
                "bbox_y": figure.bbox.y,
                "bbox_width": figure.bbox.width,
                "bbox_height": figure.bbox.height,
                "provenance": _provenance(
                    source,
                    volume=page_by_id[figure.page_id].volume,
                    page_or_folio=page_by_id[figure.page_id].page_or_folio,
                    original_path=figure.original_path,
                ),
            },
        )
        # Correct the asset's source/licence using its owning figure.
        asset_obj = await session.get(Asset, asset_ids[figure.asset_id])
        if asset_obj is not None:
            asset_obj.source_url = source.source_url
            asset_obj.source_name = source.source_name
            asset_obj.license_status = str(source.license_status)
            asset_obj.license_note = source.license_note
            asset_obj.allow_training = source.allow_training
            asset_obj.allow_redistribution = source.allow_redistribution
            asset_obj.retrieved_at = source.retrieved_at
            asset_obj.pipeline_version = source.pipeline_version

    for region in manifest.regions:
        figure = figure_by_id[region.figure_id]
        await _upsert(
            session,
            Region,
            stable_id("region", region.region_id),
            {
                "figure_id": figure_ids[region.figure_id],
                "label": f"{region.label}（{region.role}）",
                "x": region.bbox.x,
                "y": region.bbox.y,
                "width": region.bbox.width,
                "height": region.bbox.height,
                "provenance": {"role": region.role, "evidence_state": str(region.evidence_state)},
            },
        )

    for chunk in manifest.text_chunks:
        await _upsert(
            session,
            TextChunk,
            stable_id("text", chunk.text_id),
            {
                "figure_id": figure_ids[chunk.figure_id],
                "chunk_type": str(chunk.kind),
                "text": chunk.content,
                "corrected_text": chunk.content if str(chunk.kind) == "corrected" else None,
                "source_pointer": chunk.text_id,
                "state": str(chunk.evidence_state),
            },
        )

    for evidence in manifest.evidence:
        content = evidence.excerpt or f"{evidence.kind.value} evidence: {evidence.source_ref}"
        await _upsert(
            session,
            Evidence,
            stable_id("evidence", evidence.evidence_id),
            {
                "figure_id": figure_ids[evidence.figure_id],
                "evidence_type": evidence.kind.value,
                "status": str(evidence.state),
                "content": content,
                "pointer": evidence.source_ref,
                "support_confidence": {
                    "Observed": 0.8,
                    "Documented": 0.9,
                    "Inferred": 0.5,
                    "Verified": 1.0,
                }.get(str(evidence.state), 0.5),
                "source_weight": 1.0,
            },
        )

    for assertion in manifest.functional_assertions:
        await _upsert(
            session,
            FunctionalAssertion,
            stable_id("assertion", assertion.assertion_id),
            {
                "figure_id": figure_ids[assertion.figure_id],
                "slot": str(assertion.slot),
                "concept": assertion.concept,
                "confidence": assertion.confidence,
                "state": str(assertion.state),
                "evidence_pointer": ",".join(assertion.evidence_ids),
            },
        )

    for relation in manifest.relations:
        await _upsert(
            session,
            Relation,
            stable_id("relation", relation.relation_id),
            {
                "figure_id": figure_ids[relation.figure_id],
                "predicate": str(relation.predicate),
                "subject": relation.subject,
                "object": relation.object,
                "weight": relation.confidence,
                "confidence": relation.confidence,
            },
        )

    await session.flush()

    # Replace vectors for each deterministic entity/modality.  This keeps a
    # changed preprocessing version from leaving stale duplicate vectors.
    figure_chunks = chunks_by_figure
    for figure in manifest.figures:
        db_figure_id = figure_ids[figure.figure_id]
        text = _text_for_figure(figure, figure_chunks)
        text_result = providers.text_embedding.encode(text)
        await _upsert_embedding(session, db_figure_id, "figure", "text", text_result)
        image_path = fixture.asset_paths[figure.asset_id]
        image_result = providers.image_embedding.encode(image_path)
        await _upsert_embedding(session, db_figure_id, "figure", "image", image_result)
        for region in [item for item in manifest.regions if item.figure_id == figure.figure_id]:
            crop = _crop_asset(image_path, region.bbox)
            region_result = providers.image_embedding.encode(crop)
            await _upsert_embedding(
                session, stable_id("region", region.region_id), "region", "image", region_result
            )

    await session.flush()
    return {
        **fixture.counts,
        "manifest_name": fixture.manifest_path.name,
        "evaluation_status": manifest.evaluation_status,
        "idempotent": True,
    }


def asset_paths_size(path: Path) -> int:
    return path.stat().st_size


async def _upsert_embedding(
    session: AsyncSession,
    entity_id: UUID,
    entity_type: str,
    modality: str,
    result: Any,
) -> None:
    metadata = result.metadata
    embedding_id = stable_id("embedding", f"{entity_type}:{entity_id}:{modality}")
    await _upsert(
        session,
        EmbeddingRecord,
        embedding_id,
        {
            "entity_type": entity_type,
            "entity_id": entity_id,
            "modality": modality,
            "vector": list(result.vector),
            "dimension": metadata.dimension,
            "provider": metadata.provider,
            "model": metadata.model,
            "version": metadata.version,
            "preprocessing_hash": metadata.preprocessing_hash,
        },
    )


async def run_ingestion_job(
    job_id: UUID,
    settings: Settings,
    session_factory: Any,
    providers: ProviderRegistry | None = None,
) -> None:
    """Run one job in an isolated session and persist terminal status."""

    async with session_factory() as session:
        job = await session.get(IngestionJob, job_id)
        if job is None:
            return
        job.status = "running"
        job.error_message = None
        await session.commit()
        try:
            fixture = load_manifest(
                job.manifest_name,
                manifests_root=settings.manifest_root,
                assets_root=settings.asset_root,
                max_asset_bytes=settings.max_upload_bytes,
            )
            manifest_hash = hashlib.sha256(fixture.manifest_path.read_bytes()).hexdigest()
            job.manifest_sha256 = manifest_hash
            if job.dry_run:
                job.stats = fixture.counts
            else:
                job.stats = await persist_fixture(session, fixture, settings, providers)
            job.status = "completed"
            await session.commit()
        except ManifestValidationError as exc:
            await session.rollback()
            job = await session.get(IngestionJob, job_id)
            if job is not None:
                job.status = "failed"
                job.error_message = str(exc)
                job.stats = {"details": exc.details}
                await session.commit()
        except Exception as exc:  # pragma: no cover - defensive terminal path
            logger.exception("ingestion job failed", extra={"request_id": "-"})
            await session.rollback()
            job = await session.get(IngestionJob, job_id)
            if job is not None:
                job.status = "failed"
                job.error_message = "导入任务执行失败"
                job.stats = {"error_type": type(exc).__name__}
                await session.commit()


__all__ = ["persist_fixture", "run_ingestion_job", "stable_id"]
