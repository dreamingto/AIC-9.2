# 交接

项目已集成 React 前端、FastAPI 后端与 PostgreSQL/pgvector。运行 `docker compose up --build` 应构建并启动前端 `http://localhost`、后端 `http://localhost:8000` 和数据库；项目通过 AWS Public ECR 的 Docker 官方镜像缓存避开失效的全局 USTC 镜像源，并使用 PGDG 固定版本 pgvector 包。

历史验收已真实完成后端容器构建、fixture 导入、三类检索、资源许可和核验持久化。本轮审查时 Docker Desktop daemon 未运行，因此新增前端镜像、完整 Compose 拓扑与浏览器 E2E 标记为 `not_run`；不能据此声称本轮完成了容器集成验收。

当前本地检查结果：后端 39 项测试通过，前端 11 项测试通过，前后端 lint/type/build/OpenAPI/Compose 配置检查通过。后续应先在 Docker daemon 可用时重跑全栈 smoke test，再接入许可明确的真实古籍数据、OCR 与真实模型。

没有真实数据和真实模型时，报告中使用 `not_evaluated`，不得把 fixture 排名或分数写成研究结论。
