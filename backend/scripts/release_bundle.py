"""Build/verify/restore a frozen domestic input bundle; never package secrets or models."""
from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import math
import shutil
import zipfile
from pathlib import Path, PurePosixPath
from typing import Any
from uuid import UUID

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.core.config import Settings
from app.db.models import EmbeddingRecord, Figure
from app.ingestion.contracts import AIRealManifest
from app.ingestion.loader import load_manifest
from app.repositories.catalog import list_figures_for_search
from app.retrieval.experiments.comparison import validate_locked_figures
from app.retrieval.providers.base import VectorResult
from app.retrieval.providers.registry import ProviderRegistry
from app.services.ingestion_service import _upsert_embedding, stable_id
from app.services.search_service import SearchService

ROOT = Path(__file__).resolve().parents[2]
MANIFEST = "ai-real-domestic-8b4defa06141f66e.json"
LOCK = "release/domestic-data.lock.json"
SNAPSHOT = "backend/data/release/embeddings.json"


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def json_bytes(value: Any) -> bytes:
    return (json.dumps(value, ensure_ascii=False, indent=2) + "\n").encode("utf-8")


def safe_target(root: Path, name: str) -> Path:
    parts = PurePosixPath(name).parts
    if "\\" in name or len(parts) < 4 or parts[:2] != ("backend", "data"):
        raise ValueError("bundle path is outside the allowed data tree")
    if any(p in {"..", ".", ".git", ".env"} for p in parts):
        raise ValueError("unsafe bundle path")
    target = (root / name).resolve()
    target.relative_to(root.resolve())
    return target


def manifest_at(root: Path) -> AIRealManifest:
    result = load_manifest(
        MANIFEST, manifests_root=root / "backend/data/manifests",
        assets_root=root / "backend/data/assets",
    ).manifest
    if not isinstance(result, AIRealManifest):
        raise ValueError("release only accepts the AI-assisted domestic manifest")
    if not all(s.allow_redistribution for s in result.sources):
        raise ValueError("release includes a source that forbids redistribution")
    return result


def entity_ids(manifest: AIRealManifest) -> dict[UUID, str]:
    return {
        **{stable_id("figure", f.figure_id): "figure" for f in manifest.figures},
        **{stable_id("region", r.region_id): "region" for r in manifest.regions},
    }


async def vectors(
    settings: Settings, manifest: AIRealManifest, root: Path = ROOT,
) -> dict[str, Any]:
    engine = create_async_engine(settings.database_url)
    try:
        async with async_sessionmaker(engine)() as session:
            await session.execute(text("SET TRANSACTION READ ONLY"))
            rows = (await session.scalars(select(EmbeddingRecord).where(
                EmbeddingRecord.entity_id.in_(entity_ids(manifest)),
            ).order_by(EmbeddingRecord.id))).all()
            return {
                "schema_version": "1.0", "artifact_kind": "frozen_model_vectors",
                "manifest_sha256": digest(
                    (root / "backend/data/manifests" / MANIFEST).read_bytes()
                ),
                "evaluation_status": "not_evaluated",
                "records": [{
                    "entity_id": str(r.entity_id), "entity_type": r.entity_type,
                    "modality": r.modality, "vector": [float(v) for v in r.vector],
                    "provider": r.provider, "model": r.model, "version": r.version,
                    "dimension": r.dimension, "preprocessing_hash": r.preprocessing_hash,
                } for r in rows],
            }
    finally:
        await engine.dispose()


def package_files(root: Path, manifest: AIRealManifest) -> dict[str, bytes]:
    pilot = root / "backend/data/real_pilot"
    names = [
        "backend/data/manifests/" + MANIFEST,
        *["backend/data/real_pilot/" + n for n in (
            "sources.json", "domestic_ai_selection.json", "supplementary_pages.json",
            "supplementary_ocr_results.json",
        )],
        *["backend/data/assets/" + a.relative_path for a in manifest.assets],
    ]
    registry = json.loads((pilot / "sources.json").read_text(encoding="utf-8"))
    source_ids = {s.source_id for s in manifest.sources}
    for source in registry["sources"]:
        if source["source_id"] in source_ids:
            if not source["allow_redistribution"]:
                raise ValueError("original PDF forbids redistribution")
            name = "backend/data/assets/real_pilot_v1/" + source["local_filename"]
            if digest(safe_target(root, name).read_bytes()) != source["sha256"]:
                raise ValueError("original PDF hash mismatch")
            names.append(name)
    inventory = json.loads((pilot / "supplementary_pages.json").read_text(encoding="utf-8"))
    selected = {p.page_id for p in manifest.pages}
    for page in inventory["pages"]:
        if page["page_id"] in selected:
            names.append(page["image_path"])
    return {n: safe_target(root, n).read_bytes() for n in sorted(set(names))}


def build(root: Path, output: Path, snapshot: dict[str, Any]) -> dict[str, Any]:
    manifest = manifest_at(root)
    files = package_files(root, manifest)
    files[SNAPSHOT] = json_bytes(snapshot)
    entries = [{"path": n, "size": len(b), "sha256": digest(b)} for n, b in sorted(files.items())]
    fingerprint = digest(json_bytes(entries))[:16]
    output.mkdir(parents=True, exist_ok=True)
    archive = output / f"jitu-domestic-{fingerprint}.zip"
    if archive.exists():
        raise ValueError("refuse to overwrite existing release bundle")
    with zipfile.ZipFile(archive, "x", compression=zipfile.ZIP_DEFLATED) as bundle:
        for name, data in files.items():
            bundle.writestr(name, data)
    lock = {
        "schema_version": "1.0", "release_id": "domestic-" + fingerprint,
        "archive": archive.name, "archive_sha256": digest(archive.read_bytes()),
        "archive_bytes": archive.stat().st_size, "files": entries,
        "manifest_name": MANIFEST, "evaluation_status": "not_evaluated",
        "independent_ground_truth": False, "models_included": False,
        "figures": len(manifest.figures), "regions": len(manifest.regions),
        "vector_records": len(snapshot["records"]),
        "source_urls": [s.source_url for s in manifest.sources],
        "license_note": "Sources permit redistribution according to the frozen registry; "
                        "keep original scans, watermarks and provenance. AI labels are Inferred.",
    }
    lock_path = root / LOCK
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    lock_path.write_bytes(json_bytes(lock))
    return lock


def restore(root: Path, archive: Path, lock: dict[str, Any]) -> int:
    if digest(archive.read_bytes()) != lock["archive_sha256"]:
        raise ValueError("bundle SHA256 mismatch")
    expected = {e["path"]: e for e in lock["files"]}
    if len(expected) != len(lock["files"]):
        raise ValueError("duplicate lock entries")
    with zipfile.ZipFile(archive) as bundle:
        if len(bundle.namelist()) != len(expected) or set(bundle.namelist()) != set(expected):
            raise ValueError("archive file set does not match lock")
        # Validate the entire archive and existing targets before writing anything.
        for name, entry in expected.items():
            target = safe_target(root, name)
            if bundle.getinfo(name).file_size != entry["size"]:
                raise ValueError("bundle file size mismatch")
            data = bundle.read(name)
            if digest(data) != entry["sha256"]:
                raise ValueError("bundle file hash mismatch")
            if target.exists() and (
                not target.is_file() or digest(target.read_bytes()) != entry["sha256"]
            ):
                raise ValueError("restore would overwrite different existing data")
        for name in expected:
            target = safe_target(root, name)
            if not target.exists():
                target.parent.mkdir(parents=True, exist_ok=True)
                with target.open("xb") as stream, bundle.open(name) as source:
                    shutil.copyfileobj(source, stream)
    manifest_at(root)
    return len(expected)


async def import_vectors(root: Path, settings: Settings) -> int:
    lock = json.loads((root / LOCK).read_text(encoding="utf-8"))
    checkpoint = safe_target(root, SNAPSHOT)
    entry = next(e for e in lock["files"] if e["path"] == SNAPSHOT)
    if digest(checkpoint.read_bytes()) != entry["sha256"]:
        raise ValueError("frozen vector checkpoint hash mismatch")
    snapshot = json.loads(checkpoint.read_text(encoding="utf-8"))
    manifest = manifest_at(root)
    manifest_hash = digest((root / "backend/data/manifests" / MANIFEST).read_bytes())
    if snapshot["manifest_sha256"] != manifest_hash:
        raise ValueError("vector checkpoint bound to a different manifest")
    allowed = entity_ids(manifest)
    providers = ProviderRegistry.create(Settings())
    neural = ProviderRegistry.create(Settings(retrieval_profile="neural"))
    known = {p.provider_name: p for p in (
        providers.text_embedding, providers.image_embedding, neural.text_embedding,
        neural.image_embedding, neural.clip_text,
    ) if p is not None}
    records = snapshot["records"]
    validated = []
    seen = set()
    for r in records:
        entity = UUID(r["entity_id"])
        identity = (entity, r["modality"], r["provider"])
        if identity in seen or allowed.get(entity) != r["entity_type"]:
            raise ValueError("duplicate or out-of-corpus vector")
        seen.add(identity)
        provider = known.get(r["provider"])
        if provider is None:
            raise ValueError("unknown model provider")
        expected_modality = (
            "clip_text" if r["provider"] == "chinese_clip_text"
            else "image" if "image" in r["provider"] else "text"
        )
        if r["modality"] != expected_modality or (
            r["entity_type"] == "region" and expected_modality != "image"
        ):
            raise ValueError("model provider is used for the wrong modality")
        metadata = provider.metadata()
        if any(r[k] != getattr(metadata, k) for k in (
            "provider", "model", "version", "dimension", "preprocessing_hash",
        )):
            raise ValueError("model identity mismatch")
        vector = tuple(float(v) for v in r["vector"])
        if len(vector) != metadata.dimension or not all(math.isfinite(v) for v in vector):
            raise ValueError("invalid frozen vector")
        validated.append((entity, r["entity_type"], r["modality"], VectorResult(vector, metadata)))
    engine = create_async_engine(settings.database_url)
    try:
        async with async_sessionmaker(engine)() as session:
            ids = {stable_id("figure", f.figure_id) for f in manifest.figures}
            existing = (await session.scalars(select(Figure.id).where(Figure.id.in_(ids)))).all()
            if len(existing) != len(ids):
                raise ValueError("import the domestic manifest before restoring its vectors")
            # Same UUIDs are insufficient: changed text/crops must never receive stale vectors.
            figures = [f for f in await list_figures_for_search(session) if f.id in ids]
            validate_locked_figures(
                SearchService(settings.model_copy(update={
                    "asset_root": root / "backend/data/assets",
                })),
                manifest, figures,
            )
            for entity, kind, modality, result in validated:
                await _upsert_embedding(session, entity, kind, modality, result)
            await session.commit()
    finally:
        await engine.dispose()
    return len(validated)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("action", choices=["build", "restore", "import-vectors"])
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--bundle", type=Path)
    parser.add_argument("--output", type=Path, default=Path("D:/codex-releases/AIC-9.2"))
    args = parser.parse_args()
    root = args.root.resolve()
    if args.action == "build":
        manifest = manifest_at(root)
        snapshot = asyncio.run(vectors(Settings(), manifest, root))
        result: Any = build(root, args.output, snapshot)
        print(json.dumps({k: v for k, v in result.items() if k != "files"}, ensure_ascii=False))
    elif args.action == "restore":
        if args.bundle is None:
            parser.error("restore requires --bundle")
        print(restore(root, args.bundle, json.loads((root / LOCK).read_text(encoding="utf-8"))))
    else:
        print(asyncio.run(import_vectors(root, Settings())))


if __name__ == "__main__":
    main()
