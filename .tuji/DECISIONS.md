# 关键决策

1. 首版使用 PostgreSQL 16 + pgvector，数据库不可用时明确返回 503，不切换 SQLite。
2. 首版 Provider 全部离线确定性实现，真实模型通过接口后续接入。
3. Relation 是单个 Figure 内的 subject/predicate/object 三元组，跨图关系只作为 AssociationCandidate。
4. EAFR 分数保存分项、权重、模态可用性、可靠性、证据覆盖和模型不确定性。
5. 人工核验只更新候选关联状态，不自动修改底层 Evidence 状态。
6. fixture 明确标记 `synthetic_fixture` 和 `not_evaluated`。
7. Compose 默认使用 AWS Public ECR 的 Docker 官方镜像缓存，避免依赖本机失效的全局镜像加速器。
8. pgvector 使用 PGDG 的 `postgresql-16-pgvector=0.8.6-1.pgdg13+1` 固定包。
9. 后端 Linux/Python 3.12 运行时依赖固定在 `backend/requirements.lock`。
