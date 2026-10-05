"""Versioned AI interpretations after visual inspection; never independent ground truth."""
from __future__ import annotations

import json

from app.retrieval.experiments.contracts import EvidencePlan
from app.retrieval.experiments.evidence import bind_drafts
from scripts.release_bundle import ROOT, manifest_at

# These are visible-scene interpretations, not transcriptions or calibrated labels.
SCENES = {
    "ai-zhsy-p22-reeling": {"power_source": ("human", "人力操作轮架"),
                           "object": ("thread", "丝线或纤维"),
                           "purpose": ("textile_production", "纺织相关作业")},
    "ai-zhsy-p23-framework": {"object": ("thread", "丝线或纤维"),
                             "purpose": ("textile_production", "纺织相关作业")},
    "ai-zhsy-p24-threadwork": {"power_source": ("human", "人员在框架旁操作"),
                              "object": ("thread", "丝线或纤维"),
                              "purpose": ("textile_production", "纺织相关作业")},
    "ai-zhsy-p25-warping": {"power_source": ("human", "人力牵引或整理"),
                           "action": ("warping", "排列经线的场景解释"),
                           "object": ("thread", "丝线或纤维"),
                           "purpose": ("textile_production", "纺织相关作业")},
    "ai-zhsy-p25-winding": {"power_source": ("human", "人在架旁操作"),
                           "object": ("thread", "丝线或纤维"),
                           "purpose": ("textile_production", "纺织相关作业")},
    "ai-zhsy-p26-hanging": {"object": ("thread", "悬挂丝束或纤维"),
                           "purpose": ("textile_production", "纺织相关场景")},
    "ai-nlc-p24-fan": {"power_source": ("human", "人力操作轮架"),
                       "motion": ("rotation", "轮轴旋转的功能推断"),
                       "object": ("grain", "待处理物料，谷物解释待核实"),
                       "purpose": ("grain_processing", "谷物加工场景推断")},
    "ai-nlc-p24-huller": {"power_source": ("human", "人力操作杆件"),
                          "motion": ("rotation", "臼状装置旋转的推断"),
                          "object": ("grain", "待处理物料，谷物解释待核实"),
                          "purpose": ("grain_processing", "谷物加工场景推断")},
}


def main() -> None:
    manifest = manifest_at(ROOT)
    folder = ROOT / "backend/data/experiments"
    plan = json.loads((folder / "domestic-functions-v1.json").read_text(encoding="utf-8"))
    plan["plan_id"] = "domestic-full-functions-v2"
    plan["disclaimer"] += (
        " V2新增背景8图：AI已查看原扫描，只对可见场景给出保守草稿；"
        "具体古文图题、器物型号、因果动作仍未核实。覆盖增加不等于准确率提高。"
    )
    for key, claims in SCENES.items():
        region = next(r for r in manifest.regions if r.figure_id == key)
        functions = []
        for slot in ("power_source", "motion", "transmission", "action", "object", "purpose"):
            known = claims.get(slot)
            functions.append({
                "slot": slot, "concept": known[0] if known else "unknown",
                "label": known[1] if known else "未知",
                "rationale": "AI扫描场景解释；非可靠古文引文，非人工标签。"
                if known else "静态低分辨率图不足以确认该功能。",
                "supports": [{"kind": "scan_region", "reference_id": region.region_id,
                              "note": "已查看扫描中的器具、线束或操作者；动态解释仍为推断。"}]
                if known else [],
                "state": "Inferred", "confidence": None,
            })
        plan["figures"].append({
            "figure_key": key, "case_id": "background", "functions": functions,
            "relations": [], "unresolved": [
                "具体工序和装置名称缺少独立古文正文支持，未知槽不补造。",
                "没有独立相关性标签；不得称为正例、困难负例或研究真值。",
            ],
        })
    validated = EvidencePlan.model_validate(plan)
    bound = bind_drafts(validated, manifest)
    assert bound["counts"]["figures"] == 12
    (folder / "domestic-functions-v2.json").write_text(
        json.dumps(plan, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(bound["counts"]))


if __name__ == "__main__":
    main()
