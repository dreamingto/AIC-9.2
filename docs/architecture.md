# 架构与数据流程

机图索隐面向古籍技术图像，提供文本、图片和局部区域检索，并返回可追溯的来源、证据与评分。当前比赛实现为 V1.2.1；图像相似和模型分数提供比较线索，不自动判断历史传承。

## 服务关系

```text
浏览器 React / TypeScript / Zod
  → Nginx 静态页面与 /api 代理
  → FastAPI / Pydantic
      → 来源目录、数据导入、检索与候选核验
      → PostgreSQL 16 / pgvector
      → 可选宿主神经模型 worker（8767）

独立 PaddleOCR 环境 → raw OCR / 标注工具 → 受控 manifest → 数据导入
```

后端业务镜像不安装大型视觉模型。OCR 与神经检索各使用独立运行环境；模型权重不放 Git，worker 按固定 revision、文件 SHA-256 和预处理校验后只读本地文件。模型维度相同也不代表同一向量空间。

## 代码模块

| 目录 | 功能 |
|---|---|
| `backend/app/api` | 公开 V1 API 与依赖注入 |
| `backend/app/db` | SQLAlchemy 实体、连接与事务 |
| `backend/app/ingestion` | fixture、AI 辅助与人工审核 manifest 合同及校验 |
| `backend/app/repositories` | 目录、搜索快照和候选读取 |
| `backend/app/retrieval` | BM25、Provider、CFR、图关系、空间证据、EAFR 与对照算法 |
| `backend/app/services` | 导入任务、统一检索与响应序列化 |
| `backend/model_runtime` | BGE / Chinese-CLIP 本地推理、下载与文件锁 |
| `backend/scripts` | OCR、标注转换、校订轨迹、导入准备、索引及恢复 |
| `frontend/src` | 页面、集中 API 客户端、Zod 契约与请求中止 |

## 数据链

`Book → Edition → Page → Figure → Region / TextChunk` 保存书籍、版本、原页、技术图、局部框和文本。`Evidence`、功能断言与单图关系保存主张与引用。`EmbeddingRecord` 记录 Provider、模型、版本、维度和预处理身份；256 维基线与 512 维神经向量可并存，首版精确计算相似度。

导入只接受配置目录内的 manifest 文件名，校验 schema、资源路径、文件哈希、许可与引用后写入数据库。扫描、原始 OCR、AI 建议和独立 corrected 文本分别保存，人工修改不覆盖 raw。核验作用于一次搜索的候选关联，不自动升级底层证据状态。

搜索先生成查询特征并选择兼容向量，再召回、计算分项、排序，最后保存 `SearchSession` 和 `AssociationCandidate`。搜索重读使用持久化快照；新查询生成新的会话。

## 检索与评分

文本使用 BM25 与文本向量；图片使用上传图像特征；区域把归一化坐标映射到原图像素并裁剪，来源图自身排除。真实神经版采用 BGE-small-zh-v1.5 与 Chinese-CLIP ViT-B/16；无大型模型时可以显式启动确定性基线。

EAFR：

```text
S = βv·sv + βt·st + βr·sr + βf·sf + βg·sg + λe·se − λu·Umodel
```

视觉、文本、局部、功能、关系、查询相关证据覆盖和模型不确定性分别返回，连同可用性、可靠性、权重和贡献保存。缺失项不重归一放大；资料缺失率与模型不确定性分开。局部查询仅采用空间支持完整落在裁剪内的主张；关系只在高置信度条件下参与。

默认权重是可配置工程参数，不代表最优或准确率。实验功能草稿仅在独立对照流程使用，不自动写入生产标签。固定查询与算法实现、版本化协议保留在代码库；运行结果在本地输出目录。

## 证据与访问边界

- `Observed`：扫描可观察信息。
- `Documented`：文本或目录记载。
- `Inferred`：模型或规则建议。
- `Verified`：具有对应确认依据的证据状态；不能由排序自动生成。

公开资源先检查数据目录边界与 `allow_redistribution`，受限图返回 403。上传检查 MIME、魔数、大小和像素，临时文件及时清理；坐标拒绝 NaN、Infinity、越界与零面积。错误统一带 request ID，数据库或所选模型不可用明确返回 503，不静默切换 SQLite 或模型。

当前不提供账号服务，仅面向本地或受控演示；CORS 来源由环境变量配置。原图保留比例、水印、出处和许可记录。

## 运行与数据准备

根目录启动脚本提供 `fixture`、`real`、`neural` 三档。fixture 可从 Git 中的最小合成样例启动；真实数据需按 [恢复说明](../release/README.md) 恢复外置包。数据库迁移使用 Alembic，隔离测试/复现使用单独库与卷，不操作业务库。

当前演示语料是《耕织图》8 幅图与《天工开物》4 幅图；国内出版/馆藏身份与 Commons 获取渠道分开。真实 AI 文本仍为 Inferred，独立 corrected 和研究真值尚未建立。CER、WER、图题召回率及 Recall/MRR/nDCG 保持 `not_evaluated`。

部署、接口和可选组件分别见 [README](../README.md)、[API](api.md)、[模型服务](../backend/model_runtime/README.md)、[OCR 与标注](../backend/data/real_pilot/README.md)。
