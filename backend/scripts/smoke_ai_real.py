"""Exercise the actual competition corpus through HTTP, without human verification."""

from __future__ import annotations

import argparse
import json
import math
import time
from pathlib import Path
from typing import Any

import httpx

from app.ingestion.contracts import AIRealManifest
from app.ingestion.loader import load_manifest
from app.schemas.common import FigureResponse, SearchResponse
from app.services.ingestion_service import _figure_image_input, stable_id

PROJECT_ROOT = Path(__file__).resolve().parents[2]


def smoke(base_url: str, manifest_name: str) -> dict[str, Any]:
    fixture = load_manifest(
        manifest_name, manifests_root=PROJECT_ROOT / "backend/data/manifests",
        assets_root=PROJECT_ROOT / "backend/data/assets",
    )
    manifest = fixture.manifest
    if not isinstance(manifest, AIRealManifest):
        raise ValueError("smoke requires an explicitly AI-assisted real manifest")
    filters = {"dataset_kinds": ["ai_assisted_real_pilot"]}
    with httpx.Client(base_url=base_url, timeout=30) as client:
        client.get("/api/v1/health").raise_for_status()
        jobs = []
        for _ in range(2):
            created = client.post("/api/v1/ingestion/jobs", json={
                "manifest_name": manifest_name, "dry_run": False,
            })
            created.raise_for_status()
            job_id = created.json()["id"]
            for _poll in range(100):
                status = client.get(f"/api/v1/ingestion/jobs/{job_id}")
                status.raise_for_status()
                job = status.json()
                if job["status"] in {"failed", "completed"}:
                    break
                time.sleep(.2)
            assert job["status"] == "completed", job
            assert job["stats"]["dataset_kind"] == manifest.dataset_kind
            jobs.append(job_id)
        figure = manifest.figures[0]
        figure_id = stable_id("figure", figure.figure_id)
        page_id = stable_id("page", figure.page_id)
        page = client.get(f"/api/v1/pages/{page_id}")
        page.raise_for_status()
        assert page.json()["figures"]
        detail = client.get(f"/api/v1/figures/{figure_id}")
        detail.raise_for_status()
        parsed_figure = FigureResponse.model_validate(detail.json())
        assert not parsed_figure.data_status.human_reviewed
        assert all(c.corrected_text is None for c in parsed_figure.text_chunks)
        assert parsed_figure.asset is not None
        image = client.get(parsed_figure.asset.url)
        image.raise_for_status()
        assert image.content.startswith(b"\x89PNG")
        text = client.post("/api/v1/search/text", json={
            "query": "织机 经线", "top_k": 12, "filters": filters,
        })
        text.raise_for_status()
        again = client.post("/api/v1/search/text", json={
            "query": "织机 经线", "top_k": 12, "filters": filters,
        })
        again.raise_for_status()
        assert [(r["figure_id"], r["score"]) for r in text.json()["results"]] == [
            (r["figure_id"], r["score"]) for r in again.json()["results"]
        ]
        crop = _figure_image_input(fixture, figure)
        assert isinstance(crop, bytes)
        picture = client.post("/api/v1/search/image", files={
            "file": ("domestic-query.png", crop, "image/png"),
        }, data={"top_k": "12", "filters": json.dumps(filters)})
        picture.raise_for_status()
        region = client.post("/api/v1/search/region", json={
            "figure_id": str(figure_id), "bbox": figure.bbox.model_dump(),
            "coordinate_space": "normalized", "top_k": 12, "filters": filters,
        })
        region.raise_for_status()
        searches = []
        for response in (text, picture, region):
            parsed = SearchResponse.model_validate(response.json())
            assert parsed.results and all(math.isfinite(r.score) for r in parsed.results)
            assert all(r.data_status.dataset_kind == manifest.dataset_kind for r in parsed.results)
            assert all(not r.data_status.human_reviewed for r in parsed.results)
            assert all(r.verification_state == "pending" for r in parsed.results)
            assert all(e.status != "Verified" for r in parsed.results for e in r.evidence)
            stored = client.get(f"/api/v1/search/{parsed.search_id}")
            stored.raise_for_status()
            assert stored.json()["results"] == response.json()["results"]
            candidate = client.get(f"/api/v1/associations/{parsed.results[0].candidate_id}")
            candidate.raise_for_status()
            assert candidate.json()["search_id"] == str(parsed.search_id)
            searches.append({
                "type": parsed.query_summary["type"], "search_id": str(parsed.search_id),
                "result_count": len(parsed.results), "latency_ms": parsed.latency_ms,
                "top3": [{"title": r.title, "figure_id": str(r.figure_id), "score": r.score,
                          "source": r.source.model_dump(mode="json")} for r in parsed.results[:3]],
            })
        # Empty independent-human corpus must not be silently replaced by AI data.
        human = client.post("/api/v1/search/text", json={
            "query": "织机", "filters": {"dataset_kinds": ["human_reviewed_real_pilot"]},
        })
        human.raise_for_status()
        assert human.json()["results"] == []
        return {
            "engineering_status": "passed", "manifest_name": manifest_name,
            "dataset_kind": manifest.dataset_kind, "import_counts": fixture.counts,
            "ingestion_job_ids": jobs, "searches": searches,
            "idempotent_import": True, "deterministic_text_ranking": True,
            "human_verification_submitted": False, "evaluation_status": "not_evaluated",
            "research_metrics": None, "figure_url": f"http://localhost/figures/{figure_id}",
            "page_api_url": f"{base_url}/api/v1/pages/{page_id}",
        }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", default="http://127.0.0.1:8000")
    parser.add_argument("--manifest-name", required=True)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    report = smoke(args.base_url, args.manifest_name)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", "utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
