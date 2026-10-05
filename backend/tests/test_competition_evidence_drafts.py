from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path
from typing import Any

import pytest
from PIL import Image

from scripts.annotation_errors import ConversionError
from scripts.prepare_competition_evidence_drafts import active_revision, prepare_evidence_drafts


def _write(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")


def _read(path: Path) -> dict[str, Any]:
    return dict(json.loads(path.read_text(encoding="utf-8")))


@pytest.fixture
def inputs(tmp_path: Path) -> dict[str, Path]:
    revision = tmp_path / "backend/data/real_pilot/review_revisions/test-v2"
    inventory_path = tmp_path / "backend/data/real_pilot/derived_pages.json"
    links_path = tmp_path / "backend/data/real_pilot/links.json"
    pdf = tmp_path / "backend/data/assets/real_pilot_v1/source.pdf"
    pdf.parent.mkdir(parents=True)
    pdf.write_bytes(b"%PDF-1.4 test-only, not an actual historical scan")
    pdf_hash = hashlib.sha256(pdf.read_bytes()).hexdigest()
    bbox = {"x": 0.1, "y": 0.1, "width": 0.2, "height": 0.2}
    pages: list[dict[str, Any]] = []
    inventory: dict[str, Any] = {"dataset_kind": "real_pilot_page_inventory", "pages": []}
    for number in (1, 2):
        page_id = f"source-p{number:04d}"
        image_path = f"backend/data/processed/real_pilot_v1/source/page-{number}.png"
        image = tmp_path / image_path
        image.parent.mkdir(parents=True, exist_ok=True)
        Image.new("RGB", (100, 200), "white").save(image)
        image_hash = hashlib.sha256(image.read_bytes()).hexdigest()
        inventory["pages"].append(
            {
                "page_id": page_id,
                "source_id": "source",
                "image_path": image_path,
                "sha256": image_hash,
                "pdf_page": number,
                "provenance": {
                    "pdf_filename": "source.pdf",
                    "pdf_sha256": pdf_hash,
                    "source_name": "TEST ONLY",
                    "allow_redistribution": True,
                },
            }
        )
        boxes = [
            {
                "box_id": page_id + "-b001",
                "bbox": bbox,
                "raw_text": "圖機花",
                "category_candidate": "caption",
                "role_candidate": "figure_title",
                "reading_order": 1,
                "verification_state": "inferred",
                "original_box_index": 0,
            }
        ]
        if number == 1:
            for index, (text, category, role) in enumerate(
                [
                    ("花樓", "caption", "component_label"),
                    ("提起衝脚梭過之後居然花現", "text", "body"),
                    ("不应被自动附加的另一工序", "text", "body"),
                    ("HAPA", "unknown", "illustration_false_positive"),
                    (None, "text", "body_text"),
                ],
                2,
            ):
                boxes.append(
                    {
                        "box_id": page_id + f"-b{index:03d}",
                        "bbox": bbox,
                        "raw_text": text,
                        "category_candidate": category,
                        "role_candidate": role,
                        "reading_order": index,
                        "original_box_index": index - 1 if text else None,
                        "verification_state": "inferred",
                    }
                )
        pages.append(
            {
                "page_id": page_id,
                "image_path": image_path,
                "image_sha256": image_hash,
                "boxes": boxes,
                "figures": [
                    {
                        "figure_id": page_id + "-f01",
                        "bbox": bbox,
                        "caption_box_id": page_id + "-b001",
                        "verification_state": "inferred",
                    }
                ],
            }
        )
    _write(inventory_path, inventory)
    candidate = {
        "dataset_kind": "real_pilot_model_assisted_review_candidates",
        "evaluation_status": "not_evaluated",
        "source_id": "source",
        "pages": pages,
        "input_hashes": {
            "inventory_sha256": hashlib.sha256(inventory_path.read_bytes()).hexdigest()
        },
    }
    candidate_path = revision / "annotations.candidates.json"
    _write(candidate_path, candidate)
    candidate_hash = hashlib.sha256(candidate_path.read_bytes()).hexdigest()
    scope = {
        "dataset_kind": "competition_evaluation_scope",
        "source_id": "source",
        "source_candidate_sha256": candidate_hash,
        "evaluation_status": "not_evaluated",
        "pages": [
            {
                "page_id": p["page_id"],
                "image_path": p["image_path"],
                "image_sha256": p["image_sha256"],
                "pdf_filename": "source.pdf",
                "pdf_sha256": pdf_hash,
                "box_ids": [b["box_id"] for b in p["boxes"]],
                "figure_ids": [f["figure_id"] for f in p["figures"]],
                "missing_caption_ids": [],
            }
            for p in pages
        ],
    }
    _write(revision / "competition_scope.json", scope)
    records = []
    for page in pages:
        for item in [*page["boxes"], *page["figures"]]:
            kind = "box" if "box_id" in item else "figure"
            item_id = item.get("box_id") or item["figure_id"]
            corrected = item.get("raw_text")
            if item_id.endswith("b001"):
                corrected = "花機圖"
            if item_id.endswith("b005"):
                corrected = None
            if item_id.endswith("b006"):
                corrected = "补框正文建议"
            records.append(
                {
                    "box_or_figure_id": item_id,
                    "page_id": page["page_id"],
                    "kind": kind,
                    "corrected_text": corrected,
                    "category": item.get("category_candidate", "figure"),
                    "role": item.get("role_candidate", "technical_figure"),
                    "raw_text": item.get("raw_text"),
                    "bbox": copy.deepcopy(bbox),
                    "original_bbox": copy.deepcopy(bbox),
                    "reading_order": item.get("reading_order"),
                    "original_reading_order": item.get("reading_order"),
                    "confirmed": True,
                    "review_origin": "ai_assisted",
                    "verification_state": "inferred",
                    "evidence": "scan_level_ai_review",
                    "requires_human_confirmation": True,
                    "reviewer": "test AI",
                    "reviewed_at": "2026-10-05T01:00:00Z",
                    "review_note": "TEST ONLY",
                }
            )
    review = {
        "dataset_kind": "ai_assisted_review_overrides",
        "review_origin": "ai_assisted",
        "evaluation_status": "not_evaluated",
        "source_id": "source",
        "source_candidate_sha256": candidate_hash,
        "input_hashes": candidate["input_hashes"],
        "records": records,
    }
    review_path = revision / "ai.round2.json"
    _write(review_path, review)
    plan = {
        "schema_version": "1.0",
        "dataset_kind": "ai_competition_evidence_link_plan",
        "source_id": "source",
        "source_candidate_sha256": candidate_hash,
        "review_filename": "ai.round2.json",
        "figures": [
            {
                "figure_id": "source-p0001-f01",
                "title_id": "source-p0001-b001",
                "label_ids": ["source-p0001-b002"],
                "contexts": [
                    {
                        "item_ids": ["source-p0001-b003", "source-p0001-b006"],
                        "rationale": "explicit test-only linkage",
                    }
                ],
                "functional_drafts": [
                    {
                        "slot": "operation",
                        "concept": "提综织花",
                        "rationale": "AI suggestion",
                        "supports": [{"item_id": "source-p0001-b003", "quote": "居然花現"}],
                    }
                ],
                "unresolved": ["TEST ONLY"],
            },
            {
                "figure_id": "source-p0002-f01",
                "title_id": "source-p0002-b001",
                "label_ids": [],
                "contexts": [],
                "functional_drafts": [],
                "unresolved": [],
            },
        ],
        "cases": [
            {
                "case_id": "test-case",
                "name": "TEST ONLY",
                "figure_ids": ["source-p0001-f01"],
                "aim": "prepare evidence",
            }
        ],
    }
    _write(links_path, plan)
    return {
        "root": tmp_path,
        "revision": revision,
        "inventory": inventory_path,
        "links": links_path,
        "candidate": candidate_path,
        "review": review_path,
        "pdf": pdf,
    }


def _run(inputs: dict[str, Path]) -> tuple[dict[str, Any], Path]:
    return prepare_evidence_drafts(
        revision_dir=inputs["revision"],
        links_path=inputs["links"],
        inventory_path=inputs["inventory"],
        project_root=inputs["root"],
    )


def test_drafts_preserve_raw_truth_boundaries_and_explicit_links(inputs: dict[str, Path]) -> None:
    before = {k: p.read_bytes() for k, p in inputs.items() if p.is_file()}
    payload, output = _run(inputs)
    assert payload["evaluation_status"] == "not_evaluated"
    assert all(value is None for value in payload["metrics"].values())
    assert payload["statistics"]["human_truth_pages"] == 0
    assert payload["statistics"]["unknown_items"] == 1
    first, second = payload["figures"]
    assert second["contexts"] == []
    ids = [e["item_id"] for context in first["contexts"] for e in context["evidence"]]
    assert ids == ["source-p0001-b003", "source-p0001-b006"]
    supplement = first["contexts"][0]["evidence"][1]
    assert supplement["raw_text"] is None and supplement["text_hint"] == "补框正文建议"
    assert first["functional_drafts"][0]["state"] == "Inferred"
    assert first["functional_drafts"][0]["confidence"] is None
    assert first["functional_drafts"][0]["requires_human_confirmation"] is True
    assert all(q["relevance_grade"] is None for q in payload["query_drafts"])
    assert payload["cases"][0]["relevance_labels"] is None
    assert "不应被自动附加" not in (output / "证据工作表.md").read_text(encoding="utf-8")
    assert all(inputs[k].read_bytes() == content for k, content in before.items())
    assert _run(inputs) == (payload, output)


@pytest.mark.parametrize(
    "field,value",
    [
        ("source_candidate_sha256", "0" * 64),
        ("review_origin", "human"),
        ("input_hashes", {}),
    ],
)
def test_rejects_stale_or_human_review(inputs: dict[str, Path], field: str, value: Any) -> None:
    review = _read(inputs["review"])
    review[field] = value
    _write(inputs["review"], review)
    with pytest.raises(ConversionError, match="origin or input hashes"):
        _run(inputs)


@pytest.mark.parametrize(
    "field,value,pattern",
    [
        ("verification_state", "verified", "checked AI"),
        ("requires_human_confirmation", False, "checked AI"),
        ("confirmed", False, "checked AI"),
        ("raw_text", "FORGED RAW", "preserve original"),
        ("reviewed_at", "2026-10-05", "timezone"),
        ("bbox", {"x": float("nan"), "y": 0, "width": 1, "height": 1}, "non-finite"),
    ],
)
def test_rejects_forged_record_state_and_geometry(
    inputs: dict[str, Path],
    field: str,
    value: Any,
    pattern: str,
) -> None:
    review = _read(inputs["review"])
    review["records"][0][field] = value
    _write(inputs["review"], review)
    with pytest.raises(ConversionError, match=pattern):
        _run(inputs)


def test_rejects_missing_checks_or_incomplete_page_inventory(inputs: dict[str, Path]) -> None:
    original = _read(inputs["review"])
    changed = copy.deepcopy(original)
    changed["records"].pop()
    _write(inputs["review"], changed)
    with pytest.raises(ConversionError, match="all core items"):
        _run(inputs)
    _write(inputs["review"], original)
    scope_path = inputs["revision"] / "competition_scope.json"
    scope = _read(scope_path)
    scope["pages"][0]["box_ids"].pop()
    # Renumbering would still hide a box: scope completeness must be checked separately.
    with pytest.raises(ConversionError, match="inventory"):
        _write(scope_path, scope)
        _run(inputs)


@pytest.mark.parametrize(
    "field,value,pattern",
    [
        ("quote", "不存在的证据", "quote is absent"),
        ("item_id", "source-p0001-b004", "not attached"),
        ("item_id", "source-p0001-b002", "quote is absent"),
    ],
)
def test_function_requires_an_actual_attached_transcription(
    inputs: dict[str, Path],
    field: str,
    value: str,
    pattern: str,
) -> None:
    plan = _read(inputs["links"])
    plan["figures"][0]["functional_drafts"][0]["supports"][0][field] = value
    _write(inputs["links"], plan)
    with pytest.raises(ConversionError, match=pattern):
        _run(inputs)


def test_rejects_cross_page_title_and_unknown_case(inputs: dict[str, Path]) -> None:
    original = _read(inputs["links"])
    changed = copy.deepcopy(original)
    changed["figures"][0]["title_id"] = "source-p0002-b001"
    _write(inputs["links"], changed)
    with pytest.raises(ConversionError, match="local caption"):
        _run(inputs)
    changed = copy.deepcopy(original)
    changed["cases"][0]["figure_ids"] = ["source-p0003-f01"]
    _write(inputs["links"], changed)
    with pytest.raises(ConversionError, match="outside the core"):
        _run(inputs)


def test_rejects_pdf_tampering_and_existing_artifact_overwrite(inputs: dict[str, Path]) -> None:
    payload, output = _run(inputs)
    original_pdf = inputs["pdf"].read_bytes()
    inputs["pdf"].write_bytes(b"changed source PDF")
    with pytest.raises(ConversionError, match="PDF hash"):
        _run(inputs)
    inputs["pdf"].write_bytes(original_pdf)
    artifact = output / "evidence-drafts.json"
    payload["verification_state"] = "verified"
    _write(artifact, payload)
    before = artifact.read_bytes()
    with pytest.raises(ConversionError, match="refusing overwrite"):
        _run(inputs)
    assert artifact.read_bytes() == before


def test_rejects_review_path_and_active_revision_traversal(inputs: dict[str, Path]) -> None:
    plan = _read(inputs["links"])
    plan["review_filename"] = "../other-review.json"
    _write(inputs["links"], plan)
    with pytest.raises(ConversionError, match="basename"):
        _run(inputs)
    pointer = inputs["revision"].parent / "active_revision.json"
    _write(pointer, {"revision_directory": "../outside"})
    with pytest.raises(ConversionError, match="active review revision"):
        active_revision(inputs["root"])


def test_rejects_duplicate_reading_order(inputs: dict[str, Path]) -> None:
    review = _read(inputs["review"])
    review["records"][1]["reading_order"] = 1
    _write(inputs["review"], review)
    with pytest.raises(ConversionError, match="complete permutation"):
        _run(inputs)
