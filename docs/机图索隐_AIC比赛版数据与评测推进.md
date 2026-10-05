# 机图索隐：AIC 比赛版数据与评测推进

## 当前路线：国内古籍AI比赛演示（2026-10-05）

用户已明确优先国内出版内容，比赛暂不人工审核。本机现已导入国内《耕织图》8图及
国图《天工开物》4图，8扫描/14区域/35文本/59证据/38向量，实际三类检索与Chrome验收通过。
新类型ai_assisted_real_pilot独立于人审真值，指标仍not_evaluated；旧人审页暂不要求操作。
启动、数据来源和下一阶段见[国内古籍AI比赛演示](机图索隐_国内古籍AI比赛演示.md)。
以下按日期保留早先的数据和人工评测协议，仅作历史/后续可选方案。

## 最新进展（2026-10-05）

active_revision.json指定当前版本，核心113项（101原框、4补框区域、7图区、1补框图题）。
第二轮实际AI检查已完成113项，6处文字留空/13未知保留，独立人工真值0/6；已生成7图证据工作表、
6有引用功能草稿、2案例和7无相关性标签查询。业务库仍synthetic，研究指标未评测。
旧109项说明和默认命令是历史记录，当前操作须用新版路径，见[下一阶段执行计划](机图索隐_下一阶段执行计划.md)。

更新：2026-10-03。工程已建立，比赛版当前的主要工作是用真实中国古籍形成可追溯案例、人工真值和可复现实验。本文件区分已完成、机器候选和待完成事项，不把下载量或测试通过率写成研究效果。

## 当前已完成

- 新下载并验证 3 份中国古籍扫描，增补 100 个 PDF 页面。来源库现为 5 份扫描、207 个 PDF 页面，涉及《天工开物》《农政全书》《耕织图》；并非 5 种不同古籍。
- 补充材料优先采用国内馆藏或国内出版来源；国外馆藏中的中国古籍保留为对照。
- 初始《天工开物》28 页库存、Label、Cache、raw OCR 与模型候选保持原输入；新增扫描使用独立 `supplementary_pages.json`。
- 固定第 10、12、14、16、18、22 页作为核心人工复核范围，共 101 个保留框、7 个技术图候选、1 个补框图题，109 个复核项。此前 120—180 框是估算，现以实际框数为准。
- 审核页支持“比赛核心页 / 全部页面”切换；原候选哈希和浏览器草稿键不变。新增完整文字/图题清单的独立确认门。
- 已实现读取真实人工导出的评测/冻结入口。当前真实人工转录尚未接纳，6 页均未通过质量门，指标为 `null/not_evaluated`。

## 补充古籍与用途

| 扫描 | 来源记录 | 页数 | 本地文件 | 计划用途 |
|---|---|---:|---|---|
| 《天工开物》第2册 | 中国国家图书馆 NLC，Commons 目录注明明崇祯十年（1637）自刻本 | 45 | `backend/data/assets/real_pilot_v1/tiangong-kaiwu-vol2-nlc-1637.pdf` | 同书图文对照；保留明显水印，单独记录影响 |
| 《耕织图》 | 中华再造善本 / 国家图书馆出版社影印来源；目录注明清康熙三十五年内府刻本 | 27 | `backend/data/assets/real_pilot_v1/gengzhi-tu-zhsy-1696.pdf` | 蚕桑、缫丝、整经、织造场景的跨书功能对照 |
| 《御制耕织图》 | Harvard-Yenching 中国古籍馆藏，目录注明1696年 | 28 | `backend/data/assets/real_pilot_v1/gengzhi-tu-harvard.pdf` | 同名古籍不同扫描的图像质量与来源对照 |

本地文件已逐个校验 PDF 魔数、精确字节数、Commons SHA-1、本地 SHA-256 和页数。许可依据是各文件描述页的 Public domain / PD-scan 标记；原版古籍、现代影印、馆藏和文件提供方分别登记，不推断未知底本馆藏，也不把古籍公版扩展到现代编校或整套丛书。

来源文件页：

- [国图《天工开物》第2册](https://commons.wikimedia.org/wiki/File:NLC892-411999010751-35278_%E5%A4%A9%E5%B7%A5%E9%96%8B%E7%89%A9_%E7%AC%AC2%E5%86%8A.pdf)
- [中华再造善本《耕织图》](https://commons.wikimedia.org/wiki/File:ZHSY100126_%E8%80%95%E7%B9%94%E5%9C%96_%E6%B8%85%E7%84%A6%E7%A7%89%E8%B2%9E%E7%B9%AA_%E6%B8%85%E5%BA%B7%E7%86%99%E4%B8%89%E5%8D%81%E4%BA%94%E5%B9%B4%E5%85%A7%E5%BA%9C%E5%88%BB%E6%9C%AC.pdf)
- [Harvard《御制耕织图》](https://commons.wikimedia.org/wiki/File:Harvard_drs_54071528_%E5%BE%A1%E8%A3%BD%E8%80%95%E7%B9%94%E5%9C%96.pdf)

`sources.json` 是可提交的来源登记；原始 PDF、派生 PNG、裁剪、OCR、人工导出、报告和冻结数据均留在受控本地目录，不提交 Git、不进入默认 Docker 镜像。

## 核心复核范围

| PDF 页码 | 保留框 | 技术图候选 | 补框图题 | 覆盖目的 |
|---:|---:|---:|---:|---|
| 10 | 26 | 0 | 0 | 竖排正文与复杂字符 |
| 12 | 9 | 2 | 0 | 山箔/治丝等候选图题及部件标签 |
| 14 | 10 | 2 | 0 | 溜眼/经耙等整经结构候选 |
| 16 | 20 | 1 | 0 | 花机候选及正文混排 |
| 18 | 32 | 0 | 0 | 密集竖排正文、阅读顺序 |
| 22 | 4 | 2 | 1 | 赶绵/弹绵候选与漏检图题 |

上述图名、图区、角色和功能为 Inferred，仍需对照扫描确认。范围是有目的的小样本诊断集，不能作为全部古籍或未见版本的总体准确率。

## 人工确认后运行的闭环

先在 `backend` 目录生成带输入哈希的范围和复核页：

```powershell
.\.venv\Scripts\python.exe -X utf8 -m scripts.prepare_competition_scope
.\.venv\Scripts\python.exe -X utf8 -m scripts.build_historical_review_queue `
  --scope data/real_pilot/competition_scope.json
```

打开 `backend/data/real_pilot/model_review_queue.html`，默认显示核心 6 页的全部候选。按扫描逐项确认文字、类别、角色、坐标和顺序，确认本页阅读顺序，再勾选“已检查全页文字与图题，确认清单完整”。逐项确认和完整性确认分开保存，任何修改会撤销相应完整性确认。若发现候选之外的漏框，应先在 PPOCRLabel 补框并重建候选/范围，不能带着漏框勾选完整。模型建议和古文参考只帮助比较，不代替人工确认。

导出后，把实际导出文件保存到 `backend/data/real_pilot/historical-review-overrides.json`。从其他目录导入时，可给 `--review-overrides` 指定实际路径，但评测器仍需要上述受控位置保存完全相同的原始导出副本：

```powershell
.\.venv\Scripts\python.exe -X utf8 -m scripts.convert_ppocrlabel_annotations `
  --accept-file-state --reviewer "<真实复核人标识>" `
  --review-overrides data/real_pilot/historical-review-overrides.json

.\.venv\Scripts\python.exe -X utf8 -m scripts.evaluate_competition_ocr --freeze
```

评测器会重新接纳原始人工导出，并逐项比对 `annotations.human-reviewed.json`，拒绝直接编辑生成文件来替代人工轨迹。Label、Cache、扫描、PDF、候选、参考和库存与固定范围不一致时拒绝出分。没有真值或只完成部分页时，写出缺项报告，指标为空，退出码为 **2**；输入失效/格式错误为退出码 **2**（命令行错误）；完整范围通过时为 **0**。该区别应通过报告中的 `evaluation_status` 和 `freeze_status` 判断，不能把预期阻塞误记成通过。

冻结目录采用内容哈希命名，不覆盖旧快照。包含原扫描、PDF、Label、Cache、候选、人工导出、导入后的 raw/corrected 层、范围、库存、参考和指标口径；再次冻结相同输入返回相同路径。可独立检查：

```powershell
.\.venv\Scripts\python.exe -X utf8 -m scripts.evaluate_competition_ocr `
  --verify-snapshot "<脚本输出的完整快照目录>"
```

## 指标口径

- CER：NFC 归一化、去空白后的字符 Levenshtein 编辑距离，按全部参考字符做 micro 汇总；不繁简转换，不用参考文本替换预测。错误率可能超过 1。
- WER：明确采用 CJK 单字、连续拉丁字母/数字词和标点的混合 token，字段名为 `wer_cjk_character_latin_word`。这不是中文词汇分词 WER，应在论文/报告中说明，不能与采用其他分词器的值直接比较。
- raw 与 server OCR 的识别评测：在同一批被人工转录的原始保留框上，分别比较 Cache 原始预测、固定候选中的 server 原始预测与 corrected 真值。人工改框不会自动重跑模型；补框图题不并入此识别分母。缺失 server 预测不在更小子集上偷偷出分。
- 图题定位召回：以人工完整图题清单为分母，与 raw OCR 检测框按归一化 IoU ≥0.5 做最大一对一匹配。人工新增且 raw 漏检的图题也进入分母。该值反映定位召回，不代表标题转录正确或分类精度。
- raw 检测框没有图题分类，因此不输出没有合理定义的图题 Precision/F1。整页端到端 CER 保持未评测；以后独立建立完整正文与阅读顺序协议再评估。
- 检索 Recall@K/MRR/nDCG 仍需独立人工相关性标签，不能由 OCR 真值、检索排名或核验按钮自动推导。

## 仍需推进的比赛交付

人工核心真值接纳后，先冻结 OCR 诊断集，再将确认过的真实 Figure/TextChunk 和证据导入 PostgreSQL，固定两个真实演示案例：同书图文对照与跨书功能对照。对比 BM25、视觉 baseline、EAFR，使用人工相关性标签；目前线上业务数据仍是 synthetic fixture，不能把补充资料直接当成线上真实检索已完成。

技术报告沿用赛题要求的概述、需求、AI选型、实施、成效、总结、附录结构，写清离线确定性 Provider 的边界和 PaddleOCR 的真实角色。优先补齐证据、实验、演示和复现包，再考虑 ANN、大模型扩展或全量训练。完整比赛材料尚未生成；下载与工程测试并不替代材料验收。

## 2026-10-03 验证记录

- `compileall`、Ruff、Mypy：通过；类型检查覆盖 65 个应用/脚本源文件。
- Pytest：123 passed，2 个既有 FastAPI/Starlette 上游弃用警告。
- 宿主机真实 Chrome 复核页 E2E：4 passed，覆盖核心范围、完整性门、导出、撤销确认、草稿保持、桌面/移动端及坐标边界。
- 5 个登记 PDF 再验证通过；补充库存 100 页，初始 28 页库存哈希保持不变。
- 对真实当前输入运行 `evaluate_competition_ocr --freeze`：`ready_pages=0/6`，`metrics=null`，`freeze_status=blocked_pending_human_truth`。测试中的模拟人工确认没有导入真实数据。
- 本轮未重新执行 Docker 重建、PostgreSQL 集成或业务全栈 E2E；以前的真实验收按历史记录保留。

## 2026-10-04：补充 OCR 与真实数据导入通道

完成国内来源的 12 页 raw OCR 初筛：国家图书馆来源《天工开物》扫描第22—27页，以及中华再造善本出版来源《耕织图》扫描第21—26页。受控选页配置为 `backend/data/real_pilot/supplementary_ocr_selection.json`，独立结果为 `supplementary_ocr_results.json`。这些是机器初筛页，不是已冻结评测集。

| 来源 | OCR 页数 | raw 文本框 | raw_text 字符数（含换行） |
|---|---:|---:|---:|
| 国家图书馆来源《天工开物》 | 6 | 56 | 143 |
| 中华再造善本来源《耕织图》 | 6 | 201 | 687 |
| 合计 | 12 | 257 | 830 |

模型保持锁定的 PaddleOCR 3.0.3 / PP-OCRv5 mobile；所有结果仍为 `inferred / unreviewed`，corrected 为 null。文本框数和字符数是产物统计，不是质量指标。国图水印仍保留在扫描和 raw OCR 中。原28页库存哈希仍为 `c5cd13fe5a68de742d05b7effb0698bbb6a13f405493b768df48518797a255c1`，原 Label、Cache、raw OCR 和模型候选均未重写。

在 `backend` 目录复现或续跑：

```powershell
& "D:\codex-runtime\jitu-paddleocr-3.0.3\Scripts\python.exe" -X utf8 `
  -m scripts.run_real_pilot_ocr `
  --inventory data/real_pilot/supplementary_pages.json `
  --output data/real_pilot/supplementary_ocr_results.json `
  --selection data/real_pilot/supplementary_ocr_selection.json --resume
```

Runner 逐页原子保存；重跑相同输入复用已完成页。库存/扫描哈希、选页范围、模型版本、预处理或缓存完整性不符时拒绝复用，需显式使用新的输出名。已有原28页的旧版 raw 文件不会被迁移或覆盖；非默认库存不能写入默认 `ocr_results.json`，含人工 corrected 的文件不能作为续跑 raw 缓存。

新增 `human_reviewed_real_pilot` 导入契约和 `export_reviewed_real_manifest.py`。保持 synthetic fixture 的全标注要求；真实试点只导入人工确认的图区与图题，允许功能、关系和相关性标签为空。正文与具体图的归属尚未标注，因此不自动把整页正文附到每幅图。人工确认的是转录/坐标，业务证据仍为 Observed/Documented，不自动升级历史主张为 Verified。

导入记录包含原 PDF/扫描 SHA-256、内容寻址快照、人工导出/annotation/候选/范围/来源登记哈希、复核人/日期、图题 bbox，以及 raw→corrected 轨迹。图像向量按 Figure bbox 裁剪后生成，整页扫描资源保留用于回溯。缺少 CFR/置信度时，功能和模型不确定性会标记不可用，不产生 `u_model` 扣分；无查询主张的图片搜索将证据覆盖标为不可用。CFR 摘要中的缺省 uncertainty=1 表示未知，同时返回 `uncertainty.model_available=0` 和分项 availability=false，不是测得的熵。原有固定权重与模态可靠性策略仍是工程基线，没有宣称效果最优。

完成上一节真实人工接纳后运行：

```powershell
.\.venv\Scripts\python.exe -X utf8 -m scripts.export_reviewed_real_manifest
```

脚本先重验人工真值并冻结范围，再额外检查所有待导出的图区、图题分别确认，随后导出 `data/manifests/reviewed-real-core-v1.json` 和 `data/assets/reviewed_real_v1/<snapshot-id>/`，最后通过既有 loader 验证。相同导出幂等；已有 manifest 或扫描不同则拒绝覆盖。CLI 当前真实运行返回 `blocked_pending_human_truth`、0/6页、0导出图，退出2，没有生成真实业务 manifest。

只有导出成功后，才在项目根目录启用只读资源挂载：

```powershell
docker compose -f docker-compose.yml -f docker-compose.reviewed-real.yml up -d
$realJob = Invoke-RestMethod -Method Post `
  -Uri http://localhost:8000/api/v1/ingestion/jobs `
  -ContentType application/json `
  -Body '{"manifest_name":"reviewed-real-core-v1.json","dry_run":false}'
Invoke-RestMethod "http://localhost:8000/api/v1/ingestion/jobs/$($realJob.id)"
```

附加 Compose 文件只挂载已导出的扫描目录；目录不存在时不会自动创建。原 PDF、raw OCR、复核草稿和人工原始导出继续留在宿主受控目录。当前默认三服务已重建并全部 healthy，入口 `http://localhost`，Swagger `http://localhost:8000/docs`；业务库仍为3书/9图/18区域的 synthetic fixture，尚无真实图导入。

本日实际验收：compileall、Ruff、Mypy（66源文件）通过；Pytest **142 passed**（包含1项显式独立 PostgreSQL 集成测试），2个既有上游弃用警告。未配置 `TUJI_TEST_DATABASE_URL` 时该集成测试显式 skipped，不以 SQLite 替代。独立测试库从空库执行 Alembic，完成真实格式重复导入、向量256维、raw/corrected、三类API搜索/会话、许可403及核验提交；断开并重新建立连接后核验仍在，底层证据未变为 Verified。使用的是隔离模拟标注，不计入真实人工真值。

Docker 三服务重建/启动、生产前端构建和 Nginx 全栈 smoke 通过；真实Chrome **7/7 E2E**通过（3项业务闭环、4项本地复核页）。只检查配置的附加真实资源挂载尚未启用。测试完成后清理独立测试容器及其临时数据卷，保留业务数据库和运行服务。本日没有 commit/push。
