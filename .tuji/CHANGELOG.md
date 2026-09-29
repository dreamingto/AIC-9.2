# 变更记录

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
