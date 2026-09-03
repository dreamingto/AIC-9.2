# 机图索隐后端 V1

这是“机图索隐”智能文化赛道项目的后端工程基线。当前版本面向本地或受控演示环境，完成以下闭环：

`受控 manifest 导入 -> PostgreSQL/pgvector 持久化 -> 文本/图片/区域检索 -> EAFR 重排 -> 证据返回 -> 人工核验持久化`

fixture 是合成数据，只用于验证接口、数据链路和可复现性。它的 `evaluation_status` 为 `not_evaluated`，不能作为真实古籍实验指标或历史传承结论。

## 快速启动

前置条件：Docker Desktop 正在运行。

```powershell
docker compose up --build
```

Compose 默认从 AWS Public ECR 的 Docker 官方镜像缓存获取 Python 3.12 和
PostgreSQL 16，并从 PostgreSQL 官方 PGDG 仓库安装固定版本的 pgvector 0.8.6。
这可避开本机失效的 Docker Hub 镜像加速器；基础镜像地址和 pgvector 包版本均可通过
`.env` 中的 `PYTHON_BASE_IMAGE`、`POSTGRES_BASE_IMAGE`、
`PGVECTOR_PACKAGE_VERSION` 覆盖。后端容器运行依赖固定在
`backend/requirements.lock`。

服务地址：

- API：<http://localhost:8000>
- Swagger：<http://localhost:8000/docs>
- OpenAPI JSON：<http://localhost:8000/openapi.json>

Compose 启动时会先执行 `alembic upgrade head`，然后启动 Uvicorn。数据库不可用时 `/api/v1/health` 返回统一的 `DATABASE_UNAVAILABLE` 错误，不会切换到 SQLite。

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

在 `backend` 目录执行：

```powershell
python -m compileall -q app tests scripts
ruff check .
mypy app
pytest -q
```

当前仓库的纯 Python 检查不依赖外网或大模型。PostgreSQL migration、pgvector 读写和 Docker smoke test 需要 Docker daemon；若 daemon 未启动，这部分不能用 SQLite 替代。

## 目录说明

- `backend/app/retrieval/providers`：离线文本、图像、CFR、关系和 Mock Provider。
- `backend/app/retrieval/rerank/scoring.py`：可解释 EAFR 评分与证据覆盖。
- `backend/app/services/ingestion_service.py`：受控 manifest 的稳定 UUID upsert 和向量生成。
- `backend/data/manifests/jitu-fixture-v1.json`：3 个来源、9 个图单元、18 个区域和 12 个 benchmark pair；其中合成来源 C 专用于验证禁止再分发路径。
- `机图索隐_前端对接提示词.md`：前端实现时直接使用的对接约定。

首版不提供登录、账号体系、Celery、Redis、PyTorch 或远程模型。确定性 Provider 是工程 baseline，不宣称具备真实语义理解能力。
