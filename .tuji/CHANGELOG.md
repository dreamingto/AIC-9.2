# 变更记录

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
