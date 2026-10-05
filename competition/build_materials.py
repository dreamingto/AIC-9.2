"""Generate anonymous competition artifacts from frozen experiment output, not invented metrics."""
from __future__ import annotations

import argparse
import html
import json
import shutil
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import Image, PageBreak, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "output/competition"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--report", type=Path, required=True)
    args = parser.parse_args()
    data = json.loads((ROOT / "competition/materials.json").read_text(encoding="utf-8"))
    report = json.loads(args.report.read_text(encoding="utf-8"))
    assert report["evaluation_status"] == "not_evaluated"
    assert sum(r["status"] == "completed" for r in report["records"]) == 176
    assert all(r["repeat_stable"] for r in report["records"] if r["status"] == "completed")
    assert len(data["introduction"]) <= 300
    OUT.mkdir(parents=True, exist_ok=True)
    shutil.copytree(ROOT / "competition/vendor", OUT / "vendor", dirs_exist_ok=True)
    shutil.copy2(ROOT / "competition/deck.css", OUT / "deck.css")
    shutil.copy2(args.report, OUT / "comparison.json")
    for name in ("comparison.md", "corpus-lock.json", "function-evidence-drafts.json", "function-evidence-drafts.md"):
        shutil.copy2(args.report.parent / name, OUT / name)
    (OUT / "项目简介.txt").write_text(data["introduction"] + "\n", encoding="utf-8")
    (OUT / "narration.json").write_text(json.dumps(data["slides"], ensure_ascii=False, indent=2), encoding="utf-8")
    script = "# 机图索隐演示逐字稿\n\n" + "\n\n".join(
        f"## {i + 1}. {s['title']}\n\n{s['notes']}" for i, s in enumerate(data["slides"]))
    (OUT / "演示逐字稿.md").write_text(script + "\n", encoding="utf-8")
    images = {
        "loom": [("ai-zhsy-p24-loom", "《耕织图》室内织机"), ("ai-zhsy-p26-large-loom", "《耕织图》另一织机")],
        "water": [("ai-nlc-p25-water-pestle", "《天工开物》水碓"), ("ai-nlc-p26-water-mill", "《天工开物》水磨")],
    }
    slides = []
    for i, s in enumerate(data["slides"]):
        content = '<div class="lines">' + ''.join(f"<p>{html.escape(t)}</p>" for t in s["bullets"]) + '</div>'
        if s["layout"] in images:
            content = '<div class="case-grid">' + ''.join(
                f'<figure style="margin:0"><img src="assets/{key}.jpg" alt="{label}"><figcaption>{label} · 扫描 Observed / 图区 Inferred</figcaption></figure>'
                for key, label in images[s["layout"]]) + '</div><p class="small">' + ' · '.join(s["bullets"]) + '</p>'
        elif s["layout"] == "method":
            content += '<div class="formula">S = βv·sv + βt·st + βr·sr + βf·sf + βg·sg + λe·se − λu·Umodel</div><p class="small">模型空间独立 / 缺失模态显式标记 / 区域仅用框内主张</p>'
        elif s["layout"] == "experiment":
            content += '<div class="notice">开发集排名观察；Recall / MRR / nDCG / CER / WER：not_evaluated</div>'
        tag = "h1" if i == 0 else "h2"
        cls = "h1" if i == 0 else "h2"
        slides.append(f'<section class="slide" data-title="{html.escape(s["title"], quote=True)}"><p class="kicker">机图索隐 / AIC 智能文化 / {i+1:02d}</p><{tag} class="{cls}">{html.escape(s["title"])}</{tag}>{content}<div class="deck-footer"><span>2026-10-05 · 可追溯检索 · AI 草稿待核实</span><span>{i+1} / 8</span></div><aside class="notes"><p>{html.escape(s["notes"])}</p></aside></section>')
    document = '<!doctype html><html lang="zh-CN" data-themes="academic-paper"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>机图索隐 · 比赛答辩</title><link rel="stylesheet" href="vendor/base.css"><link id="theme-link" rel="stylesheet" href="vendor/academic-paper.css"><link rel="stylesheet" href="vendor/style.css"><link rel="stylesheet" href="deck.css"></head><body class="tpl-presenter-mode-reveal"><div class="deck">' + ''.join(slides) + '</div><script src="vendor/runtime.js"></script></body></html>'
    (OUT / "答辩幻灯片.html").write_text(document, encoding="utf-8")
    pdfmetrics.registerFont(TTFont("Chinese", "C:/Windows/Fonts/simsun.ttc", subfontIndex=0))
    body = ParagraphStyle("CN", fontName="Chinese", fontSize=10.5, leading=17, spaceAfter=10, textColor=colors.HexColor("#243045"))
    title = ParagraphStyle("CNtitle", parent=body, fontSize=24, leading=34, spaceAfter=22)
    heading = ParagraphStyle("CNheading", parent=body, fontSize=16, leading=24, textColor=colors.HexColor("#1a3a7a"), spaceAfter=16)
    small = ParagraphStyle("CNsmall", parent=body, fontSize=8, leading=13)
    caption = ParagraphStyle("CNcaption", parent=small, alignment=TA_CENTER)
    story = []

    def p(text: str, style: ParagraphStyle = body) -> None:
        story.append(Paragraph(html.escape(text), style))

    def table(rows: list[list[str]], widths: list[float] | None = None) -> None:
        obj = Table([[Paragraph(html.escape(str(c)), small) for c in r] for r in rows], colWidths=widths, repeatRows=1)
        obj.setStyle(TableStyle([("BACKGROUND", (0,0), (-1,0), colors.HexColor("#eef1f7")), ("VALIGN", (0,0), (-1,-1), "TOP"), ("BOX", (0,0), (-1,-1), .5, colors.HexColor("#ced4dc")), ("INNERGRID", (0,0), (-1,-1), .3, colors.HexColor("#dde2e8")), ("TOPPADDING", (0,0), (-1,-1), 8), ("BOTTOMPADDING", (0,0), (-1,-1), 8)]))
        story.extend([obj, Spacer(1, 12)])

    p("机图索隐", title); p(data["subtitle"], heading)
    p("AIC 全球校园人工智能算法精英大赛 · 智能文化赛道\n技术方案与工程验证报告 · V1.2 · 2026-10-05")
    p("团队名称与编号：由参赛者在正式提交版填写；当前为匿名预审版。", small)
    p(data["introduction"])
    table([["当前能力", "证据与边界"], ["真实中文文本、图片、局部检索", "两个国内古籍案例；动态排序，不锁定期望名次"], ["可追溯来源与分项评分", "扫描 / 目录 / AI 推断分开；AI 草稿暂不人工审核"], ["冻结开发查询与算法对照", "528 次排名验证重复稳定；研究效果 not_evaluated"]], [170, 320])
    story.append(Spacer(1, 20)); p("论文式报告不包含学校、导师或队员身份。所有数字来自本项目实际输入与运行记录。", small)
    story.append(PageBreak()); p("1  任务定义与数据范围", heading)
    p("面向古籍技术图像的候选发现和证据比较。输入包括中文语句、上传图像、归一化局部框；输出包括出处、匹配区域、分项得分、功能槽、证据状态和不确定性。历史传承不是自动预测目标。")
    p("需求来自项目整理真实扫描和调试 OCR 的实际过程：竖排与夹注读序易错、相似外形未必同功能、图题与解释分散、检索候选缺出处。以页面观察和开发场景为需求依据，尚未开展用户访谈或量化效率调研。主要用户为古籍整理与科技史研究人员；要求三个查询入口、局部证据约束、来源可回溯和错误可识别。")
    table([["语料", "出版 / 馆藏身份", "当前范围"], ["《耕织图》", "中华再造善本 / 国家图书馆出版社（国内出版）", "8 图 / 5 扫描"], ["《天工开物》第 2 册", "国家图书馆馆藏；出版身份与获取渠道分别登记", "4 图 / 3 扫描"]], [110, 240, 140])
    p("真实范围合计 12 图、14 局部区域、35 文本、59 证据、65 局部 raw OCR 行。原有 9 合成图仅用于工程测试。固定对照排除全部合成图。国内出版优先不是下载域名限制，原始来源 URL 和许可随数据包保留。")
    p("PaddleOCR 环境与检索环境分别锁定；当前 raw OCR 并非真实古文金标准。AI 观察生成的场景描述和功能草稿与 raw OCR 分开记录，corrected 真值未形成。")
    p("来源指针至少包含书名、版本、卷页、扫描路径、SHA256、许可和处理版本；许可不允许再分发时，资源接口返回 LICENSE_RESTRICTED。发布包只纳入已登记允许再分发的选中来源。")
    story.append(PageBreak()); p("2  架构、模型与存储", heading)
    table([["层", "实现"], ["浏览器", "React 19 / TypeScript / Zod；Nginx 同源代理"], ["API", "FastAPI / Pydantic v2 / 请求 ID / 统一错误"], ["数据库", "PostgreSQL 16 + pgvector；Alembic 显式迁移"], ["模型进程", "独立 Windows CUDA Worker；本地 HTTP；可插拔 Provider"], ["文本", "BAAI/bge-small-zh-v1.5 / 512 维"], ["视觉图文", "OFA-Sys/chinese-clip-vit-base-patch16 / 512 维"], ["工程离线基线", "BM25 / 256 维确定性文本与图像向量"]], [120, 370])
    p("模型身份由 provider、model、version、dimension、preprocessing_hash 联合绑定，BGE 与 CLIP 不因同为 512 维而混算。通用 VECTOR 存储不同模型空间，小规模语料采用精确余弦，不建立 ANN 索引。")
    p("选型依据：BGE 提供中文文本编码，Chinese-CLIP 提供中文图文共享空间；已有权重可本地运行，避免搜索依赖远程大模型。PaddleOCR 负责 raw 文字识别。模型效果仍需古籍评测，不把通用基准能力直接迁移为本项目准确率。")
    p("BGE revision：7999e1d3359715c523056ef9478215996d62a620；Chinese-CLIP revision：36e679e65c2a2fead755ae21162091293ad37834。Torch 2.7.1 + cu128 / Transformers 4.51.3；实测 GPU 为 RTX 4060 Laptop 8GB。非古籍专门微调模型。", small)
    p("17 个 V1 操作含三模态检索、数据查询、导入、候选核验和演示接口。数据库或模型不可用时明确返回 503，不以静态 JSON 或 SQLite 代替。")
    story.append(PageBreak()); p("3  EAFR 与空间证据约束", heading)
    p("S = βv·sv + βt·st + βr·sr + βf·sf + βg·sg + λe·se − λu·Umodel")
    table([["分项", "含义与适用条件"], ["sv / st / sr", "视觉、文本与局部相似度，进入融合前校准；缺失模态公开标记"], ["sf", "功能多标签 weighted Jaccard；支持 unknown，不用互斥 Softmax"], ["sg", "达到置信度阈值的关系三元组；当前 AI 关系 null，禁用"], ["se(q,d)", "查询与候选对级别证据覆盖；不是正文长度奖励"], ["Umodel", "模型功能置信度的不确定性；与资料缺失率独立"]], [105, 385])
    p("默认权重 v=.25 / t=.25 / r=.20 / f=.20 / g=.05 / e=.10 / u=.05，由 EAFR_WEIGHTS JSON 配置；不是最优权重。分项、可用性、可靠性、贡献和模型版本存入搜索快照。")
    p("空间修复：区域查询只采用原图坐标中全部支持落在框内的文本或功能断言。不定位的整图描述和关系不自动继承给小裁剪。来源图排除，纯图片无可提取功能主张时，功能证据项不可用。")
    p("全部 12 图草稿共 72 槽，45 有据建议、27 unknown、10 关系；全部 Inferred，confidence=null。实验功能可靠性 0.5 为公开工程政策，不是概率。该草稿用于独立对照，不自动写入生产知识库。")
    p("方案差异点：在相似度检索之上，增加查询—候选证据覆盖、框内主张范围和证据状态链，降低整页功能被误当局部功能的风险；这是工程设计创新，尚无独立对照证明优于既有研究。")
    story.append(PageBreak()); p("4  两个国内固定案例", heading)
    for kind in ("loom", "water"):
        cells = []
        for key, label in images[kind]:
            cells.append([Image(str(OUT / "assets" / (key + ".jpg")), width=210, height=160, kind="proportional"), Paragraph(label, caption)])
        t = Table([[cells[0], cells[1]]], colWidths=[245, 245]); story.extend([t, Spacer(1, 12)])
        p("织机与经线：固定输入“织机 经线”，页面读取真实扫描和版本；文本或局部请求实时计算排名，不硬编码图对。" if kind == "loom" else "水碓与水磨：固定输入“水轮 驱动 谷物 加工”，舂击与研磨应分开比较。宽泛查询可能召回土礱等候选，保留真实结果和不足提示。")
    p("页面入口 /demo；图详情与候选对照可以追踪原扫描、OCR 和 AI 描述。自动化核验测试只作用于独立库中的合成样本，真实图仍待核实。", small)
    story.append(PageBreak()); p("5  冻结对照协议与实际运行", heading)
    p("24 条固定开发查询：16 文本、4 图像、4 区域。8 方法含 BM25、BGE、中文图文、hybrid、去区域消融、现有 EAFR、AI 草稿 EAFR、去证据消融。没有独立 qrels，因此不称为冻结测试集。")
    rows = [["方法", "完成", "不适用", "失败", "预热中位数 ms"]]
    for method, m in report["summary"]["methods"].items():
        rows.append([method, str(m["completed"]), str(m["not_applicable"]), str(m["failed"]), f'{m["warm_median_ms"]:.2f}'])
    table(rows, [175, 60, 60, 55, 140])
    p("176 适用组合 ×（首次 + 2 次预热重复）= 528 次排名；失败 0、重复不稳定 0。16 组合不适用，图片输入不给文本专用模型编造查询。读取 PostgreSQL 一致性只读事务，业务记录不修改。")
    p("耗时包含模型查询编码、BM25 和排序，不含数据库加载、哈希检查、HTTP 持久化及模型冷启动；小语料预热延迟不是生产 P95。排名变化不是相关性改善率。")
    p("输入指纹：" + report["input_fingerprint"], small)
    p("研究指标：CER / WER / 图题召回 / Recall@K / MRR / nDCG 均 not_evaluated。", body)
    story.append(PageBreak()); p("6  可复现交付与验证", heading)
    p("三个启动档：fixture / real / neural。干净仓库的 .env 可缺省，脚本从模板创建；数据库未启动时明确失败。冻结输入包提供原 PDF、选中扫描、raw OCR、原 manifest 与 88 个向量，逐文件和整包校验，拒绝路径穿越与不一致覆盖。")
    p("实施按数据、后端、前端与模型四个模块推进：9 月建立服务与 OCR 环境，10 月完成真实语料、中文模型、案例和冻结对照，本轮补齐恢复与材料。开发使用 AI 辅助编码，前端初稿由 Gemini 生成；预训练模型及幻灯片模板为引用组件，自主实现服务契约、来源管理、证据约束和复现链。成员分工待参赛者登记。")
    table([["验证", "实际执行范围"], ["空库恢复", "无私密 .env 的新源码目录；新 PG 卷自动迁移 0001 / 0002；12 图导入 + 88 向量恢复"], ["数据库测试", "独立 PostgreSQL 3 项集成用例通过；不触及业务核验状态"], ["全栈", "Chrome 真实 Nginx / FastAPI / pgvector，文本、图像、区域、案例与候选"], ["持续集成", "GitHub Actions 配置后端 PG、静态/类型/测试、前端构建及 OpenAPI 字段漂移检查"], ["依赖", "服务、OCR、模型与材料环境分开；模型不混入基础镜像"]], [105, 385])
    p("数据包 SHA256：e108e27390b3b1200e7eeb314a2905e38ff609061bba8f58b67a725de8d1080e。源码和数据锁入 Git；模型权重、原扫描和视频独立发布。恢复器拒绝把旧向量绑定到改过的文本或裁剪。", small)
    p("CI 的远程执行状态以 GitHub Actions 为准；当前机器的验证与在线流水线分开记录。服务首版用于本地/受控比赛演示，不含账户体系。")
    story.append(PageBreak()); p("7  局限、路线与引用", heading)
    p("当前样本规模小，OCR 在竖排、旧字形、夹注和低清扫描下存在错误；中文通用模型没有进行古籍领域微调。AI 功能草稿缺独立核验，关系置信度未校准。以上限制已在页面和实验报告中公开。")
    p("应用价值是把候选发现、扫描查看与出处核对组织到同一流程，潜在降低材料整理成本并支持文化教育展示。目前没有真实用户效率提升比例、经济收益、专家验证或外部合作证明；不虚构这些佐证。")
    p("下一步：扩大国内出版/馆藏语料；分离开发集与独立评测集；建立可追溯校订和相关性标签；评价 CER/WER、图题召回、Recall/MRR/nDCG；再决定是否训练领域模型和调整权重。人工审核当前不阻塞比赛演示，但独立真值缺失时不报告研究准确率。")
    p("可复现附件：项目简介、技术 PDF、HTML/PDF 答辩页、真实系统演示 MP4、24 查询与功能草稿协议、原始排名 JSON、输入恢复包和逐文件锁。")
    p("模型与赛事原始资料", heading)
    for source in ["BGE 模型： https://huggingface.co/BAAI/bge-small-zh-v1.5", "Chinese-CLIP： https://huggingface.co/OFA-Sys/chinese-clip-vit-base-patch16", "Chinese-CLIP 官方代码： https://github.com/OFA-Sys/Chinese-CLIP", "赛事延期公告： https://www.aicomp.cn/notice/notice-3/4776.html", "项目源码： https://github.com/dreamingto/AIC-9.2"]:
        p(source, small)
    p("原始古籍来源 URL、许可说明和哈希见 release/domestic-data.lock.json 与恢复后的 sources.json；保持原扫描水印，不自动推出历史关系。", small)

    def footer(canvas, doc) -> None:
        canvas.setFont("Chinese", 8); canvas.setFillColor(colors.HexColor("#7c8491"))
        canvas.drawString(20*mm, 12*mm, "机图索隐 · V1.2 · AI 草稿 Inferred · 研究指标 not_evaluated")
        canvas.drawRightString(190*mm, 12*mm, str(doc.page))

    pdf = OUT / "机图索隐_技术报告.pdf"
    SimpleDocTemplate(str(pdf), pagesize=(210*mm,297*mm), rightMargin=20*mm, leftMargin=20*mm, topMargin=20*mm, bottomMargin=21*mm, title="机图索隐技术报告", author="").build(story, onFirstPage=footer, onLaterPages=footer)
    print(json.dumps({"pdf":str(pdf), "bytes":pdf.stat().st_size, "intro_characters":len(data["introduction"]), "report_fingerprint":report["input_fingerprint"]}, ensure_ascii=False))


if __name__ == "__main__":
    main()
