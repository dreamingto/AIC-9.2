# 测试记录

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

- `docker compose build backend`：通过；构建上下文由约 111 MB 降至约 16 KB，确认真实 PDF 与渲染 PNG 未进入镜像。重建并重启后端后 `/api/v1/health` 返回 200，容器 healthy。

- V1.1-B 镜像重建后再次运行 `backend/scripts/smoke_fullstack.py`：通过；3 books、文本/图片/区域检索、幂等导入、核验持久化和 allowed/restricted 许可检查均正常，Provider 5 个，结果 `not_evaluated`。

- Compose 收窄 backend 数据卷后重启验证：容器内 `/app/data/assets/real_pilot_v1` 不存在，仅挂载 fixture PNG 和 manifest；全栈 smoke 再次通过。
