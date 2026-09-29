#!/usr/bin/env python3
"""Exercise the running JiTu full-stack API through the Nginx entry point.

This is an engineering smoke test for the synthetic fixture. It does not
measure retrieval quality and must not be reported as a research evaluation.
"""

from __future__ import annotations

import argparse
import json
import math
import sys
import time
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

DEFAULT_BASE_URL = "http://127.0.0.1"
DEFAULT_FIXTURE_IMAGE = (
    Path(__file__).resolve().parents[1]
    / "data"
    / "assets"
    / "fixture_v1"
    / "fig-bucket-wheel-01.png"
)


class SmokeFailure(RuntimeError):
    """Raised when a full-stack smoke assertion fails."""


@dataclass(frozen=True)
class RawResponse:
    status: int
    content_type: str
    body: bytes


class APIClient:
    def __init__(self, base_url: str, timeout: float) -> None:
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

    def raw(
        self,
        method: str,
        path: str,
        *,
        body: bytes | None = None,
        headers: dict[str, str] | None = None,
    ) -> RawResponse:
        request = Request(
            f"{self.base_url}{path}",
            data=body,
            method=method,
            headers={"Accept": "application/json", **(headers or {})},
        )
        try:
            with urlopen(request, timeout=self.timeout) as response:
                return RawResponse(
                    status=response.status,
                    content_type=response.headers.get("Content-Type", ""),
                    body=response.read(),
                )
        except HTTPError as error:
            return RawResponse(
                status=error.code,
                content_type=error.headers.get("Content-Type", ""),
                body=error.read(),
            )
        except URLError as error:
            raise SmokeFailure(f"Cannot reach {request.full_url}: {error.reason}") from error

    def json(
        self,
        method: str,
        path: str,
        *,
        payload: dict[str, Any] | None = None,
        expected_status: int = 200,
    ) -> dict[str, Any]:
        body = None
        headers: dict[str, str] = {}
        if payload is not None:
            body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
            headers["Content-Type"] = "application/json"
        response = self.raw(method, path, body=body, headers=headers)
        if response.status != expected_status:
            detail = response.body.decode("utf-8", errors="replace")[:500]
            raise SmokeFailure(
                f"{method} {path} returned {response.status}, expected "
                f"{expected_status}: {detail}"
            )
        try:
            value = json.loads(response.body)
        except json.JSONDecodeError as error:
            raise SmokeFailure(f"{method} {path} returned invalid JSON") from error
        if not isinstance(value, dict):
            raise SmokeFailure(f"{method} {path} did not return a JSON object")
        return value


def require(condition: bool, message: str) -> None:
    if not condition:
        raise SmokeFailure(message)


def require_object(value: object, message: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise SmokeFailure(message)
    return value


def require_object_list(value: object, message: str) -> list[dict[str, Any]]:
    if not isinstance(value, list) or not value:
        raise SmokeFailure(message)
    objects: list[dict[str, Any]] = []
    for item in value:
        if not isinstance(item, dict):
            raise SmokeFailure(message)
        objects.append(item)
    return objects


def multipart_body(
    fields: dict[str, str], fixture_image: Path
) -> tuple[bytes, str]:
    boundary = f"jitu-smoke-{uuid.uuid4().hex}"
    chunks: list[bytes] = []
    for name, value in fields.items():
        chunks.extend(
            [
                f"--{boundary}\r\n".encode(),
                f'Content-Disposition: form-data; name="{name}"\r\n\r\n'.encode(),
                value.encode("utf-8"),
                b"\r\n",
            ]
        )
    chunks.extend(
        [
            f"--{boundary}\r\n".encode(),
            (
                'Content-Disposition: form-data; name="file"; '
                f'filename="{fixture_image.name}"\r\n'
            ).encode(),
            b"Content-Type: image/png\r\n\r\n",
            fixture_image.read_bytes(),
            b"\r\n",
            f"--{boundary}--\r\n".encode(),
        ]
    )
    return b"".join(chunks), f"multipart/form-data; boundary={boundary}"


def assert_search(response: dict[str, Any], search_type: str) -> list[dict[str, Any]]:
    summary = require_object(
        response.get("query_summary"), f"{search_type} search has no query_summary"
    )
    require(summary.get("type") == search_type, f"Unexpected {search_type} query summary")
    results = require_object_list(
        response.get("results"), f"{search_type} search returned no results"
    )
    for result in results:
        score = result.get("score")
        require(
            isinstance(score, (int, float)) and math.isfinite(score),
            f"{search_type} result has a non-finite score",
        )
        require(bool(result.get("candidate_id")), f"{search_type} result lacks candidate_id")
        require(bool(result.get("figure_id")), f"{search_type} result lacks figure_id")
    return results


def wait_for_ingestion(client: APIClient, job_id: str) -> dict[str, Any]:
    for _ in range(50):
        job = client.json("GET", f"/api/v1/ingestion/jobs/{job_id}")
        if job.get("status") == "completed":
            return job
        if job.get("status") == "failed":
            raise SmokeFailure(f"Fixture ingestion failed: {job.get('error_message')}")
        time.sleep(0.1)
    raise SmokeFailure("Fixture ingestion did not complete within 5 seconds")


def run_smoke(client: APIClient, fixture_image: Path) -> dict[str, Any]:
    require(fixture_image.is_file(), f"Fixture image not found: {fixture_image}")

    health = client.json("GET", "/api/v1/health")
    require(health.get("status") == "ok", "Backend health is not ok")
    require(health.get("database") == "ok", "Database health is not ok")

    capabilities = client.json("GET", "/api/v1/capabilities")
    search_types = capabilities.get("search_types")
    require(
        isinstance(search_types, list) and {"text", "image", "region"} <= set(search_types),
        "Capabilities do not expose all three search types",
    )
    providers = require_object_list(
        capabilities.get("providers"), "No providers were reported"
    )
    require(
        all(item.get("available") for item in providers),
        "At least one provider is unavailable",
    )

    ingestion = client.json(
        "POST",
        "/api/v1/ingestion/jobs",
        payload={"manifest_name": "jitu-fixture-v1.json", "dry_run": False},
        expected_status=202,
    )
    job_id = ingestion.get("id")
    if not isinstance(job_id, str):
        raise SmokeFailure("Ingestion response lacks a job id")
    completed_job = wait_for_ingestion(client, job_id)

    books_response = client.raw("GET", "/api/v1/books")
    require(books_response.status == 200, "Book catalog request failed")
    books_value = json.loads(books_response.body)
    if not isinstance(books_value, list):
        raise SmokeFailure("Book catalog did not return a list")
    books = books_value
    require(len(books) == 3, "Fixture catalog must contain 3 books")

    filters: dict[str, Any] = {"book_ids": [], "edition_ids": []}
    text_search = client.json(
        "POST",
        "/api/v1/search/text",
        payload={"query": "提水", "top_k": 50, "filters": filters},
    )
    text_results = assert_search(text_search, "text")

    image_body, image_content_type = multipart_body(
        {"top_k": "10", "filters": json.dumps(filters)}, fixture_image
    )
    image_raw = client.raw(
        "POST",
        "/api/v1/search/image",
        body=image_body,
        headers={"Content-Type": image_content_type},
    )
    require(image_raw.status == 200, f"Image search returned {image_raw.status}")
    image_search = json.loads(image_raw.body)
    require(isinstance(image_search, dict), "Image search did not return an object")
    image_results = assert_search(image_search, "image")

    source_figure_id = text_results[0]["figure_id"]
    region_search = client.json(
        "POST",
        "/api/v1/search/region",
        payload={
            "figure_id": source_figure_id,
            "bbox": {"x": 0.0, "y": 0.0, "width": 0.5, "height": 0.5},
            "coordinate_space": "normalized",
            "top_k": 10,
            "filters": filters,
        },
    )
    region_results = assert_search(region_search, "region")
    region_summary = require_object(
        region_search.get("query_summary"), "Region search has no query_summary"
    )
    require(
        region_summary.get("source_figure_id") == source_figure_id,
        "Region search did not preserve its source figure",
    )

    search_id = text_search.get("search_id")
    require(isinstance(search_id, str), "Text search lacks search_id")
    stored_search = client.json("GET", f"/api/v1/search/{search_id}")
    require(len(stored_search.get("results", [])) == len(text_results), "Stored search changed")

    candidate_id = text_results[0]["candidate_id"]
    candidate = client.json("GET", f"/api/v1/associations/{candidate_id}")
    require(candidate.get("candidate_id") == candidate_id, "Candidate lookup returned another id")
    note = f"full-stack smoke {uuid.uuid4().hex[:8]}"
    verification = client.json(
        "POST",
        f"/api/v1/associations/{candidate_id}/verify",
        payload={"state": "worth_comparing", "note": note},
    )
    require(verification.get("state") == "worth_comparing", "Verification state was not saved")
    require(verification.get("note") == note, "Verification note was not saved")
    verified_candidate = client.json("GET", f"/api/v1/associations/{candidate_id}")
    require(
        verified_candidate.get("verification_state") == "worth_comparing",
        "Candidate did not expose the saved verification state",
    )

    asset_refs = [item.get("image_ref") for item in text_results]
    allowed = next(
        (
            item
            for item in asset_refs
            if isinstance(item, dict) and item.get("allow_redistribution")
        ),
        None,
    )
    restricted = next(
        (
            item
            for item in asset_refs
            if isinstance(item, dict) and not item.get("allow_redistribution")
        ),
        None,
    )
    if allowed is None:
        raise SmokeFailure("No redistributable fixture asset was returned")
    if restricted is None:
        raise SmokeFailure("No restricted fixture asset was returned")

    allowed_asset = client.raw("GET", allowed["url"])
    require(allowed_asset.status == 200, "Redistributable asset did not return 200")
    require(allowed_asset.body.startswith(b"\x89PNG\r\n\x1a\n"), "Allowed asset is not PNG")

    restricted_asset = client.raw("GET", restricted["url"])
    require(restricted_asset.status == 403, "Restricted asset did not return 403")
    restricted_error = require_object(
        json.loads(restricted_asset.body), "Restricted asset error is not an object"
    )
    error_detail = require_object(
        restricted_error.get("error"), "Restricted asset error has no envelope"
    )
    require(
        error_detail.get("code") == "LICENSE_RESTRICTED",
        "Restricted asset did not use LICENSE_RESTRICTED",
    )

    return {
        "status": "passed",
        "evaluation_status": "not_evaluated",
        "ingestion_job_id": job_id,
        "ingestion_stats": completed_job.get("stats"),
        "books": len(books),
        "providers": len(providers),
        "text_results": len(text_results),
        "image_results": len(image_results),
        "region_results": len(region_results),
        "candidate_id": candidate_id,
        "license_checks": {"allowed": 200, "restricted": 403},
        "verification_state": verified_candidate.get("verification_state"),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", default=DEFAULT_BASE_URL)
    parser.add_argument("--fixture-image", type=Path, default=DEFAULT_FIXTURE_IMAGE)
    parser.add_argument("--timeout", type=float, default=15.0)
    args = parser.parse_args()

    try:
        result = run_smoke(APIClient(args.base_url, args.timeout), args.fixture_image.resolve())
    except (SmokeFailure, OSError, ValueError, json.JSONDecodeError) as error:
        print(f"full-stack smoke failed: {error}", file=sys.stderr)
        return 1

    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
