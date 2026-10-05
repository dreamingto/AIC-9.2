"""Freeze a read-only corpus, bind scan evidence and run fixed retrieval comparisons."""

from __future__ import annotations

import argparse
import asyncio
import json
import platform
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from uuid import uuid4

from sqlalchemy import text
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.core.config import Settings
from app.ingestion.contracts import AIRealManifest
from app.ingestion.loader import load_manifest
from app.repositories.catalog import list_figures_for_search
from app.retrieval.experiments.comparison import (
    DRAFT_RELIABILITY,
    VERSION,
    ComparisonRunner,
    corpus_snapshot,
    experiment_cfr,
)
from app.retrieval.experiments.contracts import METHODS, EvidencePlan, QueryProtocol
from app.retrieval.experiments.evidence import (
    bind_drafts,
    canonical_hash,
    draft_markdown,
    file_hash,
    immutable_write,
    json_bytes,
)
from app.retrieval.experiments.report import comparison_markdown, summarize
from app.services.ingestion_service import stable_id
from app.services.search_service import SearchService

ROOT = Path(__file__).resolve().parents[1]


async def run_comparison(
    settings: Settings,
    protocol_path: Path,
    plan_path: Path,
) -> dict[str, Any]:
    if settings.retrieval_profile != "neural":
        raise ValueError("real comparison requires neural providers; no baseline fallback")
    protocol = QueryProtocol.model_validate_json(protocol_path.read_text(encoding="utf-8"))
    plan = EvidencePlan.model_validate_json(plan_path.read_text(encoding="utf-8"))
    implementation_files = [
        Path(__file__),
        *sorted((ROOT / "app/retrieval/experiments").glob("*.py")),
        ROOT / "app/retrieval/rerank/scoring.py",
        ROOT / "app/services/search_service.py",
        ROOT / "app/retrieval/evidence/spatial.py",
        ROOT / "app/core/config.py",
        ROOT / "app/retrieval/cfr/rule_based.py",
        ROOT / "app/retrieval/baseline/bm25.py",
        ROOT / "app/retrieval/providers/neural.py",
        ROOT / "app/retrieval/providers/model_contract.py",
    ]
    implementation_hashes = {
        p.relative_to(ROOT).as_posix(): file_hash(p) for p in implementation_files
    }
    manifest_path = settings.manifest_root / protocol.manifest_name
    if file_hash(manifest_path) != protocol.manifest_sha256.lower():
        raise ValueError("fixed protocol manifest hash mismatch")
    validated = load_manifest(
        protocol.manifest_name,
        manifests_root=settings.manifest_root,
        assets_root=settings.asset_root,
    )
    manifest = validated.manifest
    if not isinstance(manifest, AIRealManifest):
        raise ValueError("this protocol only accepts the locked AI real corpus")
    drafts = bind_drafts(plan, manifest)
    service = SearchService(settings)
    health = await asyncio.to_thread(service.providers.health)
    if not all(p.available for p in health):
        raise ValueError("selected model service unavailable or wrong model identity")
    engine = create_async_engine(settings.database_url)
    started = time.perf_counter()
    try:
        async with async_sessionmaker(engine, expire_on_commit=False)() as session:
            await session.execute(
                text("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ, READ ONLY")
            )
            if (await session.execute(text("SHOW transaction_read_only"))).scalar() != "on":
                raise ValueError("database transaction must be read-only")
            keys = {f.figure_id: stable_id("figure", f.figure_id) for f in manifest.figures}
            figures = [f for f in await list_figures_for_search(session) if f.id in keys.values()]
            vectors, snapshot = await corpus_snapshot(session, service, manifest, figures)
            runner = ComparisonRunner(settings, figures, vectors, drafts, keys, service)
            preload_ms = (time.perf_counter() - started) * 1000
            records: list[dict[str, Any]] = []
            for query in protocol.queries:
                for method in METHODS:
                    try:
                        first = await runner.run(query, method, protocol.top_k)
                        if first["status"] == "completed":
                            repeated = [
                                await runner.run(query, method, protocol.top_k)
                                for _ in range(protocol.warm_repeats)
                            ]
                            first["warm_latency_ms"] = [r["latency_ms"] for r in repeated]
                            first["warm_feature_ms"] = [r["feature_ms"] for r in repeated]
                            first["warm_ranking_ms"] = [r["ranking_ms"] for r in repeated]
                            first["repeat_signatures"] = [r["ranking_sha256"] for r in repeated]
                            first["repeat_stable"] = all(
                                r["ranking_sha256"] == first["ranking_sha256"] for r in repeated
                            )
                        records.append(first)
                    except Exception as exc:
                        # No synthetic or prior result replaces a failed real query.
                        records.append(
                            {
                                "query_id": query.id,
                                "method": method,
                                "status": "failed",
                                "reason": type(exc).__name__,
                            }
                        )
                print(f"completed {query.id} ({query.kind})", flush=True)
            await session.rollback()
    finally:
        await engine.dispose()
    protocol_hash, plan_hash = file_hash(protocol_path), file_hash(plan_path)
    input_fingerprint = canonical_hash(
        {
            "version": VERSION,
            "protocol_sha256": protocol_hash,
            "plan_sha256": plan_hash,
            "manifest_sha256": protocol.manifest_sha256,
            "corpus_sha256": snapshot["sha256"],
            "draft_sha256": canonical_hash(drafts),
            "weights": service.weights.as_dict(),
            "function_reliability": DRAFT_RELIABILITY,
            "experiment_vocabulary_sha256": canonical_hash(experiment_cfr()._vocabulary),
            "implementation_hashes": implementation_hashes,
        }
    )
    return {
        "runner_version": VERSION,
        "protocol_id": protocol.protocol_id,
        "generated_at": datetime.now(UTC).isoformat(),
        "input_fingerprint": input_fingerprint,
        "input_hashes": {
            "protocol": protocol_hash,
            "plan": plan_hash,
            "manifest": protocol.manifest_sha256,
        },
        "implementation_hashes": implementation_hashes,
        "environment": {"python": platform.python_version(), "platform": platform.platform()},
        "preload_ms": preload_ms,
        "database_transaction": "repeatable-read/read-only/rollback",
        "database_records_changed": False,
        "evaluation_status": "not_evaluated",
        "models": [p.as_dict() for p in health],
        "corpus": snapshot,
        "drafts": drafts,
        "weights": service.weights.as_dict(),
        "draft_reliability_policy": DRAFT_RELIABILITY,
        "queries": [q.model_dump(mode="json") for q in protocol.queries],
        "records": records,
        "summary": summarize(records),
    }


def save_report(report: dict[str, Any], output_root: Path) -> Path:
    stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    fingerprint = str(report["input_fingerprint"])
    directory = output_root / fingerprint[:16] / f"{stamp}-{uuid4().hex[:8]}"
    for name, content in {
        "comparison.json": json_bytes(report),
        "comparison.md": comparison_markdown(report).encode("utf-8"),
        "corpus-lock.json": json_bytes(report["corpus"]),
        "function-evidence-drafts.json": json_bytes(report["drafts"]),
        "function-evidence-drafts.md": draft_markdown(report["drafts"]).encode("utf-8"),
    }.items():
        immutable_write(directory / name, content)
    return directory


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--protocol", type=Path, default=ROOT / "data/experiments/domestic-queries-v2.json"
    )
    parser.add_argument(
        "--plan", type=Path, default=ROOT / "data/experiments/domestic-functions-v2.json"
    )
    parser.add_argument(
        "--output-root", type=Path, default=ROOT / "data/real_pilot/retrieval_comparison"
    )
    parser.add_argument("--service-url", default="http://127.0.0.1:8767")
    args = parser.parse_args()
    settings = Settings(
        retrieval_profile="neural",
        model_service_url=args.service_url,
        manifest_root=ROOT / "data/manifests",
        asset_root=ROOT / "data/assets",
    )
    report = asyncio.run(run_comparison(settings, args.protocol, args.plan))
    directory = save_report(report, args.output_root)
    failed = sum(r["status"] == "failed" for r in report["records"])
    unstable = sum(not r["repeat_stable"] for r in report["records"] if r["status"] == "completed")
    print(
        json.dumps(
            {
                "output_directory": str(directory),
                "failed": failed,
                "unstable": unstable,
                "input_fingerprint": report["input_fingerprint"],
                "evaluation_status": "not_evaluated",
            },
            ensure_ascii=False,
        ),
        flush=True,
    )
    return 1 if failed or unstable else 0


if __name__ == "__main__":
    raise SystemExit(main())
