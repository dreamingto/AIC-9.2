# 机图索隐：国内古籍证据感知检索

当前比赛版V1.2.1：FastAPI/PostgreSQL/pgvector与React19/Nginx全栈，BGE-small-zh-v1.5中文文本、Chinese-CLIP视觉/中文图文、PaddleOCR raw、文本/图片/区域检索、来源证据与候选核验持久化。12幅国内真实图与9幅synthetic fixture分别标记；AI数据保持Inferred，研究指标not_evaluated。

真实内容以中华再造善本/国家图书馆出版社来源《耕织图》8图为主，国图馆藏《天工开物》4图补充。Commons是获取渠道，国内出版与馆藏分别记录。两个固定案例为织机及水碓/水磨；排名实际计算，没有硬编码期望名次。

## 启动

Windows、Docker Desktop，Docker Compose >=2.24.4。源码不需要私密.env即可解析默认Compose；启动脚本会首次从模板创建.env，已有配置不覆盖。

```powershell
./scripts/start.ps1 -Profile fixture  # 干净目录合成工程版
./scripts/start.ps1 -Profile real     # 已恢复国内数据的离线基线
./scripts/start.ps1 -Profile neural   # 已准备真实数据、模型和索引
```

入口：<http://localhost>；固定案例<http://localhost/demo>；Swagger<http://localhost:8000/docs>；OpenAPI<http://localhost:8000/openapi.json>。

fixture启动后导入：

```powershell
$body = '{"manifest_name":"jitu-fixture-v1.json","dry_run":false}'
$job = Invoke-RestMethod -Method Post -Uri http://localhost:8000/api/v1/ingestion/jobs -ContentType application/json -Body $body
Invoke-RestMethod ('http://localhost:8000/api/v1/ingestion/jobs/' + $job.id)
```

数据库不可用明确503，不用SQLite。神经模型或兼容索引不可用明确503，不静默回退。已导入真实数据时保留ai-real资产挂载。Profile切换共用本机业务卷；独立测试/复现使用独立项目与空库。

## 真实数据与模型复现

[release/README.md](release/README.md)提供冻结输入包、逐文件锁、安全恢复、原始PDF、8扫描、库存/raw OCR、固定manifest和88条国内向量恢复步骤。权重不放Git，独立模型环境见[model_runtime/README.md](backend/model_runtime/README.md)。

国内数据包本机位于`D:/codex-releases/AIC-9.2/`，发布信息与SHA见`release/`。没有冻结包，只能启动工程版；从PDF重新OCR会创建新输入版本。模型固定revision、文件SHA256及预处理；512维BGE与CLIP不混算。基线256维与神经512维并存，迁移0002_model_spaces。初次准备需要下载，此后推理只读本地文件。

## API（17个操作）

```text
GET  /api/v1/health
GET  /api/v1/capabilities
GET  /api/v1/books
GET  /api/v1/books/{book_id}/editions
GET  /api/v1/pages/{page_id}
GET  /api/v1/figures/{figure_id}
GET  /api/v1/assets/{asset_id}
POST /api/v1/search/text
POST /api/v1/search/image
POST /api/v1/search/region
GET  /api/v1/search/{search_id}
GET  /api/v1/associations/{candidate_id}
POST /api/v1/associations/{candidate_id}/verify
POST /api/v1/ingestion/jobs
GET  /api/v1/ingestion/jobs/{job_id}
GET  /api/v1/demo/cases
POST /api/v1/demo/cases/{case_id}/search
```

错误统一error.code/message/request_id/details。禁止再分发资源403；核验不自动升级Evidence。上传校验MIME/魔数/字节/像素，区域只接受有限归一化正面积。

## 评分与证据

EAFR返回sv/st/sr/sf/sg/se/u_model、可用性、可靠性、贡献和权重。环境JSON配置：

```text
EAFR_WEIGHTS={"beta_v":0.25,"beta_t":0.25,"beta_r":0.2,"beta_f":0.2,"beta_g":0.05,"lambda_e":0.1,"lambda_u":0.05}
```

值有限且在[0,1]，未知键拒绝。默认为工程参数，无最优性主张。缺失项不可用且不重归一放大；动态来源可靠性尚未学习。局部查询只继承空间支持完全落在crop内的主张；策略eafr-v2-spatial和权重存入会话，旧快照保留。

实验V2覆盖12图、72槽（45草稿/27unknown）、10关系均Inferred/confidence=null，关系不参与图重排。实验草稿未写入业务标签或默认线上排序。固定24开发查询/8方法、176适用组合/16不适用；无独立qrels，不算Recall/MRR/nDCG。backend目录执行：

```powershell
.venv/Scripts/python.exe -X utf8 -m scripts.run_domestic_comparison
```

## 检查

backend：python -m compileall -q app scripts tests model_runtime；ruff check app scripts tests model_runtime；mypy app scripts；pytest -q。

frontend（Node>=22.12）：npm ci；npm run lint；npm run test -- --run；npm run build。真实服务使用npm run test:e2e。

GitHub Actions含前后端检查和独立PG迁移/集成。后端生成frontend/src/types/openapi.json，CI拒绝未提交的契约变化，Vitest比较后端字段与前端Zod响应Schema。接口更新后在backend执行python -m scripts.export_openapi --output ../frontend/src/types/openapi.json。

## 仓库结构与说明

```text
backend/
  app/              API、数据模型、导入、检索、评分和证据服务
  migrations/       PostgreSQL / pgvector 迁移
  model_runtime/    可选神经模型服务、下载器与模型锁
  scripts/          OCR、标注、导入、索引、数据恢复及对照工具
  data/             受控配置、来源登记、实验协议和最小合成样例
  tests/            后端自动化测试
frontend/           React 应用、API 契约和组件 / 浏览器测试
scripts/            项目启动与源码边界检查
release/            国内数据校验锁、恢复说明和隔离运行配置
docs/               当前架构与 API 说明
.github/workflows/  持续集成
```

- [架构、功能与数据流程](docs/architecture.md)
- [接口与请求约定](docs/api.md)
- [真实数据恢复与模型准备](release/README.md)
- [中文模型服务](backend/model_runtime/README.md)
- [OCR 与标注数据说明](backend/data/real_pilot/README.md)
- [前端启动与构建](frontend/README.md)

仓库保留完整功能代码、依赖锁、配置、迁移、必要样例、自动化测试与 CI。开发提示词、阶段计划、个人交接日志、审查报告、比赛材料及其制作工具只在本地保存，并由 `.gitignore` 排除。原始扫描、模型权重、数据库、输出文件和缓存也独立本地管理。

历史源码与固定数据仍可从 [V1.2.1 源码归档](https://github.com/dreamingto/AIC-9.2/releases/tag/v1.2.1-competition-preview) 和 [V1.2.0 数据资产](https://github.com/dreamingto/AIC-9.2/releases/tag/v1.2.0-competition-preview) 获取。运行所需数据按 `release/domestic-data.lock.json` 校验；新的仓库整理不修改既有冻结模型、输入、实验协议或历史发布资产。

比赛阶段暂不人工审核；可选标注流程保留。AI 场景、功能和关系不构成历史结论；没有独立真值时 CER、WER、图题召回率及检索研究指标保持 `not_evaluated`。
