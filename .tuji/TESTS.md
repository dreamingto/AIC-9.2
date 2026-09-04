# 测试记录

## Python 3.12.13

- 编译：`python -m compileall -q app tests scripts` 通过。
- 静态检查：`ruff check .` 通过。
- 类型检查：`mypy app` 通过（46 个源文件）。
- 单元/API 契约测试：39 passed，2 个 TestClient 上游弃用警告。
- 依赖检查：`python -m pip check` 通过。
- OpenAPI：15 个 GET/POST 操作，Swagger 返回 200。

## Docker 与 PostgreSQL

- Compose 配置、数据库镜像、后端锁定依赖镜像和服务启动均通过。
- PostgreSQL 16、pgvector 0.8.6、Alembic `0001_initial` 已真实运行。
- 15 张领域表加 1 张 Alembic 版本表已持久化。
- image 27 条与 text 9 条向量均可由 pgvector 读取，维度均为 256。
- fixture 首次及重复导入完成，统计保持 3/9/18/54/27/12。
- 文本、图片、区域三类检索均返回数据库候选，所有总分为有限数。
- 允许资源返回 PNG/200；受限资源返回统一 `LICENSE_RESTRICTED`/403。
- `worth_comparing` 核验在后端重启和镜像重建后仍存在。

以上 Docker/PostgreSQL 条目来自已完成的历史后端集成验收。

## 前端与本轮全栈审查

- `npm ci`：186 packages，0 vulnerabilities。
- `npm run lint`：通过，0 warnings / 0 errors。
- `npm run test -- --run`：2 个测试文件，11/11 通过。
- `npm run build`：通过，TypeScript 检查与 Vite 生产构建成功。
- `docker compose config --quiet`：通过。
- 敏感信息模式扫描：未发现 API Key、令牌或私钥；`.env`、依赖、构建产物和缓存目录均处于忽略状态。
- Markdown 本地链接检查：未发现断链。
- 本轮 Docker daemon 不可用，因此前端镜像、三服务启动、PostgreSQL 持久化复验和浏览器 E2E 均为 `not_run`。
