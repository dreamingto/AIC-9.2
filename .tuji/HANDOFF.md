# 交接

## 2026-10-05 V1.2 最新交接

修复/验收详情见docs/机图索隐_V1.2修复与交付记录.md。正常入口http://localhost/demo与8000/docs；模型8767 ready/cuda。scripts/start.ps1支持fixture/real/neural。新目录先按release/README.md恢复国内包、导入manifest、恢复88冻结向量，再启动neural；不把模型环境混入服务依赖。

默认比较使用domestic-queries-v2/domestic-functions-v2；24开发输入不变，12图草稿覆盖且区域主张限制框内。最终业务运行retrieval_comparison/253b7b50c756cf58/20261005T115134Z-f679af8a，独立恢复运行D:/codex-releases/AIC-9.2/repro-comparison/253b7b50c756cf58/20261005T115326Z-82c7bf63，两者176签名同。V1历史不可覆盖。

材料源码competition/，输出output/competition/。团队信息尚未收到，按匿名预审版交付。技术PDF、答辩PDF、真实操作MP4完成；正式提交需要团队编号/命名/百度网盘和报名系统操作，不自动替用户填写。暂不人工审核决定保持，不把草稿升级Verified，不造研究指标。Git同步与资产链接以随后发布记录为准。

## 2026-10-05 当前交接：固定查询对照与功能草稿

用户授权的两项已完成：backend/data/experiments/domestic-queries-v1.json固定24开发集输入，domestic-functions-v1.json为两个案例4图的20功能/4unknown/10关系方案。全部AI/Inferred/confidence=null，无人工/qrels；关系图不可用。草稿仅由实验工具参与评分，默认线上API未改。

在backend目录运行.venv/Scripts/python.exe -X utf8 -m scripts.run_domestic_comparison；前置真实manifest/神经索引/PG和8767 worker。只读一致事务读取12真实图/50兼容向量，校验manifest/扫描/DB内容/状态/证据/来源/模型空间。8方法中176适用+16不适用，1+2重复共528排名，0失败/不稳定；跨完整运行176签名同。最终retrieval_comparison/5c005b8e95133a58/20261005T094332Z-d18e438e包含报告/锁/证据工作表，输入指纹5c005b8e95133a58701441411f5f2b677609f7a8ee0d48351add412a9c79e725。

水力查询draft将水碓提至首项，整经查询则偏向织机，必须保留案例覆盖4/12与开发集偏差。3首项/4前K顺序变化不是改善率；research metrics仍not_evaluated。235常规passed/3默认PGskip/83源文件检查，9类业务计数保持；本轮未重跑前端/E2E/隔离迁移，未commit/push。复现/解释见docs/机图索隐_固定查询算法对照与功能证据草稿.md。下一步写比赛技术报告/演示稿，背景图草稿补齐与独立评价另建版本。

## 2026-10-05 当前交接：真实检索模型与两个国内案例

已完成BGE中文文本+Chinese-CLIP视觉/图文实际GPU推理，原12真实图+9合成图全部建神经索引；95新向量与74基线共169，来源/原始文字/校订/核验不变。模型位于D:/codex-models/jitu-retrieval，隔离运行环境D:/codex-runtime/jitu-retrieval；服务8767，CUDA/eval/float32/本地文件，依赖及权重锁在backend/model_runtime。

必须先运行backend/model_runtime/start.ps1，再使用docker-compose.yml+docker-compose.ai-real.yml+docker-compose.neural.yml。模型缺失会503；显式基线去掉neural，但继续挂载ai-real。0002已在实际PG升级；不要用旧镜像启动已升级数据库。重建索引脚本不会删除基线，不会修改古籍或审核。

两个固定案例入口http://localhost/demo，实际操作API新增GET /api/v1/demo/cases及POST /api/v1/demo/cases/{case_id}/search。case IDs为gengzhi-loom/tiangong-waterpower；图对仅讲解用途，无硬编码名次/相关性真值。宽泛水力文本首项土礱的现有限制保留。全部研究指标仍not_evaluated，继续暂不人工审核。

209常规/3独立PG/12前端/6实际Chrome及6次HTTP模型搜索通过；新版案例角色文字/顶部截图另做定向Chrome确认。真实核验0/corrected0；三个业务容器healthy，测试容器停止可恢复。未commit/push。报告backend/data/real_pilot/model_retrieval，当前说明docs/机图索隐_真实检索模型与固定案例.md；下一步技术方案、演示稿、国内数据覆盖与正式比较协议。

## 2026-10-05 国内古籍AI比赛版（上一阶段）

用户已决定优先国内出版，比赛暂不人工审核。不要再要求旧人工页确认才能推进。
12图/8页真实数据已导入，国内出版《耕织图》占8图，国图馆藏《天工开物》占4图。
新AI通道独立于人工RealManifest；corrected_text均null，研究指标null，真实候选pending。
当前启动：docker compose -f docker-compose.yml -f docker-compose.ai-real.yml up --build -d。
manifest为ai-real-domestic-8b4defa06141f66e.json；导出与runtime-smoke在本地ignored的
backend/data/real_pilot/ai_domestic_exports/8b4defa06141f66e/。旧PDF/raw/人工草稿不覆盖。
197后端常规pass+独立PG2pass，前端12pass、Chrome E2E5pass、三服务healthy。
Source类区分domestic_publication和domestic_holding；NLC24—26页是谷物加工，不是纺织。
下一阶段真实中文检索Provider、两个国内案例和比赛材料；仍不自动Verified、不造准确率。
详细操作docs/机图索隐_国内古籍AI比赛演示.md；本轮未commit/push。以下为历史交接。

## 2026-10-05 第二轮与证据工作表（当前）

不要重复核心113项AI检查。active_revision指定supplements-v2-c4a07f9b9be9，实际导出
ai-assisted-review-overrides.round2.json（SHA d71b571a...），113/113检查、文字空6、unknown13；
仍AI/Inferred，独立人工0/6。旧候选/扫描/Label/Cache/raw/种子/旧导出/用户草稿保持。

人工/AI页绑定round2，URL加?review_round=2避免旧缓存；AI实际导出作种子恢复，人工seed空。
修复旧onload覆写，Browser验证小框11×7、人工0/543。第10页棍、尾也、小注已拟录，
光后拟簷及宇；磨不/磨木及多处部件仍保留争议，未作为自动功能结论依据。

在backend运行python -m scripts.prepare_competition_evidence_drafts；链接计划
competition_evidence_links.json可版本管理，实际证据在被忽略的evidence-drafts-971fb3e505444829
内JSON和证据工作表。7图/10指定正文框/6功能/2案例/7图题查询，相关性标签null，不是业务manifest。

177 tests passed/1独立PG skipped，69源文件检查通过；正式AI接纳/冻结/导出仍退出2/0图。
三服务healthy，未重建镜像/全栈E2E/commit/push。计划见docs/机图索隐_下一阶段执行计划.md。
后续国内12页独立AI图题/图区和跨书证据，再设计独立AI试点导入，不绕过人工真值门。


## 2026-10-05 补框后最新入口

使用`backend/data/real_pilot/review_revisions/active_revision.json`指定的
`supplements-v2-c4a07f9b9be9`，不要按目录名称推断最新版本。该目录有新candidate/scope、
AI迁移种子、实际AI导出/审计和独立人工/AI页，旧输入和原网页草稿不覆盖。
核心113项=原109+第10页4补框；97 AI已检查/16阅读序号变化待重检，人工仍0/6。
新增b028偏旁和b030双行/正文尾字归属留空；原9留空项/13未知项仍待裁决，非空也须人工复核。

新人工页已绑定实际113条AI导出作建议，采用后不会确认。真实人工导出保存到新目录内
historical-review-overrides.json；使用文档前部的--candidate/--scope/--output等新版本命令
接纳、冻结、导出。默认命令仍针对旧109范围，不能混用。补框无raw、CER/WER只算原保留框。
当前3个质量门实际退出2/0图/metrics=null，没有真实人工annotation或评测快照。

158后端测试通过/独立PG1项skip，68源文件检查通过；Browser验证新增裁剪、迁移建议和
采用建议后人工0确认。三服务healthy，未重建镜像/重跑业务E2E/commit/push。
详细位置、疑点、指标边界与命令见`docs/机图索隐_AI辅助复核交接.md`。

## 2026-10-05 最新接续入口

已用应用内Browser完成核心6页109项AI扫描检查；不要重做这些检查。最终导出为本地被忽略的
`backend/data/real_pilot/ai-assisted-review-overrides.json`，逐项备注和未决项/漏框报告见
`ai-assisted-review-overrides.audit.json`及`docs/机图索隐_AI辅助复核交接.md`。
AI页`http://127.0.0.1:8766/model_review_queue.ai.html`草稿仍显示109已检查；用户原人工页保留。

这些记录都保持AI/Inferred/待人工，不能改名接纳为human。13未知项、9文字留空项待判字；
第10页至少两列正文不在旧scope，需要在新副本拆正文/夹注补框，保存旧candidate/Label/草稿，
建立新候选/范围并显式对照迁移建议。非空建议也要独立人工逐项确认；不能仅确认9个留空项。
核心仍0/6人工就绪，freeze实际退出2，所有研究指标not_evaluated，真实导入仍未解锁。

CLI拒绝AI文件的未捕获异常已修为共享ConversionError，2个隔离真实`-m`回归通过；最终
149 passed/1 skipped/2既有warning，compileall/Ruff/Mypy（67源文件）通过。PG独立测试本轮skip。
今天已恢复现有3容器和loopback复核服务器，三服务healthy、4入口200、业务SQL计数3/9/18；
未重建镜像或重跑前端/业务E2E，未commit/push。电脑重启后需重新启动服务。

## 2026-10-04 最新接续入口

已完成国内两来源12页补充OCR，结果为257框/830字符（含换行），全部未复核。不要重写原28页raw、Cache、Label、候选和网页草稿；补充Runner使用独立inventory/output/selection与resume，范围或模型变化需新输出。

真实导入工具已完成，但当前仍无historical-review-overrides.json与annotations.human-reviewed.json，核心0/6就绪，实际export_reviewed_real_manifest退出2/0图。下一步在model_review_queue.html默认核心6页全部候选中确认109项、阅读顺序和完整文字/图题清单，再保存真实导出并运行接纳器。导出器将重验完整scope/人工产物/快照，另检查图区和标题，随后生成仅含图/图题的reviewed-real-core-v1.json和reviewed_real_v1扫描目录，不自动绑定正文/功能/关系。

完成导出后才启用docker-compose.reviewed-real.yml只读挂载，使用已有ingestion API并查看job终态。命令见docs/机图索隐_AIC比赛版数据与评测推进.md的2026-10-04章节。默认3服务当前healthy，入口http://localhost；业务库还是synthetic，测试模拟数据没有混入。

最新验收142后端测试（含独立PG）、66源文件类型检查、Docker重建、全栈smoke和7项Chrome E2E通过；测试容器/临时卷已清理。本轮未commit/push。真实OCR/检索研究指标继续not_evaluated。

## 2026-10-03 最新接续入口

用户授权按比赛推荐推进，优先中国古籍。已新增国图《天工开物》45页、国内出版来源《耕织图》27页、Harvard《御制耕织图》28页；5个PDF/207页/3部中国古籍，新增100页为独立supplementary库存，原28页哈希未变。勿重复整批OCR或去除新国图原图水印。

核心原第10/12/14/16/18/22页为101框、7图区、1补框图题，共109项。`prepare_competition_scope`生成范围，`build_historical_review_queue --scope data/real_pilot/competition_scope.json`生成原复核页；默认核心全部候选，旧草稿键保持。逐项确认、顺序和完整文字/图题清单分别设门，改动撤销完整性。

将真实导出保存为 `data/real_pilot/historical-review-overrides.json`，逐项override转换后运行 `python -m scripts.evaluate_competition_ocr --freeze`。缺真值退出2且metrics=null；完整范围才建立内容寻址快照。不得用旧Label审计器或直接编辑corrected绕过原人工导出。

当前0/6页就绪，保留框CER/混合CJK字符-Latin词WER/图题定位Recall未评测；分类Precision/F1、整页端到端CER和检索相关性指标未定义或未评测。业务数据库仍fixture，待真实确认后再做PG导入及同书/跨书案例。

入口：`docs/机图索隐_AIC比赛版数据与评测推进.md`。最新123项后端测试、65源文件检查、4项Chrome复核页E2E；本轮未重跑Docker/PG/业务集成、未commit/push。以下交接保留为历史记录。

项目已集成 React 前端、FastAPI 后端与 PostgreSQL/pgvector。运行 `docker compose up --build` 可构建并启动前端 `http://localhost`、后端 `http://localhost:8000` 和数据库；项目通过 AWS Public ECR 的 Docker 官方镜像缓存避开失效的全局 USTC 镜像源，并使用 PGDG 固定版本 pgvector 包。

2026-09-04 已完成最新三服务镜像构建和重建，`db`、`backend`、`frontend` 均为 healthy。`python backend/scripts/smoke_fullstack.py` 与 `cd frontend; npm run test:e2e` 已在最新容器上通过，覆盖真实 Nginx 代理、PostgreSQL、fixture 幂等导入、三类检索、资源许可和候选核验。

2026-09-04 当时检查结果：后端 47 项测试、前端 11 项测试、Playwright 3 项 E2E 全部通过，前后端 lint/type/build/OpenAPI/Compose 配置和全栈 smoke 通过。V1.1-B 当时完成真实古籍许可元数据与首批页面准备；最新 OCR/人工复核状态见本文最后一节，不要将历史验收当作本轮重跑结果。

没有真实数据和真实模型时，报告中使用 `not_evaluated`，不得把 fixture 排名或分数写成研究结论。

## V1.1-B 交接状态（2026-09-04）

真实数据准备已经开始：运行 `python backend/scripts/download_real_pilot.py` 可验证两份来源 PDF，运行 `python backend/scripts/prepare_real_pilot.py` 可重建首批《天工开物》28 页页面库存。查看 `backend/data/real_pilot/sources.json`、`derived_pages.json` 和 `annotation_schema.json` 了解来源、页面哈希与标注字段。

当前页面库存只证明来源文件和渲染链路可复现；OCR、版面/图题/功能标注、Page/Figure 数据库导入和真实检索评测尚未完成。不要把待处理页面当作已有搜索结果，也不要将 Commons 的作品公版元数据直接扩展为所有用途的法律许可。

安装并固定 OCR Provider 后运行 `python backend/scripts/run_real_pilot_ocr.py`。当前环境没有 PaddleOCR，命令会明确返回 `MODEL_UNAVAILABLE`；这一步不能用 fixture 文本替代。

后端镜像构建已验证：`backend/.dockerignore` 排除 `real_pilot_v1` 原始 PDF 与渲染 PNG，构建上下文约 16 KB；重建后 `/api/v1/health` 200 且容器 healthy。

Compose backend 目前仅只读挂载 `manifests` 与 `fixture_v1`，运行容器中不存在 `real_pilot_v1` 原始 PDF；真实页面准备和 OCR 脚本应在宿主机受控目录执行。

## PPOCRLabel 转换交接（2026-09-29）

运行 `cd backend; .\.venv\Scripts\python.exe scripts\convert_ppocrlabel_annotations.py` 可从登记来源目录生成被忽略的 `annotations.ppocrlabel-draft.json`。当前草稿为 28 页、732 框，全部 `unreviewed/not_evaluated`。

人工保存后的最新状态：28 页均有 fileState，人工 Label 保留 525/732 个框；版面审核快照已冻结为 `commons-najda-tiangong-kaiwu-2-layout-2e7bf4a41b9e`。转换器将 `--accept-file-state` 解释为只接纳版面/框选，不会自动建立 corrected 层。

下一位执行者不要重复版面初筛。先在第 8 页删除 `国立公文書館 / National Archives of Japan` 水印框，再逐字校订 525 个保留框并复核阅读顺序；最后用 `--accept-transcription-review` 过第二道门。图题召回率还需要在项目 annotation 工具中补充 caption/figure 类别，不能从 PPOCRLabel 的纯 OCR 框推断。

## 2026-10-02 最新接续入口

上一节为历史状态：水印现已清理，现有 523 框。不要重复删除或重跑整批 OCR；server 523 框指纹缓存和 Wikisource 36 节参考均已落盘。使用 `generate_historical_review_candidates.py` 更新候选时会改变候选文件哈希，需同步重新生成审核页并使用匹配的导出文件。

直接打开 `backend/data/real_pilot/model_review_queue.html`。默认优先队列 280 项，切换“全部候选”可访问全部 539 项；259 个延后项也仍待人工确认。页面可填写文字、类别/角色/坐标/顺序，查看整页叠加层并确认本页顺序，最终导出 `historical-review-overrides.json`。

接纳人工导出时，在 backend 下运行 `python -m scripts.convert_ppocrlabel_annotations --accept-file-state --reviewer <id> --review-overrides <导出文件实际路径>`。输出为 `annotations.human-reviewed.json`；禁止同时使用 blanket `--accept-transcription-review`。接纳器验证哈希、身份/日期、明确确认、几何及顺序；部分审核不升级整页转录，图题和图区确认相互独立。

当前真实 Verified 仍为 0，研究评测不可开始。下一步是接纳真实人工导出，检查剩余未确认/缺框项，再建立包含 raw/corrected、图题、阅读顺序及输入哈希的正式冻结器和评测器；旧 Label 审计器不读取网页导出的 corrected 层，不应直接用于这一路线的正式指标。

106 项后端测试、静态/类型/编译检查与 3 项本地审核页面 Chrome E2E 已通过。PDF/PNG、候选、裁剪、缓存、审核导出和 QA 截图均被 Git 忽略；Docker 构建上下文亦排除复核数据。
