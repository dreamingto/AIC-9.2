# 当前状态

## 2026-10-05 V1.2.1 Git 归档复现修复（最新）

- 真实 Git 源码归档暴露 CRLF/LF 转换导致来源登记与冻结包冲突；.gitattributes 保留登记/模型锁/协议/实现哈希源码的原字节，严格恢复器不放宽、不覆盖用户数据。代码 fe93ebc0aa32e55035855dd2c51d9ba365c5a497、冻结261文件与远程完整 tree 相同。
- 新增2字节回归后本地254后端/独立PG3；线上CI37310431347实际257后端/13前端通过。原Chrome10验收仍有效。
- V1.2.1真实Git归档恢复24文件，全部冻结哈希一致；528排名0失败/不稳定，与业务/此前恢复环境176组签名完全相同、指纹253b7b50c756cf58。公开源码710,112字节无凭据完整下载，SHA一致。
- 新release v1.2.1-competition-preview提供修复源码；国内数据/匿名预审材料保持V1.2.0资产，不移动旧tag。详见release/publication.json。业务三服务与GPU保持运行，临时复现环境已停止、卷保留；科学指标仍not_evaluated、团队信息/官方提交pending。

## 2026-10-05 V1.2 修复与发布准备（最新）

- 已修复干净启动、冻结国内输入恢复、过期向量绑定、局部查询整图主张继承、环境权重、主文档状态、CI/OpenAPI字段漂移与Undici高危锁文件。功能草稿独立V2覆盖12图/72槽/45建议/27unknown；不写入业务人工真值。
- 全量后端252 passed/3默认PGskip（独立库另跑3 passed）/2既有上游warning；88源文件Mypy/编译/Ruff/pip通过；前端13测试/lint/构建，npm audit 0。无私密.env新源码目录真实Compose构建，PG新卷0001/0002迁移、12图/88向量恢复；Chrome10 passed。
- V2与恢复库均176适用/16不适用、528排名0失败/不稳定，全部176签名与指纹一致253b7b50c756cf580dfc50cfe7e806e3e8588872cf979b137704e23dad447999；4首项/8前K变化不是改善率。研究指标not_evaluated。
- 已生成198字简介、技术/答辩PDF各8页、HTML与讲稿、真实Chrome系统操作MP4约4:41。正式团队名/编号未知，当前匿名预审版；比赛系统/百度网盘提交未代办。材料源码competition/，产物output/competition/。
- 业务服务已按最终修复代码重建healthy，仍21图/169向量/14合成核验；真实核验0。独立测试和录制作用于恢复库。源码79c3f96与CI修复86edec6正常快进同步，exact tree/commit一致；线上CI37307763298成功，255后端/13前端。公开预审版tag v1.2.0-competition-preview冻结86edec6，7资产uploaded且摘要全同。发布记录release/publication.json。

以下保留历史阶段状态；阅读时以最新记录为准。

## 2026-10-05 项目与 Git 完整性审查（最新）

- 本地比赛原型可运行，三个业务容器 healthy，BGE/Chinese-CLIP ready/cuda，17 个 API 操作、两个国内案例及4图扫描资源可读。只读 SQL 确认21图/32区域/169向量/88会话/739候选；真实12图、35文本Inferred、corrected/功能/关系/核验均0。
- 本轮重新执行：235后端passed/3独立PG默认skip/2上游提醒、83源文件Mypy、编译/Ruff/pip check；前端lint/Vitest12/构建；现有会话与许可403、Compose config、git fsck/diff检查通过。未重跑隔离PG迁移、浏览器E2E、镜像构建或528排名，未改业务数据。
- 实查GitHub API远程main与本地HEAD均e09b6ca（9月29日）、远程143文件；审查前43修改/79未跟踪/0暂存，最新神经模型、0002、真实案例和实验代码未提交。Git对象无损坏；Git传输的失效代理/连接重置未修，API直连核实成功。
- 当前HEAD隔离快照直接Compose因.env缺失失败；真实冻结输入/模型/报告不在Git且精确实验协议绑定旧manifest哈希，须独立恢复包与干净目录验收。主文档旧状态、区域继承整图主张、权重未环境配置、草稿覆盖4/12与比赛材料缺口已列入建议。
- 下一步建议（pending）：先冻结完整代码/可恢复数据和清晰启动说明，再背景图AI证据/局部边界与比赛PDF/视频/答辩材料；不新增人工前置门。审查报告docs/机图索隐_项目与Git完整性审查_2026-10-05.md；本轮未commit/push。

## 2026-10-05 固定查询对照与案例功能草稿（当前）

- 完成24固定开发集查询（16文本/4图/4区域）、8种方法/消融；只读PG锁定12真实图/50兼容512维向量，不混9synthetic。176适用+16不适用，每组1+2重复=528排名计算，失败0/不稳定0；跨完整运行176签名相同。
- 两个国内案例4图的20非unknown功能、4unknown、10关系草稿绑定扫描/AI来源/精确引用；全部Inferred/confidence=null，关系图不评分，不造古文/人工/qrels。功能工程可靠性0.5公开，不是概率；裁剪查询不继承框外功能。
- eafr_drafts仅在实验工具参与重排，未改默认API/业务标签。水力宽泛查询由土礱/水碓/水磨变为水碓/水磨/土礱；整经查询从整经偏向织机，明确覆盖偏差。3首项/4前K顺序变化不等于改善率；研究指标not_evaluated。
- 新26回归，全量235 passed/3既有opt-in默认skip/2既有warning；compileall/Ruff/Mypy83通过。业务9类计数前后相同（169向量/88会话/739候选）；三服务仍healthy。本轮未重跑前端/E2E/隔离PG迁移，未commit/push。
- 说明docs/机图索隐_固定查询算法对照与功能证据草稿.md；CLI在backend运行python -X utf8 -m scripts.run_domestic_comparison。最终报告retrieval_comparison/5c005b8e95133a58/20261005T094332Z-d18e438e，运行产物Git/Docker忽略。
- 下一步用真实对照写技术报告/3—5分钟视频；背景图功能覆盖与独立评测另建版本，暂不人工审核。

## 2026-10-05 真实模型与固定案例（当前）

- 已接入BGE-small-zh-v1.5中文文本及Chinese-CLIP ViT-B/16视觉/中文图文；固定revision、预处理hash、文件SHA256和Windows/Python3.12依赖锁。独立D盘推理环境，Torch2.7.1+cu128/Transformers4.51.3，RTX4060 Laptop8GB实际CUDA运行，8767健康。
- 新增0002_model_spaces迁移修复初始unique实体/模态索引的多模型冲突，保留全部旧数据。当前74基线256维+95神经512维=169向量；重建幂等，匹配完整模型身份，缺索引/服务返回503，无混算/静默回退。
- /demo固定国内出版《耕织图》织机与国图馆藏《天工开物》水碓/水磨，原图/框/来源/实时API/实际排名；新增2个API操作，17个V1操作。不造qrels/人工/历史Verified。
- 209常规后端pass、3项opt-in默认skip且独立空PG迁移/集成3pass；编译/Ruff/Mypy77源文件，前端lint/Vitest12/生产构建、Chrome全栈6pass，HTTP两案例6搜索及会话重读。三业务服务healthy，测试容器已停止可恢复。
- 真实文本35 Inferred、corrected0、真实核验0，原PDF/raw/旧审核草稿保留；研究指标not_evaluated，宽泛水力文本查询会首排土礱，已如实记录。
- 当前启动：先backend/model_runtime/start.ps1，再Compose同时加ai-real与neural两个overlay。入口http://localhost/demo；详细docs/机图索隐_真实检索模型与固定案例.md。下一步比赛技术方案/演示稿/扩展国内语料，暂不人工审核；未commit/push。

## 2026-10-05 国内古籍AI比赛版（上一阶段）

- 用户confirmed：优先国内出版内容，比赛阶段暂不人工审核。旧人工0/6不是当前演示开发阻塞，正式研究指标仍not_evaluated。
- 完成独立AIRealManifest/ai_assisted_real_pilot、hash-bound导出、只读overlay及三类搜索的语料筛选。人工RealManifest质量门保留，没有fake人工或corrected真值。
- 实际AI图像整理并导入：国内出版来源《耕织图》8图/5扫描+国图馆藏《天工开物》4图/3扫描，共12图、14区域、35文本、65局部raw行、59证据、38向量。全部AI文本Inferred、扫描Observed、目录Documented，0功能/图关系/qrels标签。
- 业务库实际5书/17页/21图/32区域/53文本/86证据/74向量，含原9图synthetic。原扫描/raw/人工候选/旧AI导出保持。
- manifest ai-real-domestic-8b4defa06141f66e.json；当前启动必须加docker-compose.ai-real.yml以保留选中扫描挂载。
- 后端197 passed/2 opt-in默认skipped/2既有warning；独立PG空库迁移和两项集成2 passed。71源文件编译/Ruff/Mypy，前端lint/Vitest12/生产构建、Chrome E2E5项、HTTP真实三模态smoke通过；三服务healthy。
- 修复多区域保存后重读排序、Nginx合法扫描413、小数坐标step限制；前端显示真实图题与来源/AI状态并提供数据筛选。
- 后续优先真实中文文本/视觉Provider及比赛案例/材料，暂不安排人工复核；未commit/push。入口docs/机图索隐_国内古籍AI比赛演示.md。以下为历史记录。

## 2026-10-05 第二轮AI复核与证据草稿（当前）

- 当前candidate仍c4a07f9b9be9；核心6页113项实际AI checked，16项读序重检完成。6文字留空/13unknown、52原框非空修改，统计不是准确率。原输入与旧AI导出保持。
- 新round2实际导出SHA-256为d71b571a002d423f59c5092fe7c56a35aef98ef1257e8bb60e5c29033f34d5f2；独立审计与人工/AI页绑定该文件。人工仍0/543、核心0/6。
- 新prepare_competition_evidence_drafts读取active revision/显式链接计划，核查raw/边界/完整清单/读序/扫描/PDF和AI来源，按指纹生成不覆盖的7图/10指定正文框/6有引用功能草稿/2案例/7无标签查询。目录evidence-drafts-971fb3e505444829，全部Inferred。
- 修复旧image onload回调覆写新条目裁剪；Browser快速切换小框11×7且ID一致，人工页无自动确认。AI页从实际导出恢复113检查，不回退迁移种子97。
- 全量177 passed/1独立PG skipped/2既有warning，compileall/Ruff/Mypy69源文件通过；实际接纳AI/freeze/export均退出2，0/6、metrics=null、0图，没有真实业务manifest。
- 三Docker服务healthy；未重建镜像/独立PG/前端全套/业务E2E/commit/push。下一步国内图文对照与独立AI试点导入设计，正式真值门保持。计划见docs/机图索隐_下一阶段执行计划.md。下面保留上一阶段历史。


## 2026-10-05 补框版本（上一阶段）

- 已创建独立`review_revisions/supplements-v2-c4a07f9b9be9`，active_revision.json指向该目录；旧候选、Label、Cache、人工页/草稿及AI导出保持。准备草稿目录保留，不作为当前版本。
- 核心6页现在113项（101原OCR框+4新增区域+7图区+1补框图题），全队列543项。109旧AI建议迁移，4新框已检查；16项顺序变化撤销AI检查，当前97已检查、16待重检，全部仍待独立人工。
- 补框raw/original_box_index为空；确认后只追加版面/corrected轨迹，不造raw预测。完整性门必须包含新框，保留原框CER/WER排除补框并明确计数。11文字留空、13原未知项和正文/小注边界疑点仍待裁决。
- 新人工页显示真实UI导出绑定的AI建议，采用后不勾确认；Browser已验证0/543人工确认、整页门均false。独立人工真值仍0/6，接纳AI/冻结/真实导出实际均退出2、metrics=null/0图/not_evaluated。
- 新增9项回归，最新全量158 passed/1独立PG skipped/2既有warning；编译/Ruff/Mypy68源文件通过。三服务healthy，未重建镜像、未重跑业务E2E、未commit/push。
- 新版本操作和后续接纳/冻结/真实导出命令见`docs/机图索隐_AI辅助复核交接.md`最前一节。下面109项记录保留为上一阶段历史。

## 2026-10-05 AI 扫描复核收尾

- 核心6页109项已完成AI辅助扫描检查并保存逐项备注：101原框、7图区、1补框图题；50原框提出非空修订，13未知项、9文字留空项仍待裁决。这是检查统计，不是准确率或人工真值。
- 独立AI页面/草稿/导出均保持`ai_assisted / inferred / requires_human_confirmation`，原人工草稿、candidate/inventory/Label哈希未改。第10页至少两列正文漏框，须在新标注/候选/范围版本补齐，不能将原109项清单勾为完整。
- 修复CLI `__main__`与包导入产生两份异常类的问题；共享ConversionError及2项真实模块入口回归覆盖AI拒绝、无traceback与旧输出保持。
- 最新compileall/Ruff/Mypy（67源文件）通过；pytest149 passed/1 skipped/2既有上游警告。独立PG集成未配置测试库而skip，本轮未重跑前端或业务E2E。
- 实际AI接纳退出2且没有人工产物；实际冻结仍0/6、metrics=null、blocked_pending_human_truth/not_evaluated、退出2。
- 已恢复今天停止的Docker三服务和127.0.0.1:8766复核服务；三服务healthy，4个入口HTTP200，实际业务计数仍3书/9图/18区域synthetic。原人工标签页保留，AI页显示109/539及原草稿。
- 交接入口：`docs/机图索隐_AI辅助复核交接.md`。下一步先补漏框/夹注边界，再独立人工逐项确认、顺序和完整清单；通过后冻结/评测/真实导入。未commit/push。

## 2026-10-04 最新增量

- 国内国图《天工开物》22—27页、中华再造善本《耕织图》21—26页独立raw OCR完成：12页、257框、830个raw_text字符（含换行）；全部Inferred/unreviewed，未写入corrected。原28页库存/标注/OCR/候选未重写。
- OCR Runner增加独立库存/输出、选页配置、逐页检查点、续跑哈希/范围/版本/结果完整性校验，拒绝覆盖主库存、原raw或人工修订。
- 真实图区/图题导入契约、完整真值门控导出、原PDF/扫描/审核快照哈希和raw/corrected复核轨迹完成；真实格式允许空功能/图谱/相关性标签，synthetic要求保持。
- 真实图像向量使用Figure bbox裁剪；缺CFR/置信度或无查询主张时分项标为不可用，不因资料缺失制造u_model扣分。权重/可靠性仍为工程基线。
- compileall/Ruff/Mypy（66源文件）通过，Pytest142通过含独立PG集成；2既有上游警告。Docker三服务重新构建且全部healthy，全栈smoke及7项Chrome E2E通过。
- 当前真实核心真值仍0/6；导出器实际返回blocked_pending_human_truth/0图/退出2，没有真实业务manifest，业务库仍synthetic 3书/9图/18区域。独立测试库采用模拟标注且已清理，不算真实真值或效果评测。
- 本轮未commit/push。项目入口http://localhost，Swagger http://localhost:8000/docs；下一步由实际人工核心109项/顺序/完整性确认解锁真实导入与比赛评测。

## 已完成

- 工程配置、Docker Compose、Dockerfile、Alembic 显式迁移。
- SQLAlchemy 领域模型和 provenance 字段。
- 受控 manifest loader、SHA-256/PNG/许可校验和稳定 UUID 导入器。
- 256 维确定性文本/图像 Provider、BM25、规则 CFR、关系 Provider 和 EAFR。
- FastAPI V1 路由、统一错误、request ID、CORS、资源访问和核验持久化。
- React 19/TypeScript/Vite 前端，完成文本、图片、区域三模态搜索，以及来源浏览、图详情、候选比较和人工核验流程。
- Zod API 防腐层、请求中止与路由切换状态隔离、许可受限图片降级、Capabilities 驱动的 Provider 与上传限制展示。
- Nginx SPA 回退和 `/api/` 反向代理；Compose 已加入前端服务及健康依赖。
- 修复前端容器健康检查的 IPv6 `localhost` 解析问题，统一使用 `127.0.0.1`。
- 新增标准库全栈 smoke runner，以及 3 项基于真实 Chrome 的 Playwright E2E。
- 清理前端 API 契约技术债务：nullable/必填字段对齐、统一契约错误、AbortError 和请求竞态隔离。
- 3 sources、9 figures、18 regions、54 functional assertions、27 evidence、12 benchmark pairs fixture。
- 新增 `docs/机图索隐_项目策划书.md`、`docs/机图索隐_项目需求文档.md` 和 `docs/机图索隐_项目技术文档.md`，分别覆盖竞赛策划、产品需求与当前实现细节。
- 三份文档均区分已实现能力与后续规划，并明确 fixture 为 `not_evaluated`；真实扫描已完成来源登记、页面准备和 raw OCR 试点，人工真值、真实语义模型和 ANN 尚未接入。

## 验证结果

- Python 回归：截至 2026-10-03 为 123 passed，2 个上游弃用警告；容器运行时为 Python 3.12.14。
- `ruff check .`：通过。
- `mypy app scripts/smoke_fullstack.py`：通过（46 个应用源文件和 1 个 smoke runner）。
- `python -m compileall`：通过。
- `pip check`：通过，无损坏依赖。
- FastAPI OpenAPI：15 个 V1 操作已注册，Swagger 返回 200。
- 前端 Node 22：`npm ci` 成功且 0 vulnerabilities；Oxlint 通过；Vitest 2 个测试文件、11 项测试通过；TypeScript/Vite 生产构建通过。
- `docker compose config --quiet`：通过。
- `backend/scripts/smoke_fullstack.py`：通过，覆盖健康、导入、三类检索、会话、候选、核验与资源许可。
- Playwright：3/3 通过，使用真实 Chrome 与 Nginx/API/PostgreSQL 链路。
- 文档自检：三份 Markdown 均已落盘；标题结构无重复章节序号；15 个 V1 操作、15 张领域表、V1.1-A 的 39 项基线测试与 V1.1-B 的 47 项当前测试及 fixture 规模与代码和验收记录一致。

## 数据库验收状态

- `docker compose --progress plain build` 与 `docker compose up -d` 均通过。
- 使用 PostgreSQL 16 和 PGDG pgvector 0.8.6；迁移版本为 `0001_initial`。
- 数据库有 15 张领域表及 `alembic_version`，共 16 张 public 表。
- pgvector 实际保存 image 27 条、text 9 条，向量维度均为 256。
- fixture 重复导入完成且核心实体稳定为 3 books、9 figures、18 regions。
- 文本、图片、区域检索均读取数据库并返回有限分数。
- 核验状态在后端重启及镜像重建后仍存在；底层 Evidence 未被自动升级。
- 6 个可再分发资源返回 200；3 个受限资源返回 `LICENSE_RESTRICTED` 403。

2026-09-04 已重建并启动完整三服务，`db`、`backend`、`frontend` 均为 healthy；在新容器上重新执行全栈 smoke 与 Playwright E2E 均通过。

## 未完成

2026-10-03 增量：新增国内国图《天工开物》45页、国内出版来源《耕织图》27页、Harvard中国
古籍《御制耕织图》28页；来源库5个PDF/207页/3部中国古籍，新增100页独立库存。
原28页inventory哈希仍为 `c5cd13fe5a68de742d05b7effb0698bbb6a13f405493b768df48518797a255c1`。
核心原第10/12/14/16/18/22页实际101框、7图区、1补图题，109项；完整性导出、固定范围评测与
内容寻址冻结工具完成，真实就绪仍0/6、metrics=null、not_evaluated。新扫描尚未OCR/业务导入。
最新65源文件类型检查、123项后端测试、4项Chrome复核页E2E通过；本轮未重跑Docker/PG/业务集成。

- 真实古籍页面尚未导入业务数据库；当前只完成 raw OCR 与未审核 annotation 草稿，人工真值、真实语义模型和研究指标尚未完成。
- EAFR 当前使用代码级注入权重和固定模态可靠性（可用 1、不可用 0）；环境配置、来源质量驱动的动态缩放与效果验证尚未完成。
- 现有 3 项 Playwright E2E 聚焦核心闭环，错误码矩阵、移动端视口、可访问性扫描和视觉回归仍未覆盖。
- OpenAPI 与 TypeScript/Zod 仍为人工同步，尚未建立自动代码生成或契约漂移 CI。

## V1.1-B 真实数据试点（当前增量）

- 已从 Wikimedia Commons / National Archives of Japan 登记并下载《天工开物》第二册（28 页）和《农政全书》第一册（79 页）。来源 URL、Commons SHA-1、本地 SHA-256、字节数、页数和许可字段已写入 `backend/data/real_pilot/sources.json`。
- 已运行 `backend/scripts/prepare_real_pilot.py`，完成首批 28 页 PNG 渲染并生成 `backend/data/real_pilot/derived_pages.json`；页面 `layout.status=pending_review`，OCR `status=pending_provider`。
- 新增 `backend/data/real_pilot/annotation_schema.json` 和可选 `PaddleOCRProvider` 契约；独立 OCR 环境已锁定为 Python 3.12.14、PaddlePaddle 3.0.0、PaddleOCR 3.0.3、PaddleX 3.0.3 和 PP-OCRv5 mobile 模型。
- 原始 PDF/渲染 PNG 未纳入 Git；真实数据尚未批量导入 Page/Figure/TextChunk，首张 raw OCR smoke 已完成，效果评测仍未开始。

## V1.1-B OCR 基线（2026-09-29）

- OCR 依赖独立锁文件为 `backend/requirements-ocr.lock`，不污染 `backend/.venv`，不进入默认后端 Docker 镜像。
- 通过 `127.0.0.1:7890` 下载并缓存 PP-OCRv5 mobile 检测/识别模型；`backend/scripts/run_real_pilot_ocr.py --limit 1` 成功生成首张页面 raw OCR。
- 首张页面输出 39 条有效 raw OCR 行、192 个字符，Provider 元数据为 `paddleocr / PP-OCRv5_mobile / 3.0.3`；`corrected_text=null`、`review_state=unreviewed`、`evaluation_status=not_evaluated`。
- Provider 增加 PaddleOCR 3.x `OCRResult.json`、NumPy 坐标和 Windows 中文路径兼容；OCR 结果仍未导入数据库，尚未人工校订或评测 CER/WER。
- 28 页批量 raw OCR 已完成：701 行、7392 个 raw 文本字符、0 空页；人工 corrected/reviewed 页仍为 0。
- PPOCRLabel raw Cache 已转换为项目 annotation 草稿：28 页、732 框；转换器保留四点顺序、归一化 bbox、raw/corrected 分层和 provenance，输出继续为 `not_evaluated` 且受 Git 忽略。
## V1.1-B 人工版面审核快照（2026-09-29）

- 用户完成保存后，28 页 `fileState=1`，Label 从 732 个 raw 框筛为 525 个，净删除 207 个；28 页均与 Cache 存在差异。
- 审核语义已拆分：28 页 `layout_reviewed`，0 页 `transcription_reviewed`。原始 Cache 继续保存在 raw OCR 层，`corrected_text` 不因删框自动生成。
- 内容寻址快照为 `commons-najda-tiangong-kaiwu-2-layout-2e7bf4a41b9e`，包含 Cache、Label、fileState、页面库存、派生 annotation、质量审计与哈希清单；该目录受 Git 忽略。
- 质量审计：522 个保留框文字与 Cache 完全相同、0 个同坐标文字修订、3 个新/移动坐标、0 页阅读顺序变化；第 8 页仍残留 `国立公文書館 / National Archives of Japan`。
- 当前 `layout_snapshot_ready=true`，但 `transcription_evaluation_ready=false`、`evaluation_set_freeze_ready=false`；CER、混合 CJK WER 和图题召回率均为 `not_evaluated`。

## V1.1-B 模型辅助复核（2026-10-02 最新）

- 上述 525 框为历史初筛快照。第 8 页两个馆藏水印框已受控移除；现有 523 框，Label SHA-256 为 `0c561930d8ddbb51160d3338d65e7cc2af319ab00340623f88c4e3f54c46750f`。
- Wikisource《乃服》36 节已下载并保留 provenance。改为章节锚点独立对齐后，253 个正文框平均 alignment confidence 为 0.845，低于 0.5 的框为 1；这是对齐置信，不是 OCR 准确率。
- 锁定 PaddleOCR 环境已对 523 框完成 `PP-OCRv5_server_rec` 二次识别，长竖列逆时针旋转、输入尺寸 `(3,48,1024)`，指纹缓存支持恢复；保守共识候选 88 项。
- 本地审核页覆盖 523 OCR 框、13 技术图区、3 补框图题，共 539 项；默认优先队列为 280 项，关键冲突为 169 项，延后项为 259 项。
- 已支持整页扫描、阅读顺序叠加、类别/角色/坐标修改、本页顺序单独确认、哈希隔离草稿和人工确认导出。
- 转换器可接纳逐项 human overrides；只修改 corrected/审核元数据，保留 raw/Cache，部分审核标 partial，完整文字和顺序审核才建立页级 corrected；图题与图区独立核验。
- 后端 106 项测试通过，compileall/Ruff/Mypy 通过；本地审核页真实 Chrome 3/3 E2E 通过，桌面/390px 手机截图已复核。应用内浏览器插件缺少运行文件，本轮使用现有 Playwright/Chrome 验收。
- 真实人工转录、图题确认和本页阅读顺序确认仍未接纳；正式评测集冻结、CER/WER/图题召回及数据库导入仍 pending/not_evaluated。测试导出只在隔离浏览器上下文中验证，不算真实审核。
