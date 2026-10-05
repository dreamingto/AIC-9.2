"""Actual HTTP/model smoke and fixed-case observations; never emits research metrics."""

from __future__ import annotations

import argparse
import io
import json
from pathlib import Path
from typing import Any

import httpx
from PIL import Image

from app.api.v1.demo import DemoCaseResponse
from app.schemas.common import SearchResponse


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", default="http://127.0.0.1:8000")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    report: dict[str, Any] = {"evaluation_status": "not_evaluated", "cases": []}
    with httpx.Client(base_url=args.base_url, timeout=120, trust_env=False) as client:
        capabilities = client.get("/api/v1/capabilities")
        capabilities.raise_for_status()
        report["capabilities"] = capabilities.json()
        providers = {p["provider"] for p in report["capabilities"]["providers"] if p["available"]}
        assert {"bge_zh", "chinese_clip_image", "chinese_clip_text"} <= providers
        response = client.get("/api/v1/demo/cases")
        response.raise_for_status()
        cases = [DemoCaseResponse.model_validate(item) for item in response.json()]
        assert len(cases) == 2 and all(case.ready for case in cases)
        for case in cases:
            observations: dict[str, Any] = {"id": case.id, "queries": {}}
            for mode in ("text", "region", "image"):
                if mode == "image":
                    figure = case.figures[0]
                    assert figure.asset and figure.bbox
                    response = client.get(figure.asset.url)
                    response.raise_for_status()
                    with Image.open(io.BytesIO(response.content)) as image:
                        box = figure.bbox
                        crop = image.crop(
                            (
                                int(box["x"] * image.width),
                                int(box["y"] * image.height),
                                int((box["x"] + box["width"]) * image.width),
                                int((box["y"] + box["height"]) * image.height),
                            )
                        )
                        output = io.BytesIO()
                        crop.save(output, format="PNG")
                        crop.close()
                    response = client.post(
                        "/api/v1/search/image",
                        files={
                            "file": ("demo-crop.png", output.getvalue(), "image/png"),
                        },
                        data={
                            "top_k": "10",
                            "filters": json.dumps(
                                {
                                    "dataset_kinds": ["ai_assisted_real_pilot"],
                                }
                            ),
                        },
                    )
                else:
                    response = client.post(
                        f"/api/v1/demo/cases/{case.id}/search", json={"mode": mode}
                    )
                response.raise_for_status()
                search = SearchResponse.model_validate(response.json())
                assert search.results
                assert all(r.verification_state == "pending" for r in search.results)
                if mode == "region":
                    assert all(r.figure_id != case.figures[0].id for r in search.results)
                repeated = client.get(f"/api/v1/search/{search.search_id}")
                repeated.raise_for_status()
                assert (
                    SearchResponse.model_validate(repeated.json()).model_dump()
                    == search.model_dump()
                )
                observations["queries"][mode] = {
                    "search_id": str(search.search_id),
                    "latency_ms": search.latency_ms,
                    "query_summary": search.query_summary,
                    "ranked_results": [
                        {
                            "figure_id": str(r.figure_id),
                            "title": r.title,
                            "score": r.score,
                            "components": r.score_components.model_dump(),
                        }
                        for r in search.results
                    ],
                }
            report["cases"].append(observations)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps({"cases": len(report["cases"]), "searches": 6, "status": "passed"}))


if __name__ == "__main__":
    main()
