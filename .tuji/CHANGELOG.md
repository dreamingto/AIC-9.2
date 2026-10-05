# 变更记录

## 2026-10-05 V1.2 完整性问题修复

可选.env/三档启动、冻结输入与向量恢复、区域证据空间边界、JSON权重、12图草稿V2、PG/Chrome干净复现、CI/OpenAPI漂移检查、Undici锁修补、当前文档及匿名比赛材料。具体代码与验收见docs/机图索隐_V1.2修复与交付记录.md；Git/发布最终结果后续记录。

## 2026-10-05 项目及 Git 审查

新增完整性报告与分级后续计划，重新执行前后端质量检查/运行只读核对，并经GitHub API确认远程仍为9月29日143文件提交e09b6ca。发现最新代码未提交、干净HEAD缺.env启动步骤、冻结真实输入恢复链不完整、局部证据范围及文档/配置/比赛材料缺口。仅新增审查文档和日志/记忆，未修改业务代码、数据、代理或Git远程。

## 2026-10-05 固定真实查询与功能证据草稿

- 新24查询/8方法实验协议与只读PG比较执行器，锁真实语料/神经模型/来源/向量/实现；没有硬编码候选或期望名次。
- 两国内案例4图AI功能20/unknown4/关系10扫描绑定草稿；精确AI引用、null置信度、区域范围、高置信度图关闭和证据覆盖政策。
- 实际176组合/528计算及跨完整运行签名验证，报告同时保留水力名次变化与整经偏移/覆盖限制；指标not_evaluated。
- 新26回归，235全量通过；编译/Ruff/Mypy83通过，业务计数保持，运行产物忽略，交接/说明更新。

## 2026-10-05 真实中文检索模型与国内案例

增加固定BGE/Chinese-CLIP合同、隔离GPU worker/下载/依赖文件锁、严格HTTP Provider与显式profile、中文图文共享空间及版本兼容选向量；新增事务重索引与0002完整模型唯一索引，原基线保留。增加两个真实案例API、React /demo扫描/框/来源/实际检索入口和Zod/E2E；补充真实模型smoke、工程/PG测试、README/技术文档/下一步/交接记录。当前169向量、模型与三业务服务就绪；研究指标not_evaluated，未commit/push。

## 2026-10-05 国内古籍AI比赛演示

- 新增AIRealManifest、domestic_ai_selection、hash-bound真实导出与HTTP smoke、只读Compose overlay；导入12真实图/8扫描/14区域/35文本/59证据/38向量。
- API新增data_status/title/文本origin及dataset_kinds筛选；前端显示来源和AI状态、图题与原图入口。人工真值/Verified门保留。
- 修复多区域候选重读次序、Nginx扫描413及小数坐标步长；补充20项后端回归、AI PG集成、前端语料契约与2项真图E2E。
- 验证197常规后端、独立PG2、前端12、Chrome E2E5；运行三服务healthy，旧数据保留。当前指南docs/机图索隐_国内古籍AI比赛演示.md；未commit/push。

## 2026-10-05（第二轮AI图像复核与证据草稿）

- 实际复核113项全部AI checked，保存独立round2/audit，文字留空11→6，unknown仍13。原数据与旧导出保持。
- 新显式图文链接配置与prepare_competition_evidence_drafts，生成7图/10正文框/6引用功能/2案例/7无标签查询，按输入指纹寻址，不改正式真值门。
- 修复异步预览覆写当前条目的问题；AI页支持实际导出恢复，人工页仍无预填确认。
- 新增19回归，全量177 passed/1 skipped；更新执行计划、README、交接与Obsidian。未commit/push。


## 2026-10-05（补框新版本）

- 新增补框候选版本生成器和4框配置，迁移原109条AI建议、保存原序号/审计并撤销16项变化确认；当前核心113项，旧数据/草稿不覆盖。
- 区分原OCR框与raw为空的补框；接纳器追加corrected/版面修改轨迹，范围完整性包含补框，保留原框评测排除补框并计数。
- 新复核页面可展示哈希绑定AI建议、采用建议后撤销确认、动态裁剪；CLI支持独立版本的候选/范围/人工导出/评测及真实导出路径。
- 新增9项回归，158 passed/独立PG1 skipped，68源文件检查通过；实际113条AI导出保存，独立人工仍0/6，3个质量门退出2，正式研究指标未评测。
- 更新交接/状态/测试及记忆；三服务healthy，未重建镜像/业务E2E/commit/push。
## 2026-10-05（AI 扫描检查收尾）

- 保存核心109项AI扫描检查与逐项备注，独立AI队列/草稿/导出保持Inferred及待人工；人工接纳器同时拒绝文件级与记录级AI来源和pending标记。
- 第10页发现至少两列正文漏框，记录新副本补框定位；保留原Label/候选/范围与草稿，不伪造完整性确认。
- 新增共享annotation_errors，修复模块CLI与包导入形成不同ConversionError而未捕获的问题；2项subprocess回归验证真实拒绝路径及已有输出保持。
- 最终149后端测试通过，独立PG测试1项skip，67源文件类型/静态/编译检查通过；实际AI接纳和freeze分别退出2，人工真值0/6、指标未评测。
- 启动今天停止的现有Docker三服务及loopback复核服务，healthy/HTTP200，数据库仍synthetic 3/9/18。新增AI复核交接文档并更新状态记录；未commit/push。

## 2026-10-03

- 下载核验国图《天工开物》45页、国内出版来源《耕织图》27页及Harvard《御制耕织图》28页，登记5份扫描/207页，生成独立100页补充库存和检查contact sheet，原28页/Label/Cache/raw保持。
- 固定6页/101框/109项比赛复核范围，新增核心过滤与独立完整文字/图题清单确认，保留候选哈希和旧浏览器草稿键。
- 实现原人工导出重校验、固定范围质量门、保留转录框OCR评测、漏检图题定位Recall及内容寻址冻结/篡改检查。实际0/6页就绪，not_evaluated，不创建真实快照。
- 新增17项后端测试，123项通过；65源文件检查和4项真实Chrome复核页E2E通过。新增运行说明和来源/状态/交接记录。
- 未导入新扫描到业务数据库、未重跑Docker/PG/业务集成、未commit/push；所有真实资产/人工产物继续本地受控。

## 2026-10-02

- 续作模型辅助复核链：第 8 页已受控删除两个水印框，当前 Label 为 523 框。
- Wikisource 36 节参考采用显式标题/正文锚点独立对齐，平均对齐置信由约 0.49 提升至 0.845；并完成 523 框 PP-OCRv5 server 二次识别、指纹缓存及 88 项保守共识候选。
- 补齐 3 个无 OCR 框的图题候选，构建全部 539 项/优先 280 项的本地复核页，支持扫描/顺序/类别/坐标/图题确认和哈希绑定导出。
- 新增 human overrides 接纳器，保存逐框修改轨迹、partial corrected 和独立图题真值；拒绝陈旧哈希、模型推断、重复记录、非法坐标与顺序，不自动生成评测指标。
- 移除审核构建器递归删资产逻辑，改为内容寻址目录并保留已有文件；真实审核产物加入 Git/Docker 忽略规则。
- 全量后端检查通过（106 tests）；新增真实 Chrome 本地审核页面 3 项 E2E，桌面/手机截图和实际 JSON 导出均通过。
- 未接纳真实用户逐字确认、未冻结正式评测集，CER/WER/图题召回保持 not_evaluated。

## 2026-09-29

- 安装并锁定独立 Windows CPU OCR 环境：Python 3.12.14、PaddlePaddle 3.0.0、PaddleOCR 3.0.3、PaddleX 3.0.3。
- Provider 显式使用 PP-OCRv5 mobile detection/recognition 模型，兼容 PaddleOCR 3.x `OCRResult.json`、NumPy 坐标和 Windows 中文路径。
- 通过 `127.0.0.1:7890` 完成模型下载和首张真实页面 raw OCR smoke；过滤空白检测框后生成 39 条有效 raw OCR 行、192 个字符，保持 `corrected_text=null`、`review_state=unreviewed` 和 `evaluation_status=not_evaluated`。
- 新增 `backend/requirements-ocr.lock`；OCR 环境与默认后端依赖、Docker 镜像和数据库导入保持隔离。
- 新增 `convert_ppocrlabel_annotations.py`，受控解析 `Cache.cach`、`Label.txt` 和 `fileState.txt`，校验页面库存哈希、路径、四点坐标与边界，原子生成被 Git 忽略的 annotation 草稿。
- 增加人工审核门控：PPOCRLabel 工具状态默认不升级 `reviewed`；后续进一步拆分为版面审核与转录审核两道独立门。
- 真实 Cache 转换结果为 28 页、732 框、0 reviewed/corrected 页、`not_evaluated`；检测到的 25 条 `fileState` 与 Label 全部和 Cache 相同，仅记录为工具状态。
- 初版转换器落地时后端回归为 69 passed；compileall、Ruff 和 Mypy（55 个源文件）通过。
- 人工保存后的 28 页 Label 与 Cache 已产生真实差异：732 个 raw 框筛为 525 个，净删除 207 个框，28 页均有 fileState。
- 将审核状态拆为 layout 与 transcription 两道门；当前只接纳 28 页版面审核，`corrected_text` 仍为空，避免把删噪框误写为逐字校订。
- 新增质量审计器与内容寻址冻结器；冻结本地快照 `commons-najda-tiangong-kaiwu-2-layout-2e7bf4a41b9e`，范围明确为 `layout_review_only/not_evaluated`。
- 审计发现 522 个保留框文字与 raw 完全相同、0 页发生阅读顺序调整、第 8 页残留馆藏水印，且 PPOCRLabel 无 caption 类别；CER/WER/图题召回率因此保持未评测。
- 完整后端回归更新为 77 passed；compileall、Ruff 和 Mypy（57 个源文件）通过。

## 2026-09-04

- 完成 V1.1-A 演示可靠性增量：前端 API 边界 Zod 契约、统一错误转换、AbortError 与跨路由竞态隔离。
- 修复前端 Docker 健康检查的 IPv6 回环误判，三服务重建后均为 healthy。
- 前端 Dockerfile 增加 BuildKit npm 缓存、关闭构建期 audit/fund，并跳过生产镜像不需要的 Playwright 浏览器下载。
- 新增 `backend/scripts/smoke_fullstack.py`，通过 Nginx 入口验证幂等导入、三类检索、会话、候选、核验和资源许可。
- 新增 Playwright 配置与 3 项全栈 E2E，真实 Chrome 下来源、文本核验、图片和区域检索全部通过。
- Vitest 明确只收集 `src/**/*.test.{ts,tsx}`，避免与 Playwright E2E 互相污染；11/11 组件测试通过。
- 后端 39 项测试、Ruff、Mypy、compileall、pip check，前端 lint/test/build，全栈 smoke 与 E2E 均通过。
- 更新 README、PRD、技术文档和 `.tuji`，将下一里程碑明确为 V1.1-B 真实数据与 OCR 试点。

## 2026-09-03

- 完成 FastAPI V1 的 15 个公开接口与统一错误格式。
- 完成显式 Alembic migration、受控 fixture 导入和稳定 UUID upsert。
- 完成三类检索、确定性 Provider、CFR、关系图和 EAFR 可解释评分。
- 完成资源许可检查、图片安全校验、人工核验持久化和 OpenAPI 契约测试。
- 新增 README、前端对接提示词和 `.tuji` 交接记录。
- 修复 Python 3.12 下 slots dataclass 业务异常初始化失败。
- 修复 Alembic 扩展预执行触发隐式事务、导致完整迁移在连接关闭时回滚。
- 新增可复现 PostgreSQL 16 + PGDG pgvector 0.8.6 镜像与后端运行时锁文件。
- 完成真实容器导入、三类检索、pgvector、许可控制和核验持久化验收。
- fixture 来源 C 设置为禁止再分发，用于端到端许可测试。
- 新增 `docs/机图索隐_项目策划书.md`、`docs/机图索隐_项目需求文档.md` 和 `docs/机图索隐_项目技术文档.md`。
- 三份文档以当前代码和 `.tuji` 验收记录为事实基线，明确区分已实现与计划能力，并持续标注 fixture 为 `not_evaluated`、OCR/真实模型/ANN 尚未接入。
- 完成文档标题结构与关键事实自检：无重复章节序号，15 个 V1 操作、15 张领域表、39 项测试和 3/9/18/54/27/12 fixture 规模表述一致。
- 完成语义边界复核：明确前端结果页仍待建设、效率收益待用户验证、OCR 转录核验不等于史实核验，并将动态模态可靠性缩放标为部分实现。
- 集成 React 19、TypeScript、Vite、Zod、Vitest 前端，完成三模态检索、来源浏览、图详情、候选比较和人工核验交互。
- 新增前端 Dockerfile、Nginx SPA/API 代理配置、Compose 前端服务和健康依赖。
- 前端静态与自动化检查通过：Oxlint、11 项 Vitest、TypeScript/Vite build；本轮 Docker daemon 与浏览器 E2E 标记为 `not_run`。
- 更新 README、项目文档和 `.tuji`，消除“只交付前端提示词”的过时说明，并记录非阻塞契约技术债务。

## 2026-09-04（V1.1-B 真实页面准备）

- 新增真实古籍来源登记：Commons / National Archives of Japan 的《天工开物》第二册和《农政全书》第一册。
- 新增下载器校验后的 SHA-256 元数据、首批 28 页 Poppler 渲染脚本和页面级 `derived_pages.json`。
- 新增版面/OCR 双层标注模板及可选 PaddleOCR Provider；缺少运行时显式报告不可用，不回退到 fixture 文本。
- 后端回归由 39 项增至 47 项通过；真实 OCR、人工标注、数据库导入和研究评测仍未完成。

- 新增受控 `run_real_pilot_ocr.py`：安装 OCR runtime 后可写入 raw OCR 结果；未安装时返回 `MODEL_UNAVAILABLE`，不生成伪造文本。

- 更新 `backend/.dockerignore`，排除真实 PDF 和渲染 PNG；后端镜像构建上下文从约 111 MB 降至约 16 KB，并在重建容器后健康检查通过。

- 收窄 Compose backend 数据卷为只读 `manifests` 与 `fixture_v1`，运行容器不再挂载真实 PDF；fixture smoke 仍通过。

## 2026-10-04（比赛真实数据续作）

- 完成国内两来源12页独立PaddleOCR，257框/830字符；新增受控选页、检查点、resume和缓存完整性/主文件保护。
- 拆分共享manifest、严格synthetic与人工真实图区/图题契约；增加确认审计/原PDF哈希/raw-corrected轨迹、完整真值门控导出和只读扫描Compose覆盖文件。
- 真实图像向量按Figure bbox裁剪；缺CFR/无查询主张改为分项不可用，资料缺失不作模型不确定性扣分。
- 142项后端检查（含独立PG API集成）、66源文件类型、Docker三服务重建、全栈smoke和7项Chrome E2E通过。
- 真实导出实际0/6/0图/退出2，无研究指标；业务仍fixture。已清理临时PG容器与临时卷、保留业务服务及数据。本轮未commit/push。
