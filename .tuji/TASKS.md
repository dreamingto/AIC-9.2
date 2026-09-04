# 后续任务

1. 接入许可明确的真实古籍扫描、OCR 和人工校订数据。
2. 选定真实模型后建立固定维度 ANN 索引并进行对比实验。
3. 为比赛演示补充运行监控、备份恢复和更高层端到端自动化。
4. fixture 保持 `not_evaluated`；真实实验另建数据版本、指标和复现实验记录。
5. Docker Desktop 可用后执行三服务 `docker compose up --build`、fixture 导入、三类检索、资源许可和核验持久化全栈 smoke test。
6. 增加 Playwright 或 Cypress 浏览器 E2E，覆盖真实 Nginx 代理、图片上传、区域搜索和核验流程。
7. 收紧前端契约与类型：移除测试中的显式 `any` 和异常强转；对齐图片查询 `filename` 可空性及错误 `details` 必填性。
