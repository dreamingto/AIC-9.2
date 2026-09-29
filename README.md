# 机图索隐全栈 V1.1-B

这是“机图索隐”智能文化赛道项目的全栈工程基线。V1.1-A 面向本地或受控演示环境，在 V1 业务闭环上补齐运行时契约、全栈 smoke 与浏览器 E2E：

`受控 manifest 导入 -> PostgreSQL/pgvector 持久化 -> 文本/图片/区域检索 -> EAFR 重排 -> React 证据展示与比较 -> 人工核验持久化`

fixture 是合成数据，只用于验证接口、数据链路和可复现性。它的 `evaluation_status` 为 `not_evaluated`，不能作为真实古籍实验指标或历史传承结论。

## 项目文档

- [项目策划书](docs/机图索隐_项目策划书.md)
- [项目需求文档](docs/机图索隐_项目需求文档.md)
- [项目技术文档](docs/机图索隐_项目技术文档.md)

## 快速启动

前置条件：Docker Desktop 正在运行。

```powershell
docker compose up --build
```

Compose 默认从 AWS Public ECR 的 Docker 官方镜像缓存获取 Python 3.12、
PostgreSQL 16、Node 22 和 Nginx，并从 PostgreSQL 官方 PGDG 仓库安装固定版本的 pgvector 0.8.6。
这可避开本机失效的 Docker Hub 镜像加速器；基础镜像地址和 pgvector 包版本均可通过
`.env` 中的 `PYTHON_BASE_IMAGE`、`POSTGRES_BASE_IMAGE`、
`PGVECTOR_PACKAGE_VERSION` 覆盖。后端容器运行依赖固定在
`backend/requirements.lock`。

服务地址：

- 前端：<http://localhost>
- API：<http://localhost:8000>
- Swagger：<http://localhost:8000/docs>
- OpenAPI JSON：<http://localhost:8000/openapi.json>

Compose 启动时会先执行 `alembic upgrade head`，然后启动 Uvicorn；后端健康后再启动 Nginx 前端。Nginx 为 React Router 提供 SPA 回退，并将 `/api/` 代理到后端。数据库不可用时 `/api/v1/health` 返回统一的 `DATABASE_UNAVAILABLE` 错误，不会切换到 SQLite。 Compose backend 仅只读挂载 fixture 与 manifest；真实 PDF/渲染图留在宿主机受控目录。

## 导入 fixture

启动服务后调用：

```powershell
$body = '{"manifest_name":"jitu-fixture-v1.json","dry_run":false}'
Invoke-RestMethod -Method Post -Uri http://localhost:8000/api/v1/ingestion/jobs `
  -ContentType 'application/json' -Body $body
```

返回的 job ID 可用以下接口轮询：

```text
GET /api/v1/ingestion/jobs/{job_id}
```

导入器只接受 `backend/data/manifests` 下的文件名，校验 manifest schema、资源路径、PNG 魔数、尺寸、哈希和许可字段。重复导入同一 manifest 使用稳定 UUID 并更新向量，不会产生重复实体。

## API 概览

```text
GET  /api/v1/health
GET  /api/v1/capabilities
GET  /api/v1/books
GET  /api/v1/books/{book_id}/editions
GET  /api/v1/pages/{page_id}
GET  /api/v1/figures/{figure_id}
GET  /api/v1/assets/{asset_id}
POST /api/v1/search/text
POST /api/v1/search/image
POST /api/v1/search/region
GET  /api/v1/search/{search_id}
GET  /api/v1/associations/{candidate_id}
POST /api/v1/associations/{candidate_id}/verify
POST /api/v1/ingestion/jobs
GET  /api/v1/ingestion/jobs/{job_id}
```

所有错误都使用 `error.code/message/request_id/details`。资源接口会检查 `allow_redistribution`；受限资源返回 `LICENSE_RESTRICTED`。人工核验只更新候选关联状态，不会把底层 `Evidence` 自动改成 `Verified`。

## 本地质量检查

后端在 `backend` 目录执行：

```powershell
python -m compileall -q app tests scripts
ruff check .
mypy app scripts/smoke_fullstack.py
pytest -q
```

前端要求 Node.js `>=22.12.0`，在 `frontend` 目录执行：

```powershell
npm ci
npm run lint
npm run test -- --run
npm run build
```

完整三服务启动后，在项目根目录和 `frontend` 目录分别执行：

```powershell
python backend/scripts/smoke_fullstack.py
cd frontend
npm run test:e2e
```

`smoke_fullstack.py` 从 Nginx 统一入口验证健康、能力、幂等导入、三类检索、会话重读、候选核验和资源许可。Playwright 使用本机 Chrome 验证来源页、文本检索与核验、图片上传和区域搜索。

截至 2026-09-04，前端 11 项 Vitest、后端 47 项 Pytest、全栈 smoke 和 3 项 Playwright E2E 均已通过；重建后的 `db`、`backend`、`frontend` 三个容器均为 healthy。PostgreSQL migration、pgvector 读写和全栈验收必须使用 Docker daemon，不能用 SQLite 替代。

## 目录说明

- `backend/app/retrieval/providers`：离线文本、图像、CFR、关系和 Mock Provider。
- `backend/app/retrieval/rerank/scoring.py`：可解释 EAFR 评分与证据覆盖。
- `backend/app/services/ingestion_service.py`：受控 manifest 的稳定 UUID upsert 和向量生成。
- `backend/scripts/smoke_fullstack.py`：不依赖第三方 Python 包的全栈 smoke runner。
- `backend/data/manifests/jitu-fixture-v1.json`：3 个来源、9 个图单元、18 个区域和 12 个 benchmark pair；其中合成来源 C 专用于验证禁止再分发路径。
- `frontend/`：React 19、TypeScript、Vite、Zod、Vitest、Playwright 和 Nginx 组成的单页应用，覆盖三类检索、来源浏览、图详情、候选比较和人工核验。
- `frontend/e2e/core-flow.spec.ts`：通过真实 Nginx/API/PostgreSQL 链路执行浏览器闭环验收。
- `机图索隐_前端对接提示词.md`：前后端接口与文案约束。
- `机图索隐_前端修复提示词.md`：前端契约审查与修复要求记录。

首版不提供登录、账号体系、Celery、Redis、PyTorch 或远程模型。确定性 Provider 是工程 baseline，不宣称具备真实语义理解能力；前端展示的关联、分数和证据也不构成历史传承结论。

## V1.1-B 真实古籍试点进展

2026-09-04 已完成首批真实来源登记和页面准备：

- 《天工开物》第二册：28 页，作为首批 OCR/版面标注试点。
- 《农政全书》第一册：79 页，已下载并完成来源登记，待逐页审查后再纳入标注。
- 两份原始 PDF 均来自 Wikimedia Commons 的 National Archives of Japan 扫描，文件页元数据显示为 Public domain；来源链接、Commons SHA-1、本地 SHA-256、页数和字节数记录在 `backend/data/real_pilot/sources.json`。
- `backend/scripts/prepare_real_pilot.py` 已将首批 28 页渲染为 PNG，并生成 `backend/data/real_pilot/derived_pages.json`。渲染图位于被 Git 忽略的 `backend/data/processed/real_pilot_v1/`，不会随代码提交；`backend/.dockerignore` 也排除真实 PDF 和渲染图，避免进入后端镜像。
- 页面库存仅包含尺寸、哈希、来源和待标注占位字段；尚未完成 OCR、版面/图题/功能标注或真实检索评测，`evaluation_status` 保持 `not_evaluated`。

准备命令：

```powershell
python backend/scripts/download_real_pilot.py
python backend/scripts/prepare_real_pilot.py
# 需要渲染第二来源时：
python backend/scripts/prepare_real_pilot.py --source-id commons-najda-nongzheng-quanshu-1
```

原始 PDF 不提交 Git；对外发布前重新检查 Commons 文件页及目标司法辖区的训练、展示和再分发权利。

### 运行真实 OCR

页面库存准备完成后，安装并固定经过选型的 OCR 运行时，再执行：

```powershell
python backend/scripts/run_real_pilot_ocr.py --limit 1
```

当前环境未安装 PaddleOCR，因此命令会返回 `MODEL_UNAVAILABLE` 并且不会生成伪造文本。安装后命令将按页面库存写入 raw OCR 行、像素坐标、置信度、Provider/模型版本、预处理哈希和输入图像哈希；`corrected_text` 始终留空，待人工逐字校订。
