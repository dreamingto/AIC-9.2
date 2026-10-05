"""Add a selected model's vectors transactionally without altering source/review data."""

from __future__ import annotations

import argparse
import asyncio
import json
from pathlib import Path
from typing import Any

from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.core.config import Settings
from app.core.security import resolve_safe_path
from app.repositories.catalog import list_figures_for_search
from app.retrieval.providers.registry import ProviderRegistry
from app.schemas.common import BBox
from app.services.ingestion_service import _upsert_embedding
from app.services.search_service import SearchService


async def reindex(settings: Settings) -> dict[str, Any]:
    providers = ProviderRegistry.create(settings)
    health = await asyncio.to_thread(providers.health)
    if not all(item.available for item in health):
        raise RuntimeError("selected providers unavailable; no vector rows changed")
    engine = create_async_engine(settings.database_url)
    stats = {"figures": 0, "regions": 0, "vectors_written": 0}
    try:
        async with async_sessionmaker(engine, expire_on_commit=False)() as session:
            figures = await list_figures_for_search(session)
            for figure in figures:
                text = SearchService._figure_text(figure)
                if text:
                    result = await asyncio.to_thread(providers.text_embedding.encode, text)
                    await _upsert_embedding(session, figure.id, "figure", "text", result)
                    stats["vectors_written"] += 1
                    if providers.clip_text:
                        result = await asyncio.to_thread(providers.clip_text.encode, text)
                        await _upsert_embedding(session, figure.id, "figure", "clip_text", result)
                        stats["vectors_written"] += 1
                if figure.asset:
                    path = resolve_safe_path(settings.asset_root, figure.asset.relative_path)
                    image: bytes = path.read_bytes()
                    if figure.bbox_x is not None:
                        if (
                            figure.bbox_y is None
                            or figure.bbox_width is None
                            or figure.bbox_height is None
                        ):
                            raise ValueError("incomplete figure bbox")
                        image = SearchService._crop_image(
                            image,
                            BBox(
                                x=figure.bbox_x,
                                y=figure.bbox_y,
                                width=figure.bbox_width,
                                height=figure.bbox_height,
                            ),
                        )
                    result = await asyncio.to_thread(providers.image_embedding.encode, image)
                    await _upsert_embedding(session, figure.id, "figure", "image", result)
                    stats["vectors_written"] += 1
                    for region in figure.regions:
                        crop = SearchService._crop_image(
                            path.read_bytes(),
                            BBox(x=region.x, y=region.y, width=region.width, height=region.height),
                        )
                        result = await asyncio.to_thread(providers.image_embedding.encode, crop)
                        await _upsert_embedding(session, region.id, "region", "image", result)
                        stats["regions"] += 1
                        stats["vectors_written"] += 1
                stats["figures"] += 1
                print(f"indexed {stats['figures']}/{len(figures)}", flush=True)
            await session.commit()
    finally:
        await engine.dispose()
    return {
        **stats,
        "profile": settings.retrieval_profile,
        "providers": [item.as_dict() for item in health],
        "evaluation_status": "not_evaluated",
        "source_records_changed": False,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--profile", choices=["baseline", "neural"], default="neural")
    parser.add_argument("--service-url")
    parser.add_argument(
        "--asset-root", type=Path, default=Path(__file__).parents[1] / "data/assets"
    )
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    settings = Settings(retrieval_profile=args.profile)
    settings.asset_root = args.asset_root
    if args.service_url:
        settings.model_service_url = args.service_url
    report = asyncio.run(reindex(settings))
    content = json.dumps(report, ensure_ascii=False, indent=2)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(content + "\n", encoding="utf-8")
    print(content)


if __name__ == "__main__":
    main()
