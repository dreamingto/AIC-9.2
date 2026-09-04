# 机图索隐全栈项目记录

- 状态：V1 前后端闭环已实现；后端曾通过 Docker PostgreSQL/pgvector 集成验收，本轮静态与自动化审查通过。
- 后端：FastAPI、PostgreSQL/pgvector、受控 synthetic fixture、三类检索、EAFR、证据和人工核验。
- 前端：React 19、TypeScript、Vite、Zod、Vitest 与 Nginx；覆盖三类检索、来源、图详情、比较和核验页面。
- 边界：不登录、不自动判定历史传承、不把 fixture 指标当研究结果。
