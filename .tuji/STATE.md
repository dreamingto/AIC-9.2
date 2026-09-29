# 当前状态

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
- 三份文档均区分已实现能力与后续规划，并明确 fixture 为 `not_evaluated`；真实扫描已完成来源登记和首批页面准备，OCR、真实模型和 ANN 尚未接入。

## 验证结果

- Python 回归：47 passed，2 个上游弃用警告；容器运行时为 Python 3.12.14。
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

- 真实古籍数据、OCR、真实模型和研究指标尚未接入。
- EAFR 当前使用代码级注入权重和固定模态可靠性（可用 1、不可用 0）；环境配置、来源质量驱动的动态缩放与效果验证尚未完成。
- 现有 3 项 Playwright E2E 聚焦核心闭环，错误码矩阵、移动端视口、可访问性扫描和视觉回归仍未覆盖。
- OpenAPI 与 TypeScript/Zod 仍为人工同步，尚未建立自动代码生成或契约漂移 CI。

## V1.1-B 真实数据试点（当前增量）

- 已从 Wikimedia Commons / National Archives of Japan 登记并下载《天工开物》第二册（28 页）和《农政全书》第一册（79 页）。来源 URL、Commons SHA-1、本地 SHA-256、字节数、页数和许可字段已写入 `backend/data/real_pilot/sources.json`。
- 已运行 `backend/scripts/prepare_real_pilot.py`，完成首批 28 页 PNG 渲染并生成 `backend/data/real_pilot/derived_pages.json`；页面 `layout.status=pending_review`，OCR `status=pending_provider`。
- 新增 `backend/data/real_pilot/annotation_schema.json` 和可选 `PaddleOCRProvider` 契约。未安装 OCR runtime 时显式返回 `MODEL_UNAVAILABLE`。
- 原始 PDF/渲染 PNG 未纳入 Git；真实数据尚未导入 Page/Figure/TextChunk，也未开始真实 OCR 或效果评测。
