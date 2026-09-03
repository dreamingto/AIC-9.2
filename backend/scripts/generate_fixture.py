#!/usr/bin/env python3
"""Generate the deterministic JiTu V1 synthetic fixture.

The fixture intentionally contains no real scan.  It is an executable,
reproducible contract test for ingestion, retrieval and evidence rendering.
Run from the repository root::

    python backend/scripts/generate_fixture.py

The script writes nine PNGs and one JSON manifest below ``backend/data`` by
default.  Every generated hash is calculated from the final PNG bytes, so a
subsequent loader run can verify the complete asset chain.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_ASSETS = ROOT / "data" / "assets"
DEFAULT_MANIFESTS = ROOT / "data" / "manifests"
FIXTURE_ID = "jitu-fixture-v1"
GENERATOR_VERSION = "fixture-generator-1.0"
GENERATED_AT = datetime(2026, 9, 2, tzinfo=UTC).isoformat()
WIDTH, HEIGHT = 512, 384


FIGURES: list[dict[str, str]] = [
    {
        "id": "fig-water-wheel-01",
        "source": "src-agri-illustrated",
        "title": "水车",
        "caption": "以轮叶承水并连续提灌的水力装置。",
        "family": "wheel",
        "purpose": "提水灌溉",
        "action": "提水",
        "power": "流水",
        "motion": "旋转",
        "transmission": "轮轴传动",
        "object": "农田水面",
    },
    {
        "id": "fig-chain-pump-01",
        "source": "src-agri-illustrated",
        "title": "翻车",
        "caption": "以链板循环提水的连续灌溉器具。",
        "family": "chain",
        "purpose": "提水灌溉",
        "action": "提水",
        "power": "人力",
        "motion": "循环",
        "transmission": "链板传动",
        "object": "农田水面",
    },
    {
        "id": "fig-bucket-wheel-01",
        "source": "src-water-engineering",
        "title": "筒车",
        "caption": "轮周水筒随水流转动，将低处水提升至渠岸。",
        "family": "bucket",
        "purpose": "提水灌溉",
        "action": "提水",
        "power": "流水",
        "motion": "旋转",
        "transmission": "轮周承载",
        "object": "灌渠",
    },
    {
        "id": "fig-loom-01",
        "source": "src-textile-machines",
        "title": "织机",
        "caption": "经纬线交错并由梭具往复完成织造。",
        "family": "loom",
        "purpose": "织造布帛",
        "action": "织造",
        "power": "人力",
        "motion": "往复",
        "transmission": "杆件联动",
        "object": "经纬纱线",
    },
    {
        "id": "fig-spindle-01",
        "source": "src-textile-machines",
        "title": "纺车",
        "caption": "大轮带动锭子旋转，将纤维捻成纱线。",
        "family": "spindle",
        "purpose": "纺纱",
        "action": "纺纱",
        "power": "人力",
        "motion": "旋转",
        "transmission": "带轮传动",
        "object": "纤维束",
    },
    {
        "id": "fig-jacquard-01",
        "source": "src-textile-machines",
        "title": "提花机",
        "caption": "提综机构按纹样选择性升降经线。",
        "family": "jacquard",
        "purpose": "织造纹样",
        "action": "织造",
        "power": "人力",
        "motion": "升降",
        "transmission": "杆件联动",
        "object": "经线",
    },
    {
        "id": "fig-crossbow-01",
        "source": "src-agri-illustrated",
        "title": "连弩",
        "caption": "连续上弦与发射的弩机，用于远射。",
        "family": "crossbow",
        "purpose": "远程发射",
        "action": "发射",
        "power": "人力",
        "motion": "往复",
        "transmission": "杠杆传动",
        "object": "箭矢",
    },
    {
        "id": "fig-cannon-cart-01",
        "source": "src-water-engineering",
        "title": "炮车",
        "caption": "车轮承托炮身并调节发射方向。",
        "family": "wheel",
        "purpose": "火器机动",
        "action": "机动",
        "power": "人力",
        "motion": "平移",
        "transmission": "轮轴承载",
        "object": "炮身",
    },
    {
        "id": "fig-grain-mill-01",
        "source": "src-water-engineering",
        "title": "水碓",
        "caption": "水力驱动杵臼往复舂捣谷物。",
        "family": "mill",
        "purpose": "谷物加工",
        "action": "碾磨",
        "power": "流水",
        "motion": "往复",
        "transmission": "凸轮传动",
        "object": "谷物",
    },
]

SOURCES: list[dict[str, Any]] = [
    {
        "source_id": "src-agri-illustrated",
        "source_url": "https://example.invalid/jitu/source/agri",
        "source_name": "JiTu synthetic source A",
        "book_title": "农政全书（合成示例）",
        "author": "徐光启（示例署名）",
        "era": "明代（示例）",
        "edition": "合成演示版 A",
    },
    {
        "source_id": "src-water-engineering",
        "source_url": "https://example.invalid/jitu/source/water",
        "source_name": "JiTu synthetic source B",
        "book_title": "天工开物（合成示例）",
        "author": "宋应星（示例署名）",
        "era": "明代（示例）",
        "edition": "合成演示版 B",
    },
    {
        "source_id": "src-textile-machines",
        "source_url": "https://example.invalid/jitu/source/textile",
        "source_name": "JiTu synthetic source C",
        "book_title": "纺织图谱（合成示例）",
        "author": "机图索隐研究组（示例署名）",
        "era": "传统工艺（示例）",
        "edition": "合成演示版 C",
    },
]


def _draw_wheel(draw: ImageDraw.ImageDraw, variant: int) -> None:
    center = (175 + variant * 14, 195)
    radius = 72 - variant * 5
    draw.ellipse(
        (center[0] - radius, center[1] - radius, center[0] + radius, center[1] + radius),
        outline="#315b72",
        width=8,
    )
    draw.ellipse(
        (center[0] - 15, center[1] - 15, center[0] + 15, center[1] + 15),
        fill="#d98c3f",
        outline="#315b72",
        width=4,
    )
    for angle in range(0, 360, 45):
        import math

        rad = math.radians(angle)
        end = (center[0] + int(radius * math.cos(rad)), center[1] + int(radius * math.sin(rad)))
        draw.line((center[0], center[1], end[0], end[1]), fill="#315b72", width=4)


def _draw_asset(kind: str, index: int) -> Image.Image:
    image = Image.new("RGB", (WIDTH, HEIGHT), "#f7f1df")
    draw = ImageDraw.Draw(image)
    draw.rectangle((16, 16, WIDTH - 16, HEIGHT - 16), outline="#a65d3c", width=3)
    draw.line((35, 62, WIDTH - 35, 62), fill="#ceb98b", width=2)
    draw.rectangle((42, 90, 470, 330), outline="#d7c79c", width=2)
    if kind == "wheel":
        _draw_wheel(draw, index % 2)
        draw.rectangle((260, 184, 425, 208), fill="#b57848", outline="#5e4233", width=4)
        draw.line((340, 208, 340, 293), fill="#5e4233", width=8)
        draw.ellipse((302, 271, 378, 318), outline="#315b72", width=7)
    elif kind == "chain":
        for cy in (150, 265):
            draw.ellipse((95, cy - 36, 167, cy + 36), outline="#315b72", width=7)
            draw.ellipse((122, cy - 9, 140, cy + 9), fill="#d98c3f")
        draw.line((131, 150, 131, 265), fill="#5e4233", width=7)
        for y in range(164, 260, 19):
            draw.rectangle((121, y, 141, y + 9), fill="#d98c3f", outline="#5e4233")
        draw.line((167, 150, 365, 150), fill="#b57848", width=10)
        draw.line((167, 265, 365, 265), fill="#b57848", width=10)
    elif kind == "bucket":
        _draw_wheel(draw, 0)
        for x, y in ((230, 110), (276, 135), (302, 188), (280, 248), (230, 278)):
            draw.rectangle((x, y, x + 42, y + 22), fill="#d98c3f", outline="#5e4233", width=3)
        draw.line((245, 115, 245, 300), fill="#5e4233", width=5)
    elif kind == "loom":
        draw.rectangle((94, 116, 410, 288), outline="#315b72", width=9)
        draw.line((128, 142, 368, 142), fill="#b57848", width=8)
        draw.line((128, 245, 368, 245), fill="#b57848", width=8)
        for x in range(145, 361, 18):
            draw.line((x, 145, x, 242), fill="#a65d3c", width=2)
        draw.line((150, 188, 355, 188), fill="#315b72", width=10)
        draw.polygon((210, 171, 292, 171, 277, 205, 225, 205), fill="#d98c3f", outline="#5e4233")
    elif kind == "spindle":
        draw.ellipse((95, 150, 245, 300), outline="#315b72", width=9)
        draw.ellipse((143, 199, 197, 253), fill="#d98c3f", outline="#5e4233", width=4)
        draw.line((170, 110, 170, 198), fill="#5e4233", width=9)
        draw.polygon((151, 108, 189, 108, 170, 68), fill="#315b72")
        draw.line((197, 226, 392, 226), fill="#b57848", width=7)
    elif kind == "crossbow":
        draw.line((96, 205, 394, 205), fill="#5e4233", width=12)
        draw.line((175, 112, 175, 295), fill="#315b72", width=10)
        draw.line((95, 138, 254, 138), fill="#315b72", width=8)
        draw.line((95, 272, 254, 272), fill="#315b72", width=8)
        draw.rectangle((250, 179, 348, 231), fill="#d98c3f", outline="#5e4233", width=4)
        for x in (275, 305, 335):
            draw.line((x, 184, x, 226), fill="#5e4233", width=3)
    elif kind == "mill":
        draw.ellipse((104, 125, 255, 276), outline="#315b72", width=9)
        draw.ellipse((146, 167, 213, 234), fill="#d98c3f", outline="#5e4233", width=4)
        draw.line((213, 200, 395, 200), fill="#b57848", width=13)
        draw.rectangle((355, 136, 414, 264), outline="#5e4233", width=7)
        draw.line((363, 150, 406, 250), fill="#315b72", width=5)
    else:
        # The remaining loom variant is the patterned-jacquard fixture.
        draw.rectangle((92, 110, 420, 290), outline="#315b72", width=9)
        for x in range(125, 400, 23):
            draw.line((x, 130, x, 270), fill="#a65d3c", width=3)
        for y in range(145, 270, 24):
            draw.line((115, y, 400, y), fill="#d98c3f", width=4)
        draw.line((175, 90, 175, 130), fill="#5e4233", width=7)
        draw.line((337, 90, 337, 130), fill="#5e4233", width=7)
    return image


def _asset_bytes(path: Path) -> tuple[str, int, int]:
    data = path.read_bytes()
    with Image.open(path) as image:
        size = image.size
    return hashlib.sha256(data).hexdigest(), size[0], size[1]


def _source(source: dict[str, Any]) -> dict[str, Any]:
    redistribution_restricted = source["source_id"] == "src-textile-machines"
    return {
        **source,
        "volume": "示例卷",
        "page_or_folio": "见各页",
        "license_status": "synthetic_fixture",
        "license_note": (
            "纯合成示例；此来源用于资源许可限制流程演示，不允许通过公开接口再分发。"
            if redistribution_restricted
            else "纯合成示例，禁止作为真实古籍研究结论；仅用于软件流程演示。"
        ),
        "allow_training": True,
        "allow_redistribution": not redistribution_restricted,
        "retrieved_at": GENERATED_AT,
        "pipeline_version": "jitu-ingestion-contract-1.0",
    }


def build_manifest(assets_root: Path) -> dict[str, Any]:
    assets: list[dict[str, Any]] = []
    pages: list[dict[str, Any]] = []
    figures: list[dict[str, Any]] = []
    regions: list[dict[str, Any]] = []
    text_chunks: list[dict[str, Any]] = []
    evidence: list[dict[str, Any]] = []
    assertions: list[dict[str, Any]] = []
    relations: list[dict[str, Any]] = []

    for index, figure in enumerate(FIGURES, start=1):
        figure_id = figure["id"]
        asset_id = f"asset-{figure_id}"
        page_id = f"page-{figure_id}"
        relative_path = f"fixture_v1/{figure_id}.png"
        # Build from POSIX manifest segments so generation works on Windows
        # and in the Linux-based backend container alike.
        asset_path = assets_root.joinpath(*relative_path.split("/"))
        asset_path.parent.mkdir(parents=True, exist_ok=True)
        image = _draw_asset(figure["family"], index)
        # Explicit PNG options keep bytes stable across repeated generation.
        image.save(asset_path, format="PNG", optimize=False, compress_level=9)
        digest, width, height = _asset_bytes(asset_path)
        assets.append(
            {
                "asset_id": asset_id,
                "relative_path": relative_path,
                "mime_type": "image/png",
                "sha256": digest,
                "width": width,
                "height": height,
            }
        )
        pages.append(
            {
                "page_id": page_id,
                "source_id": figure["source"],
                "volume": f"示例卷{(index - 1) // 3 + 1}",
                "page_or_folio": f"folio-{index:02d}",
            }
        )
        figures.append(
            {
                "figure_id": figure_id,
                "page_id": page_id,
                "asset_id": asset_id,
                "title": figure["title"],
                "caption": figure["caption"],
                "bbox": {"x": 0.08, "y": 0.18, "width": 0.84, "height": 0.63},
                "original_path": relative_path,
            }
        )
        # Exactly two regions per figure make the intended 18-region fixture
        # explicit and useful for region-search demos.
        regions.extend(
            [
                {
                    "region_id": f"region-{figure_id}-drive",
                    "figure_id": figure_id,
                    "label": "主动部件",
                    "role": "动力输入",
                    "bbox": {"x": 0.16, "y": 0.28, "width": 0.30, "height": 0.34},
                    "evidence_state": "Observed",
                },
                {
                    "region_id": f"region-{figure_id}-work",
                    "figure_id": figure_id,
                    "label": "工作部件",
                    "role": "作用输出",
                    "bbox": {"x": 0.53, "y": 0.30, "width": 0.28, "height": 0.30},
                    "evidence_state": "Observed",
                },
            ]
        )
        title_id = f"text-{figure_id}-title"
        context_id = f"text-{figure_id}-context"
        text_chunks.extend(
            [
                {
                    "text_id": title_id,
                    "figure_id": figure_id,
                    "kind": "title",
                    "content": figure["title"],
                    "evidence_state": "Documented",
                },
                {
                    "text_id": context_id,
                    "figure_id": figure_id,
                    "kind": "context",
                    "content": (
                        f"{figure['caption']} 动力为{figure['power']}，"
                        f"运动形式为{figure['motion']}，用于{figure['purpose']}。"
                    ),
                    "evidence_state": "Documented",
                },
            ]
        )
        image_evidence_id = f"evidence-{figure_id}-image"
        text_evidence_id = f"evidence-{figure_id}-text"
        metadata_evidence_id = f"evidence-{figure_id}-metadata"
        evidence.extend(
            [
                {
                    "evidence_id": image_evidence_id,
                    "figure_id": figure_id,
                    "kind": "image",
                    "state": "Observed",
                    "source_ref": asset_id,
                    "excerpt": "合成线稿中的轮轴、杆件或工作部件。",
                },
                {
                    "evidence_id": text_evidence_id,
                    "figure_id": figure_id,
                    "kind": "text",
                    "state": "Documented",
                    "source_ref": context_id,
                    "excerpt": figure["caption"],
                },
                {
                    "evidence_id": metadata_evidence_id,
                    "figure_id": figure_id,
                    "kind": "metadata",
                    "state": "Documented",
                    "source_ref": figure["source"],
                    "excerpt": "来源、卷次和版本均为合成 provenance。",
                },
            ]
        )
        slot_values = {
            "power_source": figure["power"],
            "transmission": figure["transmission"],
            "motion": figure["motion"],
            "action": figure["action"],
            "object": figure["object"],
            "purpose": figure["purpose"],
        }
        for slot, concept in slot_values.items():
            state = "Documented" if slot in {"power_source", "purpose"} else "Inferred"
            assertions.append(
                {
                    "assertion_id": f"assertion-{figure_id}-{slot}",
                    "figure_id": figure_id,
                    "slot": slot,
                    "concept": concept,
                    "confidence": 0.94 if state == "Documented" else 0.78,
                    "evidence_ids": [text_evidence_id, image_evidence_id],
                    "state": state,
                }
            )
        relations.append(
            {
                "relation_id": f"relation-{figure_id}-main",
                "figure_id": figure_id,
                "subject": "主动部件",
                "predicate": "transmits",
                "object": "工作部件",
                "confidence": 0.83,
                "evidence_ids": [image_evidence_id, text_evidence_id],
                "state": "Inferred",
            }
        )

    # Pairs are deliberately balanced across positive and hard-negative labels.
    pair_specs = [
        ("fig-water-wheel-01", "fig-chain-pump-01", "same_function", "均用于提水灌溉"),
        ("fig-chain-pump-01", "fig-bucket-wheel-01", "same_function", "均以连续运动提水"),
        ("fig-loom-01", "fig-spindle-01", "related_mechanism", "均以人力驱动纺织流程"),
        ("fig-loom-01", "fig-jacquard-01", "same_function", "均作用于经纬线织造"),
        ("fig-water-wheel-01", "fig-bucket-wheel-01", "related_mechanism", "均采用轮周承水"),
        ("fig-spindle-01", "fig-jacquard-01", "related_mechanism", "均以纺织机构完成连续工艺"),
        (
            "fig-water-wheel-01",
            "fig-loom-01",
            "similar_form_different_function",
            "均有轮状/框架轮廓但作用对象不同",
        ),
        (
            "fig-chain-pump-01",
            "fig-cannon-cart-01",
            "similar_form_different_function",
            "均出现轮件但一个提水一个承炮",
        ),
        (
            "fig-spindle-01",
            "fig-crossbow-01",
            "similar_form_different_function",
            "均有细长杆件但用途不同",
        ),
        (
            "fig-cannon-cart-01",
            "fig-grain-mill-01",
            "similar_form_different_function",
            "均有轮轴但分别用于机动与加工",
        ),
        (
            "fig-crossbow-01",
            "fig-jacquard-01",
            "similar_form_different_function",
            "杆件布局相似但作用对象不同",
        ),
        ("fig-bucket-wheel-01", "fig-grain-mill-01", "related_mechanism", "均将水力转为机械运动"),
    ]
    evidence_by_figure = {figure["id"]: f"evidence-{figure['id']}-text" for figure in FIGURES}
    benchmark_pairs = []
    for index, (query_id, candidate_id, label, rationale) in enumerate(pair_specs, start=1):
        benchmark_pairs.append(
            {
                "pair_id": f"pair-{index:02d}",
                "query_figure_id": query_id,
                "candidate_figure_id": candidate_id,
                "label": label,
                "rationale": rationale,
                "evidence_ids": [evidence_by_figure[query_id], evidence_by_figure[candidate_id]],
            }
        )

    return {
        "schema_version": "1.0",
        "fixture_id": FIXTURE_ID,
        "title": "机图索隐 V1 离线合成夹具",
        "description": "用于验证导入、证据链和跨图关联检索流程的可复现合成数据。",
        "dataset_kind": "synthetic_fixture",
        "evaluation_status": "not_evaluated",
        "generated_at": GENERATED_AT,
        "generator_version": GENERATOR_VERSION,
        "disclaimer": (
            "Synthetic fixture only; evaluation_status=not_evaluated，不得作为真实古籍研究结论。"
        ),
        "sources": [_source(source) for source in SOURCES],
        "assets": assets,
        "pages": pages,
        "figures": figures,
        "regions": regions,
        "text_chunks": text_chunks,
        "evidence": evidence,
        "functional_assertions": assertions,
        "relations": relations,
        "benchmark_pairs": benchmark_pairs,
    }


def generate(
    *, assets_root: Path = DEFAULT_ASSETS, manifests_root: Path = DEFAULT_MANIFESTS
) -> Path:
    assets_root = assets_root.resolve()
    manifests_root = manifests_root.resolve()
    assets_root.mkdir(parents=True, exist_ok=True)
    manifests_root.mkdir(parents=True, exist_ok=True)
    manifest = build_manifest(assets_root)
    path = manifests_root / f"{FIXTURE_ID}.json"
    path.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=False) + "\n",
        encoding="utf-8",
    )
    return path


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--assets-root", type=Path, default=DEFAULT_ASSETS)
    parser.add_argument("--manifests-root", type=Path, default=DEFAULT_MANIFESTS)
    args = parser.parse_args()
    path = generate(assets_root=args.assets_root, manifests_root=args.manifests_root)
    print(path)


if __name__ == "__main__":
    main()
