# 机图索隐前端 (JiTuSoyo Frontend)

本目录为“机图索隐”项目的前端单页应用（SPA）。

## 技术栈
- React 19
- TypeScript
- Vite
- Tailwind CSS v4
- React Router DOM
- Vitest & React Testing Library (测试)

## 本地开发启动

在 `frontend` 目录下运行：
```bash
npm install
npm run dev
```
将启动 Vite 开发服务器，`/api` 代理转发到 `http://localhost:8000`，需确保后端已在运行。

## 构建与测试
```bash
npm run build # 生产构建
npm run test  # 自动化测试
npm run lint  # 代码风格检查
```

## Docker Compose 启动

根目录下可以一键启动前后端及数据库：
```bash
docker compose up --build
```
前端服务通过 Nginx 运行在容器 80 端口并映射到宿主机 80 端口，前端页面入口为：[http://localhost](http://localhost)，`/api/` 路由被自动转发至 `backend:8000`。

## 注意事项
- 本前端严格对接 API v1 的公开契约，在后端 `synthetic_fixture` 及演示环境下运行。
- 不要将受限图片下载到本地持久化。
- 数据与状态如实展示模型推断、人工核验反馈结果。
