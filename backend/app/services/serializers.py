from __future__ import annotations

from typing import Any

from app.db.models import (
    Asset,
    Book,
    Edition,
    Evidence,
    Figure,
    FunctionalAssertion,
    Page,
    Region,
    Relation,
    TextChunk,
)
from app.schemas.common import (
    AssetRef,
    BookSummary,
    EditionSummary,
    EvidenceResponse,
    FigureResponse,
    FunctionalAssertionResponse,
    PageResponse,
    RegionResponse,
    RelationResponse,
    SourceSummary,
    TextChunkResponse,
)


def asset_ref(asset: Asset | None) -> AssetRef | None:
    if asset is None:
        return None
    return AssetRef(
        id=asset.id,
        url=f"/api/v1/assets/{asset.id}",
        mime_type=asset.mime_type,
        width=asset.width,
        height=asset.height,
        license_status=asset.license_status,
        allow_redistribution=asset.allow_redistribution,
    )


def book_summary(book: Book) -> BookSummary:
    return BookSummary.model_validate(book)


def edition_summary(edition: Edition) -> EditionSummary:
    return EditionSummary.model_validate(edition)


def region_response(region: Region) -> RegionResponse:
    return RegionResponse.model_validate(region)


def text_response(chunk: TextChunk) -> TextChunkResponse:
    return TextChunkResponse.model_validate(chunk)


def evidence_response(evidence: Evidence) -> EvidenceResponse:
    return EvidenceResponse.model_validate(evidence)


def assertion_response(assertion: FunctionalAssertion) -> FunctionalAssertionResponse:
    return FunctionalAssertionResponse.model_validate(assertion)


def relation_response(relation: Relation) -> RelationResponse:
    return RelationResponse.model_validate(relation)


def figure_response(figure: Figure) -> FigureResponse:
    bbox: dict[str, float] | None = None
    if (
        figure.bbox_x is not None
        and figure.bbox_y is not None
        and figure.bbox_width is not None
        and figure.bbox_height is not None
    ):
        bbox = {
            "x": figure.bbox_x,
            "y": figure.bbox_y,
            "width": figure.bbox_width,
            "height": figure.bbox_height,
        }
    return FigureResponse(
        id=figure.id,
        page_id=figure.page_id,
        title=figure.title,
        asset=asset_ref(figure.asset),
        bbox=bbox,
        regions=[region_response(item) for item in figure.regions],
        text_chunks=[text_response(item) for item in figure.text_chunks],
        assertions=[assertion_response(item) for item in figure.assertions],
        relations=[relation_response(item) for item in figure.relations],
        evidences=[evidence_response(item) for item in figure.evidences],
    )


def page_response(page: Page) -> PageResponse:
    return PageResponse(
        id=page.id,
        edition_id=page.edition_id,
        volume=page.volume,
        page_or_folio=page.page_or_folio,
        width=page.width,
        height=page.height,
        asset=asset_ref(page.asset),
        figures=[figure_response(item) for item in page.figures],
    )


def source_summary(figure: Figure) -> SourceSummary:
    book = figure.page.edition.book
    edition = figure.page.edition
    return SourceSummary(
        book_title=book.title,
        edition=edition.name,
        source_name=edition.source_name,
        volume=figure.page.volume,
        page_or_folio=figure.page.page_or_folio,
        source_url=edition.source_url,
        license_status=edition.license_status,
    )


def model_versions(provider_metadata: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        item["provider"]: {key: value for key, value in item.items() if key != "provider"}
        for item in provider_metadata
    }
