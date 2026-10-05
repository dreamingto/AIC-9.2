# 机图索隐：国内古籍 AI 辅助比赛演示

更新：2026-10-05。当前用户决策是优先国内出版内容，比赛阶段暂不人工审核。
已完成真实扫描的受控导入和三类检索；人工审核不再是本阶段演示开发的阻塞项。

## 数据范围与来源

| 来源 | 类型 | 实际导入范围 | 图单元 |
| --- | --- | --- | ---: |
| 《耕织图》，中华再造善本／国家图书馆出版社来源，经 Wikimedia Commons 获取 | 国内出版来源，具体版本按来源目录记载 | PDF 第22—26页，五个跨页扫描 | 8 |
| 《天工开物》第2册，中国国家图书馆扫描，经 Wikimedia Commons 获取 | 国内馆藏来源，不称为现代国内出版物 | PDF 第24—26页，三个跨页扫描 | 4 |

国内出版来源占图单元的 8/12。没有把海外馆藏、中国作者和国内出版社混为一类。
《耕织图》原底本馆藏目录不明，不推断；现代出版来源来自文件目录，不作独立书目鉴定。
国图所选页是谷物加工机械，纠正旧 supplementary_ocr_selection 中“纺织”的初筛推断；
旧选页文件和原 OCR 的哈希不变，新范围以 domestic_ai_selection.json 为准。

《耕织图》覆盖煮茧缫丝、框架作业、室内织机、整经、绕架、大型织机和丝束晾挂候选场景。
难以辨认的古籍图题使用“AI 场景名”，不是原文。国图页保存風扇車、土礱、水碓圖、水磨
四个 AI 转录建议。水碓、水磨保留为跨页完整系统，不将水轮和加工部件拆成无关系的两幅图。

导入量：2个来源、8页/8扫描资源、12图、14局部区域、35文本块、59证据、38向量。
复用原来已完成的 PaddleOCR 3.0.3／PP-OCRv5_mobile raw OCR，本轮没有宣称重跑识别。
只引入完全落在对应图单元范围内的65条 raw OCR，保留原始字序和置信度；
页顶题诗或邻图文字不会复制到两个图单元。AI 名称/场景描述共24文本块，raw OCR共11块。

原合成 fixture 保留：3书/9图/18区域。整个业务库现为5书、17页、21图、32区域、
53文本块、86证据、74向量。其中“书”计数指工程来源记录，不是新考证出的五种古籍。

## AI 与评测状态

新类型 `ai_assisted_real_pilot` 与 `synthetic_fixture`、`human_reviewed_real_pilot` 分开。

- 扫描图像为 `Observed`；来源目录/页码为 `Documented`。
- 图题建议、现代场景描述、raw OCR和AI局部框选为 `Inferred`。
- `human_review=false`，`human_review_status=skipped_by_user_for_competition`。
- `independent_ground_truth=false`、`evaluation_status=not_evaluated`、研究指标为null。
- AI文案不填入人工 `corrected_text`，不产生人工确认、qrels或历史 `Verified`。

原人工接纳、冻结和评测工具保持独立。本阶段不要求用户继续确认旧复核页。
CER、WER、图题召回率和检索Recall/MRR/nDCG暂不计算，因为没有独立评测真值。
本轮的测试通过数、API响应时间和稳定排序检查是工程验收，不能替代研究准确率。

真实图单元暂未导入功能槽置信度、图关系或相关性标签，功能/图结构分项按不可用处理。
现有BM25、哈希文本向量和确定性视觉向量是离线工程基线，不代表真实语义模型的效果。
水碓与水磨可作为结构/用途对照案例，不能作为已标注困难负例或历史传承结论。

## 启动与复现

本机已完成导出和导入。**保留真实扫描只读挂载时，使用两个Compose文件启动**：

```powershell
docker compose -f docker-compose.yml -f docker-compose.ai-real.yml up --build -d
```

只运行基础 `docker compose up` 会移除真实资源挂载，已有数据库记录仍在，但原图访问可能404。
基础工程版适合只有合成fixture的干净目录。真实数据未打入Docker镜像，也未提交Git。
干净目录需先恢复有许可的本地PDF、supplementary_pages.json和supplementary_ocr_results.json。

在 backend 目录，使用Python3.12项目环境生成相同数据包：

```powershell
.\.venv\Scripts\python.exe -m scripts.prepare_domestic_ai_manifest
```

生成器校验来源PDF、页面PNG、OCR输入、库存和选页哈希；按指纹创建不可覆盖的PNG副本、
manifest和导出报告。路径受控、许可字段必填，国内出版图单元必须占多数。
当前 manifest 是 `ai-real-domestic-8b4defa06141f66e.json`，SHA-256：
`7752ab965597de901ead44541006786a6c45012e1d96948f77d0cf1cd83d34f6`。

在根目录启动Compose后，可通过现有导入接口重复导入；实体使用稳定UUID，不复制图单元。
比赛版HTTP smoke命令（backend目录）：

```powershell
.\.venv\Scripts\python.exe -m scripts.smoke_ai_real `
  --manifest-name ai-real-domestic-8b4defa06141f66e.json `
  --output data/real_pilot/ai_domestic_exports/8b4defa06141f66e/runtime-smoke.json
```

该命令执行两次导入、页面/原图读取、三类检索、排序复现、会话和候选重读，
不会提交真实数据的人工核验。部署默认后端单文件上限10MiB，Nginx请求体上限12MiB含multipart；
后续更改后端上限时应同步调整代理。

## 页面与演示案例

入口：[比赛演示检索页](http://localhost/search)。将“检索数据”切换为
“真实古籍 · AI 辅助比赛版”，即可隔离合成fixture。

1. 检索“织机 经线”：实测前两项为室内织机、大型织机。打开原图查看来源和AI文本标签。
2. 打开[室内织机](http://localhost/figures/6c713a35-9d9e-52ff-bf83-43abc3bd13bc)，
   对照[水碓](http://localhost/figures/7d7f57ff-d678-5cc5-9e0f-e8ef4589b554)和
   [水磨](http://localhost/figures/e47bcfab-bb14-5cdf-91cb-98c8f9459b8f)，展示来源、图题建议和部件范围。
3. 图片检索可上传真实扫描；区域检索的坐标以整张扫描为基准，允许0.055等合法有限小数。
4. 对照页显示查询摘要、分项得分、缺失模态和证据；本轮真实候选保持pending，不要求提交核验。

文本“织机 经线”、裁剪图片、区域搜索分别返回12、12、11候选；区域搜索排除了自身。
这是候选数量和流程检查，不是Recall或准确率。低分辨率《耕织图》仍有明显OCR噪声，
视觉基线对线描古籍区分力有限；用户应看到待核实标记，而非可靠转录承诺。

## 实际验收与下一阶段

- 后端全量197 passed、2个opt-in PostgreSQL用例默认skipped、2个既有上游弃用warning。
- 单独启动一次性PostgreSQL/pgvector测试库，空库Alembic迁移成功，两个opt-in集成用例2 passed。
- compileall、Ruff app/scripts/tests、Mypy app/scripts（71源文件）通过。
- 前端lint、Vitest12 passed、生产构建通过；实际Chrome/Playwright工程及真实古籍E2E共5 passed。
- Compose构建和只读资源挂载成功；三服务healthy。HTTP smoke和数据库计数独立核对通过。
- E2E核验提交仅发生在合成fixture；真实古籍没有被自动核验。
- 后端重启后，原已保存的文本/图片/区域会话仍返回12/12/11候选；Nginx健康接口200。
  独立SQL确认真实古籍核验记录为0，35文本均Inferred且corrected_text均null。
  两个临时集成测试容器已停止，保留恢复能力；业务三服务继续运行。

实测修复：多区域候选重读时保留原相似度顺序；Nginx不再以默认1MB拦截合法扫描上传；
区域数字表单取消0.01步长限制。测试mock未被用于真实业务候选或OCR。

下一阶段保持不人工审核，优先引入适合中文古籍的真实文本/视觉检索Provider，
保存Provider版本和资源预算，仍只报告工程性能与案例观察。随后固定2个国内古籍演示案例，
整理技术方案、演示脚本和视频材料；正式效果指标继续保持not_evaluated，直到另有独立评测方案。

详细运行报告在 `backend/data/real_pilot/ai_domestic_exports/8b4defa06141f66e/`；
原扫描、raw、旧人工候选和AI导出保持不变。本轮未commit或push。
