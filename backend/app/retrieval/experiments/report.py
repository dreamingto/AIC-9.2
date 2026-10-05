from __future__ import annotations

import statistics
from typing import Any

from app.retrieval.experiments.contracts import METHODS


def summarize(records: list[dict[str, Any]]) -> dict[str, Any]:
    methods: dict[str, Any] = {}
    for method in METHODS:
        rows = [r for r in records if r["method"] == method]
        done = [r for r in rows if r["status"] == "completed"]
        times = [float(t) for r in done for t in r["warm_latency_ms"]]
        methods[method] = {
            "completed": len(done),
            "failed": sum(r["status"] == "failed" for r in rows),
            "not_applicable": sum(r["status"] == "not_applicable" for r in rows),
            "stable_repeat_count": sum(r["repeat_stable"] for r in done),
            "warm_sample_count": len(times),
            "warm_median_ms": statistics.median(times) if times else None,
            "warm_min_ms": min(times) if times else None,
            "warm_max_ms": max(times) if times else None,
            "first_pass_median_ms": statistics.median(float(r["latency_ms"]) for r in done)
            if done
            else None,
        }
    by_query = {(r["query_id"], r["method"]): r for r in records}
    observations: list[dict[str, Any]] = []
    for query_id in sorted({r["query_id"] for r in records}):
        left, right = by_query.get((query_id, "hybrid")), by_query.get((query_id, "eafr_drafts"))
        if left and right and left["status"] == right["status"] == "completed":
            a = [r["figure_id"] for r in left["results"]]
            b = [r["figure_id"] for r in right["results"]]
            observations.append(
                {
                    "query_id": query_id,
                    "top1_changed": a[:1] != b[:1],
                    "top_k_order_changed": a != b,
                    "top1_before": left["results"][:1],
                    "top1_after": right["results"][:1],
                    "interpretation": "ranking change only; not evidence of relevance improvement",
                }
            )
    return {
        "methods": methods,
        "observations": observations,
        "research_metrics": {
            "status": "not_evaluated",
            "reason": "no independent relevance/transcription truth",
            "recall_at_k": None,
            "mrr": None,
            "ndcg": None,
            "cer": None,
            "wer": None,
        },
    }


def comparison_markdown(report: dict[str, Any]) -> str:
    lines = [
        "# 国内古籍固定查询与算法对照报告",
        "",
        f"协议：`{report['protocol_id']}`；版本：`{report['runner_version']}`。",
        f"输入锁：`{report['input_fingerprint']}`。",
        "",
        "这是开发集上的排名观察与工程验证。没有独立相关性真值，研究指标 not_evaluated。",
        "草稿由AI观察扫描生成，不是人工功能标签；confidence=null。",
        "",
        f"语料：{report['corpus']['figure_count']}幅真实图、"
        f"{report['corpus']['vector_count']}条兼容512维向量；合成图0幅。",
        f"草稿覆盖{report['drafts']['counts']['figures']}幅图；覆盖不均影响重排，不能据排名变化宣称提升。",
        "数据取自PostgreSQL/pgvector的只读一致性事务，校验扫描与数据库内容、完整模型空间。",
        "文本输入含AI场景描述和原raw OCR；两种来源不等于已确认古文。",
        "",
        "## 方法与时间",
        "",
        "|方法|完成查询|不适用|失败|重复稳定|预热样本|预热中位数ms|预热范围ms|",
        "|---|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for method, m in report["summary"]["methods"].items():
        median = f"{m['warm_median_ms']:.2f}" if m["warm_median_ms"] is not None else "—"
        span = (
            f"{m['warm_min_ms']:.2f}—{m['warm_max_ms']:.2f}"
            if m["warm_min_ms"] is not None
            else "—"
        )
        lines.append(
            f"|{method}|{m['completed']}|{m['not_applicable']}|{m['failed']}|"
            f"{m['stable_repeat_count']}|{m['warm_sample_count']}|{median}|{span}|"
        )
    lines.extend(
        [
            "",
            "耗时包含各方法所需的查询编码、BM25与排序，不含一次性的数据库加载、扫描哈希、",
            "候选向量载入及HTTP API持久化。模型在实验前已加载；first-pass不是模型冷启动，",
            "warm是同一协议预热后的重复请求。本机小语料测量不是生产P95，也不是方法效果。",
            "",
            "BM25按本查询最大分数归一；BGE只使用BGE文本空间；Chinese-CLIP只使用整图共享空间。",
            "hybrid使用生产sv/st/sr系数及st=0.7BGE+0.3BM25，hybrid_no_region去掉sr。",
            "eafr_current使用现有生产证据覆盖；eafr_drafts使用带指针的AI功能Jaccard与查询—候选功能证据覆盖。",
        "eafr_current与草稿变体的区域查询均限定框内空间支持；未定位上下文不评分。",
            "eafr_drafts_no_evidence去掉功能证据项；功能可靠性固定0.5，是工程政策，不是模型概率。",
            "所有关系confidence=null，sg与u_model不可用；没有依据就不补分数。",
            "权重无调优或最优声明。",
            "",
            "## 固定查询与真实前列结果",
            "",
            "视觉查询从扫描裁剪，所有方法排除来源图；没有给BM25/BGE编造查询文字。",
            "区域草稿只有全部空间依据落在框内时才进入查询，纯图片不生成CFR。",
            "",
        ]
    )
    for query in report["queries"]:
        description = query["text"] or query["source_figure_key"]
        lines.extend(
            [
                f"### {query['id']} / {query['kind']} / {description}",
                "",
                query["purpose"],
                "",
                "|方法|前3项（分数）|状态|",
                "|---|---|---|",
            ]
        )
        for row in report["records"]:
            if row["query_id"] != query["id"]:
                continue
            titles = "；".join(
                f"{r['title']} ({r['score']:.4f})" for r in row.get("results", [])[:3]
            ).replace("|", "\\|")
            lines.append(f"|{row['method']}|{titles or row.get('reason', '—')}|{row['status']}|")
        lines.append("")
    observations = report["summary"]["observations"]
    lines.extend(
        [
            "## 排名变化与边界",
            "",
            "hybrid与eafr_drafts对照："
            f"{sum(o['top1_changed'] for o in observations)}条查询首项变化；",
            f"{sum(o['top_k_order_changed'] for o in observations)}条查询前K顺序变化。",
            "仅描述变化，不是改善率。",
            "域外查询即使返回候选，也没有相关性或可信度保证。没有相关性标签，不标记困难负例。",
            "功能草稿和查询由同一AI整理流程产生，存在用词相似与选择偏差；必须通过独立评测才能判断效果。",
            "当前4幅草稿覆盖不均，整经等背景查询可能被推向织机案例；不可把偏移全部称为改善。",
            "未改业务功能断言、关系、核验、raw或corrected；未来独立真值应使用另一个协议版本。",
            "",
            "原始分项、全部前K候选、每次重复签名、失败/不适用与模型锁见comparison.json。",
            "",
        ]
    )
    return "\n".join(lines)
