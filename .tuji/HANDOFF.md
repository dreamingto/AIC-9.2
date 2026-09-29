# 交接

项目已集成 React 前端、FastAPI 后端与 PostgreSQL/pgvector。运行 `docker compose up --build` 可构建并启动前端 `http://localhost`、后端 `http://localhost:8000` 和数据库；项目通过 AWS Public ECR 的 Docker 官方镜像缓存避开失效的全局 USTC 镜像源，并使用 PGDG 固定版本 pgvector 包。

2026-09-04 已完成最新三服务镜像构建和重建，`db`、`backend`、`frontend` 均为 healthy。`python backend/scripts/smoke_fullstack.py` 与 `cd frontend; npm run test:e2e` 已在最新容器上通过，覆盖真实 Nginx 代理、PostgreSQL、fixture 幂等导入、三类检索、资源许可和候选核验。

当前检查结果：后端 47 项测试、前端 11 项测试、Playwright 3 项 E2E 全部通过，前后端 lint/type/build/OpenAPI/Compose 配置和全栈 smoke 通过。V1.1-B 已启动：真实古籍许可元数据与首批页面准备完成，下一步接入 OCR Provider 与 raw/corrected 双层文本；不要直接跳到效果宣称。

没有真实数据和真实模型时，报告中使用 `not_evaluated`，不得把 fixture 排名或分数写成研究结论。

## V1.1-B 交接状态（2026-09-04）

真实数据准备已经开始：运行 `python backend/scripts/download_real_pilot.py` 可验证两份来源 PDF，运行 `python backend/scripts/prepare_real_pilot.py` 可重建首批《天工开物》28 页页面库存。查看 `backend/data/real_pilot/sources.json`、`derived_pages.json` 和 `annotation_schema.json` 了解来源、页面哈希与标注字段。

当前页面库存只证明来源文件和渲染链路可复现；OCR、版面/图题/功能标注、Page/Figure 数据库导入和真实检索评测尚未完成。不要把待处理页面当作已有搜索结果，也不要将 Commons 的作品公版元数据直接扩展为所有用途的法律许可。

安装并固定 OCR Provider 后运行 `python backend/scripts/run_real_pilot_ocr.py`。当前环境没有 PaddleOCR，命令会明确返回 `MODEL_UNAVAILABLE`；这一步不能用 fixture 文本替代。

后端镜像构建已验证：`backend/.dockerignore` 排除 `real_pilot_v1` 原始 PDF 与渲染 PNG，构建上下文约 16 KB；重建后 `/api/v1/health` 200 且容器 healthy。

Compose backend 目前仅只读挂载 `manifests` 与 `fixture_v1`，运行容器中不存在 `real_pilot_v1` 原始 PDF；真实页面准备和 OCR 脚本应在宿主机受控目录执行。
