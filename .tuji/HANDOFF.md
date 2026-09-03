# 交接

Docker Desktop 已启动，后端与 PostgreSQL/pgvector 容器正在运行。项目通过 AWS Public ECR 的 Docker 官方镜像缓存避开失效的全局 USTC 镜像源，并使用 PGDG 固定版本 pgvector 包。运行 `docker compose up --build` 可复现构建、迁移并启动 `http://localhost:8000`。

fixture 已导入，三类检索、资源许可和核验持久化已完成真实 smoke test。后续开发从接入许可明确的真实古籍数据、OCR 与真实模型开始。

没有真实数据和真实模型时，报告中使用 `not_evaluated`，不得把 fixture 排名或分数写成研究结论。
