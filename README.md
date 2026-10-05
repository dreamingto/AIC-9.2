# 机图索隐：国内古籍证据感知检索

当前比赛版V1.2：FastAPI/PostgreSQL/pgvector与React19/Nginx全栈，BGE-small-zh-v1.5中文文本、Chinese-CLIP视觉/中文图文、PaddleOCR raw、文本/图片/区域检索、来源证据与候选核验持久化。12幅国内真实图与9幅synthetic fixture分别标记；AI数据保持Inferred，研究指标not_evaluated。

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

## 文档与材料

[V1.2 发布与下载](https://github.com/dreamingto/AIC-9.2/releases/tag/v1.2.0-competition-preview) 已提供完整源码包、冻结国内数据恢复包、匿名预审材料包和独立 PDF/MP4。代码提交与通过的在线 CI、各资产 SHA256 见 [发布记录](release/publication.json)。正式参赛团队信息与百度网盘/报名系统提交仍需参赛者办理。

- [当前架构与需求](docs/机图索隐_当前架构与需求_V1.2.md)
- [审查及修复记录](docs/机图索隐_项目与Git完整性审查_2026-10-05.md)
- [固定查询V1](docs/机图索隐_固定查询算法对照与功能证据草稿.md)：历史结果，新报告独立生成。
- [模型与案例](docs/机图索隐_真实检索模型与固定案例.md)
- [国内数据](docs/机图索隐_国内古籍AI比赛演示.md)
- competition/：技术报告源稿、简介、讲稿、答辩内容与生成工具。
- .tuji/TESTS.md：实际检查、跳过、not_run分轮记录。

长文保留历史基线范围；当前能力以V1.2说明为准。比赛暂不人工审核，旧人工工作流可选。AI场景、动态功能和关系不是历史结论；无独立真值时CER/WER/图题召回等保持not_evaluated。
