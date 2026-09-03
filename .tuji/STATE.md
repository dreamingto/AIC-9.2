# 当前状态

## 已完成

- 工程配置、Docker Compose、Dockerfile、Alembic 显式迁移。
- SQLAlchemy 领域模型和 provenance 字段。
- 受控 manifest loader、SHA-256/PNG/许可校验和稳定 UUID 导入器。
- 256 维确定性文本/图像 Provider、BM25、规则 CFR、关系 Provider 和 EAFR。
- FastAPI V1 路由、统一错误、request ID、CORS、资源访问和核验持久化。
- 3 sources、9 figures、18 regions、54 functional assertions、27 evidence、12 benchmark pairs fixture。
- 新增 `docs/机图索隐_项目策划书.md`、`docs/机图索隐_项目需求文档.md` 和 `docs/机图索隐_项目技术文档.md`，分别覆盖竞赛策划、产品需求与当前实现细节。
- 三份文档均区分已实现能力与后续规划，并明确 fixture 为 `not_evaluated`，OCR、真实古籍/真实模型和 ANN 尚未接入。

## 验证结果

- Python 3.12.13：`pytest -q` 39 passed，2 个 TestClient 依赖弃用警告。
- `ruff check .`：通过。
- `mypy app`：通过（46 个源文件）。
- `python -m compileall`：通过。
- `pip check`：通过，无损坏依赖。
- FastAPI OpenAPI：15 个 V1 操作已注册，Swagger 返回 200。
- 文档自检：三份 Markdown 均已落盘；标题结构无重复章节序号；15 个 V1 操作、15 张领域表、39 项测试及 fixture 规模与代码和验收记录一致。

## 数据库验收状态

- `docker compose --progress plain build` 与 `docker compose up -d` 均通过。
- 使用 PostgreSQL 16 和 PGDG pgvector 0.8.6；迁移版本为 `0001_initial`。
- 数据库有 15 张领域表及 `alembic_version`，共 16 张 public 表。
- pgvector 实际保存 image 27 条、text 9 条，向量维度均为 256。
- fixture 重复导入完成且核心实体稳定为 3 books、9 figures、18 regions。
- 文本、图片、区域检索均读取数据库并返回有限分数。
- 核验状态在后端重启及镜像重建后仍存在；底层 Evidence 未被自动升级。
- 6 个可再分发资源返回 200；3 个受限资源返回 `LICENSE_RESTRICTED` 403。

## 未完成

- 真实古籍数据、OCR、真实模型和研究指标尚未接入。
- EAFR 当前使用代码级注入权重和固定模态可靠性（可用 1、不可用 0）；环境配置、来源质量驱动的动态缩放与效果验证尚未完成。
