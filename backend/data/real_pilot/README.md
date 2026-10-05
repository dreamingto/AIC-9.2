# V1.1-B 真实古籍试点

本目录保存可版本化的来源与许可元数据。原始 PDF 下载到
`backend/data/assets/real_pilot_v1/`，该目录受项目 `.gitignore` 保护，不随 Git 提交。

当前来源均通过 Wikimedia Commons 官方 MediaWiki API 核验，Commons 文件元数据显示：

- `LicenseShortName`: `Public domain`
- `UsageTerms`: `Public domain`
- `AttributionRequired`: `false`
- `Restrictions`: 空

数字文件权利状态以抓取日期的 Commons 文件页为依据。对外发布数据包前仍应重新检查文件页，
并保留来源链接、抓取时间和哈希。不要仅根据古籍作者年代推断数字扫描件许可。

## 下载与校验

在项目根目录执行：

```powershell
python backend/scripts/download_real_pilot.py
```

脚本只接受登记在 `sources.json` 中、位于 `upload.wikimedia.org` 的 HTTPS PDF，验证
PDF 魔数、字节数、Commons SHA-1 和本地 SHA-256。重复执行会校验现有文件，不重复下载。

## 试点选择

- 《天工开物 2》共 28 页，作为第一批 20-50 页 OCR/版面标注试点。
- 《农政全书 1》共 79 页，作为第二来源保留；完成逐页图像审查后再选择技术图页面。

两个文件都是真实馆藏扫描；首批 28 页已完成 raw OCR 和一轮人工框选筛噪，但逐字转录、图题分类和
检索效果评估仍未完成，`evaluation_status` 必须保持为 `not_evaluated`。

## 页面准备

使用 Poppler 将首批来源渲染为可标注 PNG，并生成可追溯库存：

```powershell
python backend/scripts/prepare_real_pilot.py
```

默认只处理 `pilot_selection=primary_all_28_pages` 的《天工开物》第二册；可用 `--source-id` 指定来源或 `--all-sources` 渲染两份 PDF。脚本校验 PDF 字节数、SHA-256、页数和渲染页数后，输出 `derived_pages.json`。页面的版面和 OCR 字段保持 pending，不生成任何虚构文本或历史标签。

`annotation_schema.json` 是人工标注模板，要求保留 layout 区域、阅读顺序、raw OCR、corrected text、行坐标、置信度、输入哈希和修改轨迹。未安装 PaddleOCR 时，后端的可选 Provider 明确返回 `MODEL_UNAVAILABLE`。

Docker 构建默认排除 `data/assets/real_pilot_v1/` 和 `data/processed/real_pilot_v1/`，原始扫描和渲染图仅保留在本地受控目录。

## PaddleOCR 运行时

OCR 运行时是仓库外的独立 Windows x64 CPU 环境，不加入默认后端虚拟环境，也不进入 Docker 镜像。当前锁定：

```text
Python 3.12.14
paddlepaddle==3.0.0
paddleocr==3.0.3
paddlex==3.0.3
PP-OCRv5_mobile_det
PP-OCRv5_mobile_rec
```

完整依赖写入 `backend/requirements-ocr.lock`。推荐使用 `PADDLE_PDX_MODEL_SOURCE=BOS`，通过本地代理下载模型。受控入口为：

```powershell
& "D:\codex-runtime\jitu-paddleocr-3.0.3\Scripts\python.exe" `
  backend/scripts/run_real_pilot_ocr.py --limit 1
```

该命令只生成 `backend/data/real_pilot/ocr_results.json` 中的机器 raw OCR，保留输入哈希、逐行 bbox、confidence、Provider 版本和耗时；不填写 `corrected_text`，不改变人工 `review_state`，不把 OCR 转录核验等同于文献或传承关系核验。

## PPOCRLabel 草稿转换

PPOCRLabel 的 `Cache.cach`、`Label.txt` 和 `fileState.txt` 均保存在渲染页面目录中，受
`.gitignore` 保护。使用受控转换器生成项目 annotation schema 草稿：

```powershell
cd backend
.\.venv\Scripts\python.exe scripts\convert_ppocrlabel_annotations.py
```

输出为被忽略的 `backend/data/real_pilot/annotations.ppocrlabel-draft.json`。转换器只接受登记的
`source_id`，校验库存 SHA-256、页面路径、TSV/JSON、四点多边形和像素边界，并以原子写入生成
稳定结果。四点顺序按 PPOCRLabel 原数组保留，同时计算归一化 bbox 和 reading order。

`fileState.txt` 可能由机械保存流程写入，不能单独证明人工校订。默认运行会记录
`tool_confirmed_pages`，但版面和转录均保持 unreviewed。完成逐页删框、调整框和阅读顺序后，
可只接纳版面审核：

```powershell
.\.venv\Scripts\python.exe scripts\convert_ppocrlabel_annotations.py `
  --accept-file-state --reviewer "<reviewer-id>"
```

这不会填写 `corrected_text`。只有逐字检查所有保留框、清除编码损坏与馆藏噪声后，才可追加
`--accept-transcription-review`。转录接纳会拒绝包含 Unicode replacement character `�` 的标签。

质量审计命令：

```powershell
.\.venv\Scripts\python.exe scripts\audit_ppocrlabel_annotations.py
```

审计仅在明确接纳转录且所有门槛通过时计算 CER 和带明确定义的混合 CJK token error rate。
PPOCRLabel 不包含 `caption` 类别，因此图题召回率必须等图题区域真值建立后再计算。

完成版面审核后，可冻结内容寻址的本地快照：

```powershell
.\.venv\Scripts\python.exe scripts\freeze_ppocrlabel_snapshot.py `
  --reviewer "<reviewer-id>"
```

原版面快照为 `commons-najda-tiangong-kaiwu-2-layout-2e7bf4a41b9e`：28 页均已确认，
raw 732 框初筛至 525 框。随后受控清理器仅删除第 8 页右下角的
`国立公文書館 / National Archives of Japan` 两个馆藏数字化水印框，当前 Label 为 523 框，
净删除 209 框。清理前后 SHA-256、坐标和规则保存在被 Git 忽略的
`label_sanitization_audit.json`；最新审计为 `no_known_digitization_noise=true`。

原内容寻址快照仍只代表清理前的版面审核，不得用来声称转录已确认。当前 523 个框仍无人工
`corrected_text`，没有接纳 transcription review；CER、WER 和图题召回率继续为
`not_evaluated`。

## 古文参考、二次 OCR 与聚焦复核

公共领域参考文本由 `download_naifu_reference.py` 通过 Wikisource MediaWiki API 下载，覆盖
《天工开物·乃服》36 节。它可能来自不同版本并含社区录入差异，只能作为对照候选，不能替代
扫描底本真值。正文以显式章节锚点分别对齐，平均 alignment confidence 从全局贪心版本的约
0.49 提升至 0.845，253 个正文框中仅 1 个低于 0.5。

在锁定的独立 Paddle 环境中运行繁体、竖排和古籍能力更强的
`PP-OCRv5_server_rec`：

```powershell
cd backend
& "D:\codex-runtime\jitu-paddleocr-3.0.3\Scripts\python.exe" -X utf8 `
  -m scripts.generate_historical_review_candidates `
  --run-server-ocr --device cpu --batch-size 16
```

脚本将 523 个竖排框逆时针旋转后以 `input_shape=(3,48,1024)` 识别，并按输入指纹写入可恢复的
本地缓存。输出包含 raw、server OCR、分节 Wikisource 候选、类别、角色、阅读顺序、13 个技术
图区和保守共识建议；全部固定为 `verification_state=inferred`。当前候选类别统计为 text 283、
caption 38、annotation 202，另有 figure 13；保守共识文本 88 项，人工转录与图题真值均为 0。

生成聚焦审核页：

```powershell
cd backend
.\.venv\Scripts\python.exe -m scripts.build_historical_review_queue
```

本地产物为 `model_review_queue.html`、`model_review_queue.json` 和
`model_review_assets/`，均受 `.gitignore` 保护。审核页只集中展示三方冲突、低置信、章节标题、
图题/部件标签、13 个技术图区和 3 个补框图题：当前优先队列 280 项，其中 169 项为关键冲突。
另有 259 项延后检查，可切换“全部候选”或“延后项”继续查看，总共 539 项。延后项只是启发式
排队结果，不等于文字正确或已核验。页面显示整页扫描、文字框顺序叠加层和裁剪，支持改类别、
阅读顺序及归一化坐标；已确认内容再次编辑时会自动撤销该项确认。

页面可直接打开 `model_review_queue.html`，无需服务端。草稿按候选文件 SHA-256 分开保存在
浏览器本机存储中。只有复核人保存并逐项确认后，才会导出独立 override JSON；本页阅读顺序
需要单独勾选确认。模型对齐分数和启发式一致性均不是 CER 或模型准确率。

## 导入人工确认与修改轨迹

生成器不会覆盖 `Label.txt`、Cache 或 raw OCR。人工导出后执行：

```powershell
cd backend
.\.venv\Scripts\python.exe -m scripts.convert_ppocrlabel_annotations `
  --accept-file-state --reviewer "<reviewer-id>" `
  --review-overrides "<导出文件的实际路径>"
```

该路径生成受 Git 忽略的 `annotations.human-reviewed.json`，并核对候选文件、当前 Label、库存
哈希及 reviewer/reviewed_at/confirmed。未知框、重复记录、模型 Inferred、非法坐标、重复阅读
顺序和陈旧输入会被拒绝；验证失败时保留原输出文件。

已确认文字以逐框 corrected_lines 和修改轨迹保留。未确认完整正文时，页级 corrected_text
仍为空并报告 partial；所有保留框转录和本页阅读顺序都确认后才报告 reviewed。技术图区和
图题真值具有独立确认状态，补框图题也会进入 layout regions。仅确认技术图区不会自动确认
图题。该流程不能同时使用整批 `--accept-transcription-review`，也不能使用仍未校订的
Label 作为审核页 corrected 层的替代品。

当前尚无真实人工导出文件被接纳，转录与图题真值仍为 0；评测集冻结、正式 CER/WER、图题
召回率和数据库导入继续 pending/not_evaluated。

## AIC 核心范围与国内古籍补充（2026-10-03）

来源库现有5份扫描、207页，涉及3部中国古籍。本轮新增国图《天工开物》第二册45页、中华
再造善本《耕织图》27页、Harvard《御制耕织图》28页；均验证字节数、Commons SHA-1、本地
SHA-256、PDF页数。新增扫描包含蚕桑/织造图，国图水印保留。

新增100页单独登记为 `supplementary_pages.json`，不覆盖原28页 `derived_pages.json`。
从 backend 目录执行以下命令重建（已有图重用；不修改原始PDF）：

```powershell
.\.venv\Scripts\python.exe -X utf8 -m scripts.download_real_pilot
.\.venv\Scripts\python.exe -X utf8 -m scripts.prepare_real_pilot `
  --source-id commons-zhsy-gengzhi-tu-1696 `
  --source-id commons-harvard-gengzhi-tu-1696 `
  --source-id commons-nlc-tiangong-kaiwu-2-1637 `
  --dpi 100 --max-image-side 2500 `
  --inventory-path data/real_pilot/supplementary_pages.json
```

核心范围固定原第10、12、14、16、18、22页：101框、7个技术图区候选、1个补框图题，共109项。
`competition_core_selection.json`为可提交配置；范围本身待人工真值，不是已冻结评测集：

```powershell
.\.venv\Scripts\python.exe -X utf8 -m scripts.prepare_competition_scope
.\.venv\Scripts\python.exe -X utf8 -m scripts.build_historical_review_queue `
  --scope data/real_pilot/competition_scope.json
```

审核页默认核心6页全部候选，草稿键继续绑定原候选哈希，可切回全部页面。逐项/阅读顺序确认
后，另需确认全页文字与图题清单完整；发现额外漏框先回PPOCRLabel补框重建，不能带漏框勾选完整。
将真实人工导出保存到 `data/real_pilot/historical-review-overrides.json`，按上一节接纳后执行：

```powershell
.\.venv\Scripts\python.exe -X utf8 -m scripts.evaluate_competition_ocr --freeze
```

评测器重新核对原始人工导出/产物和固定范围输入。未完成全部6页时写出缺项报告，metrics为null，
退出码2，不创建真实快照；输入失效也拒绝出分。通过后计算原保留转录框raw/server的micro CER、
CJK-character/Latin-word WER，完整人工图题清单用于raw检测框IoU≥0.5最大一对一定位Recall。
不报告无合理分类定义的Precision/F1、整页端到端CER或未标注相关性的检索指标。

截至2026-10-03实际0/6页就绪，新增扫描尚未做OCR/业务导入，线上业务仍为synthetic fixture。详细命令、
指标口径与验证见 `docs/机图索隐_AIC比赛版数据与评测推进.md`；真实资产/报告/快照被Git和Docker排除。

## 2026-10-04 续作

补充库存中已独立完成国内两来源12页OCR：国图《天工开物》扫描22—27页、中华再造善本
《耕织图》扫描21—26页；257框、830个raw_text字符（含换行），corrected/reviewed均为0。
`supplementary_ocr_selection.json`为可提交选页配置，`supplementary_ocr_results.json`为被忽略的
机器产物。原28页文件与复核草稿保持原样。Runner支持独立库存/输出、逐页保存、哈希与模型
版本校验和`--resume`；scope/model变化或人工corrected文件不得复用。

新增人工门控导出命令 `python -m scripts.export_reviewed_real_manifest`：真实人工接纳、固定
范围完整性及图区/图题各自确认通过后，导出仅含图与图题的真实业务manifest及扫描；不生成
功能/关系/相关性标签，不把转录确认升级为历史Verified。当前真实0/6，命令退出2，未导出。
确认后可用`docker-compose.reviewed-real.yml`只读挂载导出扫描并走既有导入API。

最新142项后端测试（含独立PG格式集成）、66源文件Mypy与静态检查、Docker三服务重建、
全栈smoke和7项Chrome E2E通过。业务库仍为fixture；详细安全边界与命令见比赛推进文档。

## 2026-10-05 AI 辅助扫描检查

同日后续已生成独立补框版本：`review_revisions/active_revision.json`指向
`supplements-v2-c4a07f9b9be9`。核心113项=原109+4补框，原109建议迁移；97 AI已检查，
16序号变化待重检，人工仍0/6。新人工页可采用绑定的AI建议但不会自动确认。
补框的raw为空，完整性门包含新增区域，保留原框CER/WER排除补框并记录数量。
接纳/评测/导出须使用新版--candidate/--scope等路径参数；详细命令、11留空文字和末部
正文/夹注归属疑点见`docs/机图索隐_AI辅助复核交接.md`前部。旧文件/草稿不覆盖。
最新158后端测试通过/独立PG1项skip，68源文件检查通过；真实freeze/export继续退出2。

核心6页109项已保存AI扫描检查、修订和逐项备注，独立页面为`model_review_queue.ai.html`，
导出为`ai-assisted-review-overrides.json`，定位/未决报告为`ai-assisted-review-overrides.audit.json`。
原人工页面与草稿不覆盖。AI项始终Inferred/待人工；`confirmed=true`仅指AI已检查。
转换器拒绝AI导出，即使改名/改顶层类型，记录级AI来源或pending-human标记也会被拒绝。

第10页至少两列正文不在原候选范围，须在新副本补框并建立新候选/scope，保留原文件哈希和
109项建议。独立人工逐项确认、顺序/完整清单完成后才接纳、冻结、评测和真实导入。
最新149项后端测试通过/独立PG1项skip，67源文件检查通过；实际freeze仍0/6、退出2、
not_evaluated。详细问题、修订例子和验收边界见`docs/机图索隐_AI辅助复核交接.md`。
