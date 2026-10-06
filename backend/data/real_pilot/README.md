# OCR、来源登记与可选标注流程

本目录在 Git 中仅保存来源登记、数据选择配置、标注 schema 与工具。PDF、页面扫描、raw OCR、校订导出、审核草稿、冻结快照和运行报告由本地管理。比赛当前不要求追加人工审核；已有工具保留供后续独立校订与评测使用。

## 来源与许可

`sources.json` 登记书名、版本、出处、下载 URL、许可、获取日期及文件哈希。国内出版/馆藏单位与 Wikimedia Commons 获取渠道分别说明；目录记载不视为独立版本学鉴定。下载器只接受登记中的 HTTPS PDF，校验魔数、字节数、Commons SHA-1 与本地 SHA-256。

当前国内比赛选择由 `domestic_ai_selection.json` 定义：《耕织图》8 幅技术图，国图馆藏《天工开物》4 幅技术图。扫描保持水印与出处。真实文本、图题与模型场景建议为 Inferred，没有独立逐字校订或研究真值。

## 原始数据准备

先按 [真实数据恢复说明](../../../release/README.md) 恢复既有冻结输入。重新下载/渲染/OCR用于新数据版本，不保证与旧快照逐字节相同。

需要自行准备新输入时，在 backend 环境中使用相应脚本：

```powershell
python -m scripts.download_real_pilot
python -m scripts.prepare_real_pilot
```

原始 PDF 在 `backend/data/assets/real_pilot_v1/`，渲染页在 `backend/data/processed/real_pilot_v1/`。`prepare_real_pilot` 校验 PDF 字节数、SHA-256、页数及渲染页数，生成本地 `derived_pages.json`。其他来源可通过该命令的 `--help` 选择，不覆盖旧范围。

## PaddleOCR 与 raw/corrected

`backend/requirements-ocr.lock` 锁定独立 OCR 依赖；不要将 PaddleOCR 环境混入后端或神经检索环境。`app/retrieval/providers/ocr.py` 提供可选 Provider，`scripts/run_real_pilot_ocr.py` 执行批量识别，缺少模型明确报告 MODEL_UNAVAILABLE。

raw OCR 保留行文本、框坐标、顺序、置信度与输入身份。`annotation_schema.json` 定义 layout、reading_order、raw_text、corrected_text 与修改轨迹。`annotation_tool.html` 和 `scripts.annotation_server` 提供本地标注入口；PPOCRLabel 转换与审计工具在 `backend/scripts`。

模型辅助候选、共识或 AI 检查不等于人工确认。改动文本、框或顺序会撤销对应确认；人工导出按输入哈希、身份、阅读顺序、坐标及完整清单验证。部分确认不能升级整页。

## 导入与可选评测

- `prepare_domestic_ai_manifest`：生成独立 AI 辅助 manifest，保留真实出处与 Inferred 状态。
- `export_reviewed_real_manifest`：经过正式确认与校验后生成独立审核 manifest。
- `freeze_ppocrlabel_snapshot`、`prepare_competition_scope`、`evaluate_competition_ocr`：范围绑定、快照和 OCR 评测；未就绪真值不得出分。
- `prepare_competition_evidence_drafts` 与固定对照协议：组织功能证据草稿，不能自动写入生产人工标签。

具体参数以各命令的 `--help` 为准。导入接口仅读取受控 manifest 名称；来源/原页/技术图/局部框/文本与证据保持可回溯关系。

CER、WER、图题召回率需要独立转录与完整图题真值；检索 Recall/MRR/nDCG 需要独立相关性标签。当前均为 `not_evaluated`。AI 排名、置信度、开发查询和工程测试不能替代这些指标。
