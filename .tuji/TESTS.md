# 测试记录

## 2026-10-05 V1.2 修复验收（最新）

- 后端252 passed/3默认PGskip/2上游弃用提醒；88源文件Mypy，compileall/Ruff/pip check通过。3 opt-in PG另在55432/tuji_reviewed_real_test实际3 passed。独立测试卷与实际数据恢复卷分开保留。
- 无.env新源码目录实际Compose构建/healthy，自动0001+0002；冻结包24文件哈希恢复后，真实manifest导入12图/14区域/35文本/59证据；88向量导入及重复导入数量稳定。
- 新恢复环境Chrome10 passed（三模态、合成核验、真实资源与神经案例、历史标注）。默认业务库不新增真实核验。服务重启持久化与最终发布核对记录见后续条目。
- V2两次全运行（业务库/恢复库）各528排名/0失败/0不稳定；全部176签名、语料与输入指纹253b7b50c756cf58一致。对照只读，非相关性准确率。
- 前端13测试/3文件、lint/构建通过；npm audit发现新Undici高危，升级锁至7.30.0后0漏洞，未force主版本。最终不确定度展示修复后JS364.75kB/gzip110.51kB，再跑Chrome10通过。
- OpenAPI17操作导出与前端Zod字段比对通过；线上CI37307763298成功，Linux/PG255后端与13前端测试、迁移/Ruff/Mypy/编译/审计/构建/契约漂移均通过。首次runner对探活单引号解析失败，改双引号后通过。
- PDF各8页渲染复核，技术PDF1,979,933字节，演示MP4实际探测4:40.96/1280x720/H264+AAC/8,171,940字节。实际浏览器两case真实API操作，重录反映最终UI。材料包12,609,618字节；公开release7资产服务器摘要与本地锁全同。
- 独立后端实际restart，2条synthetic核验数量保持且health恢复200；原业务核验14保持。公开源码包无凭据全量下载705,060字节，SHA256一致。48MB数据包回读60秒仅2,866,494字节而超时，标记partial不用于恢复；公开链路确实返回归档，服务器全包摘要与本地一致，但本轮不声称该大包全量网络回读通过。

## 2026-10-05 完整性审查重新验证

- compileall app/tests/scripts/model_runtime、Ruff同目录、Mypy app/scripts83源文件、pip check通过；pytest235 passed/3未配置独立PG而skip/2既有上游弃用提醒。前端lint exit0、Vitest12/2文件通过、tsc/Vite构建通过（主JS364.46kB/gzip110.41kB）。
- 三业务容器healthy；首页/demo/health/docs200，17操作OpenAPI、8767 ready/cuda及6Provider可用；两个case ready、4图扫描200、3旧搜索/候选重读成功、受限fixture资源403/LICENSE_RESTRICTED。业务SQL仍21图/32区域/169向量/88会话/739候选/14fixture核验，真实35文本Inferred且corrected/功能/关系/核验0。
- 当前三Compose配置通过；git fsck exit0、diff --check通过。公开GitHub API实查main e09b6ca与本地相同，tree143文件/未截断；Git协议访问因本机失效代理/直连reset失败，没有更改代理配置。
- 在系统临时目录将HEAD archive成隔离目录，直接docker compose config真实失败：env file .env not found。此为首次启动文档缺口，未通过复制私密.env掩盖。
- 本轮未重跑独立空PG迁移/集成、Chrome全栈、镜像构建、断网或528对照；历史记录保持。本轮审查不在业务库新建搜索、导入或核验，不以GET健康替代上述验收。

## 2026-10-05 固定查询对照与功能草稿

- 新26回归：协议三模态/176适用与null标签、无伪造视觉文字/来源自排除、非法bbox、假Verified/置信度拒绝、逐图扫描与文字引用绑定/误图/假引文/来源类型漂移、范围内功能/跨范围拒绝、证据长度无奖励、BGE/CLIP空间隔离/稳定排序、模型失败无回退、manifest预检、输出不可覆盖、研究指标null、数据库文字/状态/证据/来源/PDF/向量漂移与缺图拒绝。
- 最终compileall app/scripts/tests通过，Ruff app/scripts/tests通过，Mypy app/scripts83源文件通过，全量235 passed/3既有opt-in PG默认skipped/2既有上游warning。
- 真实PG使用READ ONLY/REPEATABLE READ并实际SHOW确认；锁12真实图/50神经向量，528次排名计算，无失败/重复不稳定；跨两次完整运行176排序/分数/分项签名相同。研究指标not_evaluated。
- 执行前后9类业务计数逐项相同：21图/53文本/54原fixture功能/9原fixture关系/86证据/169向量/88会话/739候选/14原fixture核验；新草稿未写业务标签。三服务healthy。
- 本轮未重跑前端/浏览器/独立PG迁移导入，未改API/迁移，未commit/push。报告目录被Git与Docker忽略。

## 2026-10-05 真实神经模型与国内固定案例

- compileall覆盖app/scripts/tests/model_runtime；Ruff app/scripts/tests与Mypy77源文件通过。209常规pass/3 PG默认skip/2既有上游弃用提醒；新增模型身份/维度/NaN/范数/错误版本/预处理/故障无回退/跨模态空间/兼容索引缺失/ID隔离等回归。
- 实际空PG先暴露初始迁移unique索引冲突；0002扩展完整模型空间后，最终新空容器执行0001+0002迁移并3集成pass。覆盖实际256/512维写读并存/稳定ID/模型筛选、原人审与AI合同检索/许可/重开连接。临时容器停止可恢复，业务PG不受测试污染。
- 独立模型环境pip check通过，Torch2.7.1+cu128/Transformers4.51.3；权重revision/LFS SHA256及配置gitblob hash下载校验，worker启动逐文件校验并实际CUDA推理。
- 两次实际索引21图/32区域/95神经向量，SQL169=74旧基线+95新模型，重复不增条数；真实文本仍35Inferred/corrected0/真实核验0。
- 前端lint/Vitest12/tsc+Vite与真实Docker构建通过；实际Chrome core+domestic+neural6pass，新版角色文字和截图又定向neural1pass。图片成功加载/区域坐标/实际模型身份/文本、上传、区域/候选数据均走真实服务。
- HTTP两个案例的6次模型搜索、所有会话完整重读通过。本次耗时约78—539ms含缓存，仅工程观察；记录neural-smoke.json。独立CER/WER/图题Recall/检索Recall/nDCG仍not_evaluated。
- 最终服务重启后6个神经搜索会话的图ID/顺序/分数逐项保持，上一阶段baseline报告中的旧会话也保持；模型8767仍ready/cuda，三个业务容器healthy。git diff --check通过，运行报告被正确忽略，最后截图已视觉检查。

## 2026-10-05 国内古籍导入与实测

- 最终重新创建空的独立PG测试容器，对当前代码迁移+两项集成仍2 passed，测试容器已停止可恢复；业务容器保持运行。后端重启后会话12/12/11保持、Nginx健康200；SQL真实核验0、Inferred文本35/corrected0。

- 新20项AI合同/导出回归：原PDF/PNG/库存/OCR输入漂移、来源许可与路径、出版来源多数、原raw分图隔离、AI/人工状态、假Verified、corrected拒绝、不可覆盖、裁剪向量输入、多区域重读次序。
- 全量197 passed/2 opt-in PG默认skipped/2既有上游warning；compileall/Ruff app scripts tests/Mypy app scripts71源文件通过。
- 新建独立127.0.0.1:55432的tuji_reviewed_real_test，空库Alembic迁移通过；两项opt-in PG集成2 passed，涵盖人审格式与AI格式隔离、幂等、向量、raw/null corrected、三模态、重开连接和许可。
- 前端lint/Vitest12 passed/生产构建通过，实际Chrome E2E core-flow+domestic-ai-flow5 passed；真实AI数据未提交核验，合成核验仅工程测试。
- Docker真实构建与overlay挂载，三服务healthy。HTTP smoke两次导入+12/12/11三类候选+会话/候选重读+确定性排序通过；独立SQL计数21图=9synthetic+12AI。
- 实测发现并修复：多区域的重读次序漂移，Nginx默认1MB导致扫描上传413，step=0.01拒绝0.055等合法归一化坐标。
- 研究CER/WER/标题召回/检索准确率仍not_evaluated，不能用上述工程测试结果替代。

## 2026-10-05 第二轮AI复核与证据生成

- 新增18项生成器回归：完整清单和AI检查、哈希/来源/Verified拒绝、NaN/原raw/日期/读序拒绝、真实引用绑定、跨页误图题/未知案例/路径穿越拒绝、PDF变更、输出不覆盖、幂等及原输入保持；新增1项实际AI导出恢复且不升级人工/不改candidate。
- compileall、Ruff通过，Mypy app scripts为69源文件；全量177 passed/1独立PG skipped（未配置TUJI_TEST_DATABASE_URL）/2既有上游warning。
- 实际生成7图/6功能/2案例/7无标签查询，重复运行复用evidence-drafts-971fb3e505444829。round2实际导出113检查/6文字空/13unknown。candidate仍c4a07...、原AI导出仍08ca9...；产物git check-ignore通过。
- Browser发现旧裁剪回调显示相邻正文列，修复后新模板快速切换三轮，b023预览11×7且ID正确；刷新人工页0/543、单项/读序/完整性未确认。URL加review_round=2规避旧HTML缓存。
- 实际round2 AI接纳退出2且无人工输出；freeze0/6、metrics=null/blocked_pending_human_truth/退出2；export0图/退出2。这是质量门按设计拒绝，不能记为研究评测通过。
- Docker三服务healthy，未重建镜像、未运行独立PG/前端全套/业务E2E；Browser验证仅针对复核页。


## 2026-10-05 补框版本与建议迁移

- 新增9项回归：旧raw/文件字节保持、幂等版本、人工页不预填确认、hash/AI来源/NaN/重复框/不存在锚点拒绝、补框必入完整性门、补框不造raw及不混入保留框CER/WER、保持旧AI顺序而不回退机器顺序、绑定AI建议不升级人工。
- 全量pytest158 passed/1独立PG skipped/2既有上游warning；compileall/Ruff/Mypy68源文件通过。真实导出CLI增加版本路径后相关42项回归通过，实际新版导出返回blocked_pending_human_truth/0图/退出2。
- 新版本prepare_revision实际迁移109建议/补4框，核心6页113项，全队列543项；16序号变更撤销AI检查，原页顺序/完整性确认均不继承。实际AI UI导出113项，97已检查/16待顺序重检，11文字空值；全为ai_assisted/inferred/待人工。
- Browser核对新4框、更新小字左边界、保存2正文建议及2小注留空。新人工页0/543确认，采用AI建议后confirmed/page-confirmed/inventory-confirmed仍false，扫描图正常。
- 实际AI接纳、freeze和export三门均退出2；0/6、metrics=null、0图，没有实际人工annotation或真实快照。candidate/inventory/Label原hash保持，旧AI导出和人工HTML未覆盖。
- review_revisions文件被Git/Docker排除。三服务healthy；本轮未重建镜像或重跑前端、PG集成及业务E2E，测试模拟冻结不算真实评测。

## 2026-10-05 AI 复核来源门与模块CLI

- 2026-10-04完成109项AI辅助扫描检查，109条保存记录来源均ai_assisted、状态inferred、证据scan_level_ai_review、requires_human_confirmation=true；page_reviews/page_inventory_reviews均0。candidate/inventory/Label原哈希保持，AI页/JSON/审计git check-ignore通过。
- 接纳器新增文件级/记录级AI与pending-human拒绝，队列支持独立AI文件/草稿；AI结果不能进入人工真值。
- 共享ConversionError修复`-m`入口的重复导入异常类；新增2个subprocess测试使用隔离项目真实模块入口，验证退出2、无traceback、不新建输出及已有输出字节保持。该接纳器测试文件17项通过。
- 最终compileall/Ruff通过，Mypy app scripts检查67源文件；全量pytest149 passed/1 skipped/2既有上游弃用警告。独立PG测试没有TUJI_TEST_DATABASE_URL而skip，不宣称本轮PG集成通过。
- 实际AI文件接纳退出2且无traceback，人工annotations/overrides仍不存在。实际evaluate_competition_ocr --freeze退出2，0/6就绪、metrics=null、blocked_pending_human_truth/not_evaluated。
- Docker现有三服务start后均healthy，前端/后端health/原人工复核页/AI复核页HTTP200；只读SQL核对books/figures/regions为3/9/18。今天静态服务重新启动，仅绑定127.0.0.1:8766。
- 应用内Browser恢复原AI草稿109/539，检查备注和原扫描裁剪可见，用户原人工页未改动。未重建镜像、未重跑前端测试或业务E2E；后端纯测试与服务启动探活分别记录。

## 2026-10-04 补充OCR、真实导出和PostgreSQL

- 独立锁定PaddleOCR实际运行12页：257框、830字符（含换行），原28页inventory哈希仍c5cd13fe5a68de742d05b7effb0698bbb6a13f405493b768df48518797a255c1。Raw保持unreviewed，corrected=0。
- 新增7项Runner测试、10项导出/契约测试、1项缺CFR/无查询证据分项不可用测试、1项显式独立PG API集成。
- Runner覆盖部分失败检查点/续跑、不重复识别、未知ID、扫描hash、模型/范围变化、结果损坏、人工修订及主文件保护。导出覆盖无真值门、原始人工导出重校验/冻结/导出/loader完整链、幂等、图区/标题独立确认、审计/许可/状态拒绝、资源不覆盖和bbox裁剪。
- PG测试端口限定55432/测试库名，未配置TUJI_TEST_DATABASE_URL则skip；空库Alembic成功，隔离模拟输入导入2次、2图/6向量/256维、raw/corrected、3类搜索/会话、候选核验、断连后读取、允许/受限资源和Evidence不升级均通过。
- 最终compileall、Ruff与Mypy app scripts通过，66源文件；包含独立PG的pytest为142 passed/2既有上游警告。独立测试容器及临时卷已清理，业务卷保留。
- Docker默认及reviewed-real附加配置校验通过；默认三服务up --build -d通过并全部healthy，生产前端构建通过，Nginx全栈smoke通过；Chrome E2E共7 passed（业务3/审核4）。附加真实扫描挂载未启用。
- 真实导出器运行：0/6页就绪、0图、blocked_pending_human_truth，CLI退出2；实际人工导出/转录真值仍不存在，没有真实快照、正式OCR或检索指标。

## 2026-10-03 核心范围评测与中国古籍补充

- 5个登记PDF验证通过，字节数/SHA-1/SHA-256/PDF页数匹配；3个新增来源独立渲染100页，原28页inventory哈希不变。
- compileall、Ruff、Mypy通过（65个应用/脚本源文件）；Pytest 123 passed，2个既有上游弃用警告。
- 新增17项评测/冻结用例：缺真值、固定范围部分确认、raw/corrected分离、server预测、Cache/Label/PNG/PDF变更、原人工导出与产物一致性、完整图题清单、漏检分母、一对一匹配、micro CER/混合token WER、内容寻址复用与文件/manifest篡改。
- 实际 `evaluate_competition_ocr --freeze`：0/6页就绪、metrics=null、not_evaluated、blocked_pending_human_truth；预期质量门阻塞，不创建真实评测快照。
- 真实Chrome本地审核E2E 4 passed：核心范围、全页完整性门、导出与撤销、草稿保持、桌面/移动端和坐标边界。首次check对主动取消勾选的门导致测试适配失败，改用click后重跑；历史场景显式切回全部范围。
- 测试虚构人工记录没有导入真实数据。本轮未重跑Docker/PG/业务全栈集成，亦未将旧全栈验收当成本轮结果。
- 前端 `npm run lint` 单独复核退出码0；最终格式修正后的Ruff通过，实际评测Python退出码单独核实为2。最后模板更新后4项Chrome E2E再次通过，截图已查看。

## Python

- 编译：`python -m compileall -q app tests scripts` 通过。
- 静态检查：`ruff check .` 通过。
- 类型检查：`mypy app scripts/smoke_fullstack.py` 通过（46 个应用源文件和 1 个 smoke runner）。
- 单元/API 契约测试：39 passed，2 个 TestClient 上游弃用警告。
- 依赖检查：`python -m pip check` 通过。
- OpenAPI：15 个 GET/POST 操作，Swagger 返回 200。
- 本轮宿主机回归运行于 Python 3.14.3；Docker 集成运行时为 Python 3.12.14，目标版本仍为 Python 3.12。

## Docker 与 PostgreSQL

- Compose 配置、数据库镜像、后端锁定依赖镜像和服务启动均通过。
- PostgreSQL 16、pgvector 0.8.6、Alembic `0001_initial` 已真实运行。
- 15 张领域表加 1 张 Alembic 版本表已持久化。
- image 27 条与 text 9 条向量均可由 pgvector 读取，维度均为 256。
- fixture 首次及重复导入完成，统计保持 3/9/18/54/27/12。
- 文本、图片、区域三类检索均返回数据库候选，所有总分为有限数。
- 允许资源返回 PNG/200；受限资源返回统一 `LICENSE_RESTRICTED`/403。
- `worth_comparing` 核验在后端重启和镜像重建后仍存在。

2026-09-04 重新执行 `docker compose --progress plain build` 和三服务重建；`db`、`backend`、`frontend` 全部为 healthy。

- `python backend/scripts/smoke_fullstack.py`：通过。
- smoke 结果：3 books、5 providers、文本/图片各 9 条结果、区域 8 条结果。
- smoke 许可结果：允许资源 200、受限资源 `LICENSE_RESTRICTED`/403。
- smoke 明确输出 `evaluation_status: not_evaluated`。

## 前端与本轮全栈审查

- `npm ci`：190 packages，0 vulnerabilities。
- `npm run lint`：通过，0 warnings / 0 errors。
- `npm run test -- --run`：2 个测试文件，11/11 通过。
- `npm run build`：通过，TypeScript 检查与 Vite 生产构建成功。
- `docker compose config --quiet`：通过。
- `npm run test:e2e`：Playwright 3/3 通过，使用本机 Chrome 和真实三服务链路。
- 敏感信息模式扫描：未发现 API Key、令牌或私钥；`.env`、依赖、构建产物和缓存目录均处于忽略状态。
- Markdown 本地链接检查：未发现断链。
- 最新前端镜像生产构建通过；首次 Linux npm 依赖下载约 67 秒，后续使用 BuildKit npm cache。

## V1.1-B 真实数据准备验证（2026-09-04）

- `python backend/scripts/download_real_pilot.py`：两份本地 PDF 均 `existing_verified`；字节数、PDF 魔数、Commons SHA-1、本地 SHA-256 校验通过。
- `python backend/scripts/prepare_real_pilot.py --dpi 150`：通过；首批 1 个来源、28 页渲染完成，库存 `evaluation_status=not_evaluated`。
- `pdfinfo`：首批 PDF 未加密、28 页、PDF 1.5；抽样渲染 PNG 已成功生成。由于当前 Windows 视觉助手无法读取该目录图片，未完成助手内嵌视觉复核；后续应在本地浏览器或图像查看器抽检页面清晰度。
- `compileall`、Ruff、Mypy、Pytest：后端 47 项通过；新增 OCR/页面准备测试包含哈希、路径越界、待处理状态和 Provider 不可用语义。
- 未执行真实 OCR、Page/Figure 数据库导入和真实效果评测，不能将本轮产物写成算法指标。

- `python scripts/run_real_pilot_ocr.py --limit 1`：按预期失败并输出 OCR runtime 未安装；该失败是能力边界检查，不是静默降级。

## 2026-09-29 OCR 运行时验收

- 独立环境版本：Python 3.12.14、`paddlepaddle==3.0.0`、`paddleocr==3.0.3`、`paddlex==3.0.3`；`pip check` 通过。
- PP-OCRv5 mobile detection/recognition 模型通过 `127.0.0.1:7890` 下载并缓存成功。
- `python backend/scripts/run_real_pilot_ocr.py --limit 1`：退出码 0，生成 1 页、39 条有效 raw OCR 行、192 个字符；输出 Provider 为 `paddleocr / PP-OCRv5_mobile / 3.0.3`。
- OCR 输出检查：`corrected_text` 为 null、`review_state=unreviewed`、`evaluation_status=not_evaluated`；没有覆盖人工校订字段。
- 运行时锁文件：`backend/requirements-ocr.lock`；未修改 `backend/requirements.lock`，未将 OCR 大依赖加入 Docker 镜像。

- `docker compose build backend`：通过；构建上下文由约 111 MB 降至约 16 KB，确认真实 PDF 与渲染 PNG 未进入镜像。重建并重启后端后 `/api/v1/health` 返回 200，容器 healthy。

- V1.1-B 镜像重建后再次运行 `backend/scripts/smoke_fullstack.py`：通过；3 books、文本/图片/区域检索、幂等导入、核验持久化和 allowed/restricted 许可检查均正常，Provider 5 个，结果 `not_evaluated`。

- Compose 收窄 backend 数据卷后重启验证：容器内 `/app/data/assets/real_pilot_v1` 不存在，仅挂载 fixture PNG 和 manifest；全栈 smoke 再次通过。

## 2026-09-29 PPOCRLabel 转换验收

- `python -m compileall -q app tests scripts`：通过。
- `ruff check .`：通过。
- `mypy app scripts`：通过，检查 55 个源文件。
- 初版转换器验收时 `pytest -q` 为 69 passed，2 个 FastAPI/Starlette 上游弃用警告。
- 转换器测试覆盖合法 Cache、raw/corrected 隔离、fileState 门控、四点顺序、归一化 bbox、NaN/Infinity、越界点、非法 JSON、未知/穿越路径、重复页面、原子写入与幂等。
- 人工修改前的初始转换为 28/28 页、732 框、0 跳过；25 条工具 fileState 未升级审核，`evaluation_status=not_evaluated`。
- 草稿连续两次生成的 SHA-256 均为 `AD18FA51E17C98F835D9B5B693B3B6CEB5B1542B2B85923705A9C5238EE462E0`，确认无时间戳漂移；输出被 `.gitignore` 排除。

## 2026-09-29 人工版面快照与质量门

- 保存后输入：28 Cache 页、28 fileState、27 非空 Label 页加 1 个确认空页；732 个 raw 框、525 个人工保留框、净删除 207 个。
- 新增 layout/transcription 双门测试、Unicode replacement character 拒绝测试、CER/WER 编辑距离测试、质量审计阻塞测试和快照幂等/完整性测试。
- `freeze_ppocrlabel_snapshot.py` 连续执行两次返回相同 snapshot id 和文件哈希，内容寻址快照验证通过。
- `python -m compileall -q app tests scripts`：通过。
- `ruff check .`：通过。
- `mypy app scripts`：通过，检查 57 个源文件。
- `pytest -q`：77 passed，2 个 FastAPI/Starlette 上游弃用警告。
- 当前审计门：layout snapshot ready；transcription/evaluation-set freeze blocked。CER、混合 CJK WER、图题召回率保持 null/not_evaluated。

## 2026-10-02 模型辅助复核与人工接纳

- 受控水印清理、36 节参考下载、章节标题/正文锚点、独立对齐、首列中段匹配、缓存重用与保守共识测试通过。
- 审核队列覆盖聚焦/延后条目、补框图题、扫描裁剪、路径边界和现有资产保留；候选仍为 Inferred。
- human overrides 测试覆盖 raw/corrected 分层、完整/部分页、阅读顺序、独立图题区域、幂等输出、Label 改变后的陈旧数据拒绝，以及模型状态/哈希/未知/重复/NaN/顺序/日期错误时原输出保持不变。
- `python -m compileall -q app tests scripts`、`ruff check .`、`mypy app scripts` 通过（62 个源文件）；`pytest -q` 为 106 passed，2 个既有 FastAPI/Starlette 上游警告。
- 最后两项导入测试与格式化完成后重新执行上述全部检查，结果仍为 106 passed；`npm run lint` 本轮退出码 0。没有以先前运行结果代替最后改动的回归。
- `node node_modules/@playwright/test/cli.js test e2e/historical-review.spec.ts`：3/3 通过，使用真实 Chrome 和直接文件页；验证桌面 crop/完整扫描/顺序叠加、延后项、补框图题实际下载 JSON、确认撤销、手机 390px、越界坐标和草稿导航。
- 桌面与手机截图已人工查看，图片非空、文字无重叠、无横向溢出；隔离测试导出未导入真实数据，也未计入 Verified。
- 本轮没有重跑 Docker/业务数据库/全栈检索 E2E；新增检查针对宿主机 OCR 复核链。原有 V1.1-A 验收仍按历史记录，不把本地页面测试称为 PostgreSQL 集成验收。
