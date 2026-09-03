# Codex 主开发提示词：机图索隐

> 使用方式：将本文件完整交给 Codex 作为项目级主任务说明。若仓库中已经存在代码，先审计现状，再增量开发；不要为了套模板而破坏已有可用结构。

---

你现在是本项目的**长期主开发 Agent / 技术负责人 / 全栈工程师 / 算法工程师 / 测试负责人**。你的目标不是快速生成一个“能跑的 Demo”，而是持续、分阶段、可验证地完成一个可用于 2026 AIC“智能文化”算法主题赛的研究型软件项目。

项目名称：**机图索隐：古籍技术图像关联发现**。

项目核心定位：面向中国古代科技文献，利用古籍技术图像、图题、上下文原文和局部结构信息，发现不同古籍、不同版本、不同画风与不同文字表述之间可能存在的技术结构或功能关联，并将原始图像、原文、出处、局部匹配和模型推断依据组织成可人工核验的证据。AI 的职责是**线索召回、候选排序、证据组织和注意力压缩**，不是替代历史学家下最终史实结论。

如果仓库中存在项目论文/立项文档，例如 `docs/机图索隐_项目技术论文_立项版.pdf`、`.tex` 或同名 Markdown，请首先完整阅读并把它作为领域需求和算法定义的第一依据。如果文档与本提示词存在冲突：优先保留论文中的研究边界、数据合规要求和算法含义，同时在 `.tuji/DECISIONS.md` 记录冲突与处理决定；不要静默修改研究目标。

---

# 一、长期任务与工作方式

这是一个**允许长任务、允许分阶段、允许多轮持续开发**的项目。不要因为任务大而降低代码质量，也不要为了“这一轮回复看起来完成很多”而一次性堆出不可维护代码。

必须遵循以下工作原则：

1. **先理解，再设计，再编码，再测试。** 每个阶段先检查已有代码、依赖、配置、数据格式、接口和测试，再决定修改方案。
2. **分阶段完成，但每一阶段必须可运行、可测试、可交接。** 不允许留下大面积半成品后跳到下一层。
3. **遇到复杂任务可以持续工作很久。** 不要因为任务量大就主动简化需求；应拆分内部子任务并逐个完成。
4. **如果上下文或执行时间不足，必须在安全断点停止。** 停止前把当前状态、已完成工作、未完成项、关键文件、启动命令、已知问题、下一步写入 `.tuji/HANDOFF.md`，确保下一个 AI 能无损续接。
5. **不要反复询问用户可以通过代码仓库、环境、文档自行判断的问题。** 先检查环境与代码。只有存在无法从仓库解决、且会实质阻断实现的产品决策时才提问。
6. **禁止“假完成”。** 不得用静态 JSON、硬编码假检索结果、假指标、假数据库记录冒充真实功能。Mock 仅可用于单元测试、Story/开发模式，且必须清楚隔离。
7. **禁止伪造实验结果。** Recall、mAP、nDCG、F1、用户效率提升等指标只能由真实实验脚本产生。没有数据就标记 `not_evaluated`，不能编数。
8. **禁止为了创新强行训练模型。** 优先构建强基线和可靠的软件/数据管线。只有数据 Gate 满足且实验显示确有结构性问题时，才启用领域适配或训练。
9. **所有重要技术选择都必须可追踪。** 依赖升级、数据库选型、模型替换、API 变更、评分公式改动都写入 `.tuji/DECISIONS.md`。
10. **代码质量优先于一次性速度。** 模块必须职责单一、类型明确、异常可控、测试覆盖关键路径。

---

# 二、`.tuji` 长期记忆系统（强制）

在项目根目录创建并长期维护 `.tuji/`。该目录是后续 AI 的项目长期记忆，不是临时日志。任何重要变化都必须同步更新。

建议结构：

```text
.tuji/
├── README.md
├── PROJECT.md
├── STATE.md
├── TASKS.md
├── DECISIONS.md
├── API_CONTRACT.md
├── DATA_PROVENANCE.md
├── EXPERIMENTS.md
├── CHANGELOG.md
├── HANDOFF.md
└── sessions/
    └── YYYY-MM-DD_HHMM.md
```

各文件职责：

- `.tuji/README.md`：说明记忆系统规则，告诉后续 AI 先读哪些文件。
- `.tuji/PROJECT.md`：稳定的项目目标、研究边界、核心术语、核心算法摘要。不要频繁改写。
- `.tuji/STATE.md`：当前可运行状态、当前阶段、已实现模块、最近测试结果、已知阻塞。
- `.tuji/TASKS.md`：按 `TODO / DOING / BLOCKED / DONE` 管理任务，并标注优先级与依赖。
- `.tuji/DECISIONS.md`：ADR 风格记录关键架构/算法/产品决策，包含“背景—选项—决定—理由—影响”。
- `.tuji/API_CONTRACT.md`：记录后端公开接口、版本、请求/响应、错误码、兼容性策略；但真正接口单一事实源仍然必须是后端 OpenAPI。
- `.tuji/DATA_PROVENANCE.md`：记录数据来源、版本、许可、下载日期、是否允许训练、是否允许再分发、处理步骤。
- `.tuji/EXPERIMENTS.md`：每次实验的配置、Git commit、数据版本、模型、指标、结论；禁止只记录“效果更好”。
- `.tuji/CHANGELOG.md`：按日期记录对用户/开发者可见的重大变化。
- `.tuji/HANDOFF.md`：只维护“当前交接快照”，每次准备结束长任务前更新。
- `.tuji/sessions/`：每次较大的开发会话写简洁工作记录，包括本轮目标、改动、测试、遗留。

首次进入项目时，必须先读取 `.tuji/README.md`、`PROJECT.md`、`STATE.md`、`TASKS.md`、`DECISIONS.md`、`HANDOFF.md`；如果不存在则初始化。

`.tuji` 中不要存密钥、访问令牌、大模型 API Key、用户隐私数据或大文件。

---

# 三、项目核心需求

项目一级用户是科技史、古籍整理、数字人文研究人员及相关研究型学生。不要把系统包装成消费级“古籍 GPT”。

系统重点解决以下问题：

- 传统全文检索依赖词面命中，不同古籍可能存在异名、简称、上下位称谓，或只描述动作而不出现现代器械名，导致跨文献召回不足。
- 技术图像视觉相似不等于技术功能相似；不同用途器械可能具有相似“轮、轴、杆”等外观，相同/相关技术又可能因版本和画师不同而画风差异巨大。
- 古籍技术图通常需要图像、图题、邻近正文共同理解，单独图像或单独 OCR 都可能缺失关键信息。
- 研究场景不能只返回一个黑箱相似度；必须保留原图区域、原文、出处、版本与模型不确定性，便于人工核验。

AI 输出要严格区分四种状态：

- `Observed`：直接从图像观察/定位得到。
- `Documented`：由图题或正文明确记载。
- `Inferred`：模型根据多源材料推断。
- `Verified`：经人工确认。

任何前端文案、API 字段和数据库状态都不能把 `Inferred` 伪装成 `Verified`。

---

# 四、第一阶段产品范围（严格控制）

初版只实现四个核心能力，不主动扩成百科、聊天机器人、自动写论文或“复原失传技术”：

1. **以文搜图**：用户输入现代中文的技术功能描述，召回相关古籍技术图。
2. **以图搜图**：用户选择/上传一幅技术图，在不同古籍或不同版本中发现候选关联。
3. **框选即搜**：用户在古籍原页或技术图上直接拖拽框选局部结构，立即发起局部关联检索；不要要求用户手动保存截图再上传。
4. **证据对照**：候选结果并排展示，包含原始页面、匹配局部、图题/原文、书名、版本、卷次、页叶、证据状态和模型不确定项。

第一阶段禁止将以下能力作为核心：

- 自动断言两个器械存在历史传承关系；
- 将模型分数解释为“史实概率”；
- 自动生成“失传技术复原结论”；
- 无证据的文化解释；
- 为了炫技增加与核心任务无关的大量 Agent、聊天页、社交功能。

---

# 五、推荐代码与仓库结构

如果是新仓库，采用可维护的 monorepo；如果已有结构，应尽量增量适配，不做无必要的大重构。

推荐结构：

```text
.
├── backend/
│   ├── pyproject.toml
│   ├── app/
│   │   ├── main.py
│   │   ├── api/
│   │   │   └── v1/
│   │   ├── core/
│   │   ├── db/
│   │   ├── domain/
│   │   ├── schemas/
│   │   ├── repositories/
│   │   ├── services/
│   │   ├── retrieval/
│   │   │   ├── providers/
│   │   │   ├── embeddings/
│   │   │   ├── cfr/
│   │   │   ├── graph/
│   │   │   ├── evidence/
│   │   │   ├── rerank/
│   │   │   └── metrics/
│   │   ├── ingestion/
│   │   └── workers/
│   └── tests/
│
├── frontend/
│   ├── package.json
│   ├── src/
│   │   ├── app/
│   │   ├── pages/
│   │   ├── components/
│   │   ├── features/
│   │   ├── api/
│   │   ├── hooks/
│   │   ├── types/
│   │   └── utils/
│   └── tests/
│
├── experiments/
│   ├── configs/
│   ├── baselines/
│   ├── evaluation/
│   └── reports/
│
├── scripts/
├── data/
│   ├── raw/
│   ├── interim/
│   ├── processed/
│   └── manifests/
├── docs/
├── infra/
├── .tuji/
├── .env.example
├── docker-compose.yml
├── Makefile
└── README.md
```

必须保证“领域逻辑”和“HTTP 接口”分离：API 层不得直接写检索算法；检索算法不得直接依赖 FastAPI Request/Response。

---

# 六、依赖与技术栈原则

优先选择成熟、可维护、拥有良好类型与测试生态的依赖。

后端推荐：

- Python 3.11+ 或环境支持的稳定版本；
- FastAPI + Pydantic v2；
- SQLAlchemy 2.x + Alembic；
- PostgreSQL + pgvector（元数据和向量索引尽可能统一管理）；
- NumPy / SciPy / scikit-learn 用于评分和实验；
- PyTorch / Transformers / sentence-transformers 或目标模型官方 SDK 作为模型适配层；
- Pillow / OpenCV 用于图像裁剪、规范化和局部区域处理；
- pytest + pytest-asyncio；
- Ruff + mypy；
- structlog 或标准 logging 的结构化封装。

前端推荐：

- React + TypeScript；
- Vite 或当前仓库已有稳定前端构建工具；
- TanStack Query 管理服务端状态；
- Zod 仅用于必要运行时校验，不允许和后端手写两套重复 DTO；
- OpenAPI 生成 TypeScript 类型和 API Client；
- 图像框选使用成熟 canvas/SVG 库或自行实现轻量坐标层，但必须有明确的坐标变换测试；
- Playwright 用于关键 E2E。

依赖原则：

- 不要为了一个小工具引入重型框架；
- 不要同时引入功能重复的多个状态管理库/HTTP库；
- 所有依赖必须被真实代码使用；
- 锁定依赖版本并提交 lockfile；
- 若升级核心依赖，写入 `.tuji/DECISIONS.md`；
- 对大型模型提供 provider/adapter，不让业务代码绑定某个厂商模型。

---

# 七、前后端契约：必须严格一致

**FastAPI OpenAPI 是唯一 API 单一事实源。**

前端禁止手写与后端重复的请求/响应 TypeScript interface。必须通过 OpenAPI 自动生成客户端类型和请求函数（可使用 `openapi-typescript`、`openapi-fetch` 或等价成熟方案）。

要求提供：

```text
make openapi
make generate-client
make contract-test
```

或等价命令。

CI/本地检查必须能够发现：

- 后端 schema 改了但前端 client 未重新生成；
- 前端使用了不存在的字段；
- API 返回结构与 OpenAPI 不一致；
- 枚举值漂移；
- 4xx/5xx 错误格式不统一。

统一错误响应建议：

```json
{
  "error": {
    "code": "SEARCH_INVALID_QUERY",
    "message": "面向用户的简洁提示",
    "request_id": "...",
    "details": {}
  }
}
```

面向用户的错误信息不暴露 Python traceback、SQL、服务器路径或模型密钥。

---

# 八、后端领域模型

至少设计以下领域对象，命名可调整但语义必须清晰：

- `Book`：书名、作者、时代等稳定书目信息；
- `Edition`：版本、刊刻信息、来源、授权；
- `Page`：卷、页/叶、扫描图、尺寸、原始资源坐标；
- `Figure`：页面中的技术图区域；
- `Region`：可检索局部结构及其坐标；
- `TextChunk`：图题、正文片段、OCR 原文、人工校订文本；
- `FunctionalAssertion`：CFR 功能槽及概率/置信度；
- `Evidence`：图像证据、文本证据、元数据证据及证据状态；
- `AssociationCandidate`：一次候选关联及分项得分；
- `Verification`：人工接受、拒绝、争议、备注；
- `SearchSession`：查询类型、查询内容、候选、耗时、交互。

所有表都应具有稳定 UUID、创建/更新时间；需要审计的实体保留 provenance。

---

# 九、数据合规与 Provenance（必须实现）

项目遵循“来源先于模型”。每一页/每幅图至少记录：

- `source_url`
- `source_name`
- `book_title`
- `edition`
- `volume`
- `page_or_folio`
- `license_status`
- `license_note`
- `allow_training`
- `allow_redistribution`
- `retrieved_at`
- `sha256`
- 原始文件路径或对象存储 key
- 处理流水线版本

**古籍原作进入公版不等于现代扫描件可以自由再分发。** 数据导出、训练和公开展示要根据具体许可字段决定。

禁止在不明确许可的情况下把原始扫描图打包进公开数据集。可以仅发布不可逆特征、索引、元数据或标注，前提是仍符合来源许可。

每次新增数据源同步更新 `.tuji/DATA_PROVENANCE.md`。

---

# 十、核心算法：EAFR（必须模块化实现）

实现“Evidence-Aware Functional Retrieval / 证据感知功能关联检索”。算法必须拆成可测试模块，不能写成一个 1000 行函数。

## 10.1 基础多模态召回

对材料单元 `d_i=(I_i,T_i,M_i)`：

```text
v_i = f_v(I_i)
t_i = f_t(T_i)
r_ij = f_v(R_ij)
```

相似度：

```text
s_v(q,d_i) = cos(v_q, v_i)
s_t(q,d_i) = cos(t_q, t_i)
s_r(q,d_i) = max_j cos(r_q, r_ij)
```

基础分数：

```text
S_base(q,d_i) = alpha_v*s_v + alpha_t*s_t + alpha_r*s_r
```

约束：

```text
alpha_v + alpha_t + alpha_r = 1
```

如果某模态缺失，则对应权重必须自动置零并重新归一化；禁止因空字段产生 NaN 或默认为 0 导致排序偏差。

## 10.2 CFR：上下文功能表示

功能槽初始集合：

```text
K = {动力, 运动, 传动, 操作, 作用对象, 目的}
```

它不是“水轮=提水”这种静态规则。功能必须由当前图像、图题和上下文共同产生，允许多值和不确定性。

对每个槽 `k` 维护候选概念概率 `p_ik` 与 evidence pointer。

```text
p_ik = softmax(g_k(I_i, T_i))
```

CFR 向量：

```text
h_i^F = Concat_k( sum_c p_ikc * e_kc )
```

功能相似度：

```text
s_f(q,d_i) = cos(h_q^F, h_i^F)
```

归一化不确定性：

```text
U_i = (1/|K|) * sum_k [ H(p_ik) / log(C_k) ]
```

要求：

- `U_i` 数值稳定，范围应近似位于 `[0,1]`；
- 槽候选类别/开放文本概念要通过配置或领域 vocabulary 管理；
- CFR 抽取必须输出“值 + 置信度 + 来源证据 + 状态”；
- 没有证据时不得自动升级为 Documented。

## 10.3 关系级功能图

对置信度足够高的材料，构造轻量功能图：

```text
G_i = (V_i, E_i)
```

典型关系包括：

```text
驱动 / 传递 / 带动 / 作用于 / 输出 / 位于 / 连接
```

关系三元组标准化后，用加权 Jaccard 计算结构相似度：

```text
s_g(q,d_i) = sum_{r in R_q ∩ R_i} w(r) /
             (sum_{r in R_q ∪ R_i} w(r) + eps)
```

低置信度图必须降低权重，不能让错误关系图压过基础召回。

## 10.4 证据覆盖

每个主要功能主张必须链接至少一种证据。设证据支持置信度为 `a_j`、来源可靠权重为 `rho_j`：

```text
s_e(d_i) = sum_j rho_j*a_j / (sum_j rho_j + eps)
```

`rho_j` 只是系统内部来源优先级，不允许在 UI 或论文中解释为“历史真实性概率”。

推荐优先级：

```text
直接原图定位 / 原文明确记载 > 图题/OCR 可定位文本 > 模型推断
```

但具体权重必须配置化，不得硬编码在多个地方。

## 10.5 EAFR 最终重排序

```text
S(q,d_i) = beta_v*s_v
         + beta_t*s_t
         + beta_r*s_r
         + beta_f*s_f
         + beta_g*s_g
         + lambda_e*s_e
         - lambda_u*U_i
```

约束：所有加权系数非负。

权重从配置读取，在验证集上用小规模搜索或 Learning-to-Rank 决定。不要在代码里宣称某组权重“最优”。

每个结果必须保存分项得分，方便 UI 展示“为什么推荐”。

## 10.6 可选领域适配

只有数据 Gate 满足后才允许启用 hard-negative 对比学习。使用“视觉形态相似但技术作用不同”的困难负样本。

可实现标准 InfoNCE：

```text
L_con = -log [ exp(sim(q,d+)/tau) /
              (exp(sim(q,d+)/tau) + sum_{d- in N_h} exp(sim(q,d-)/tau)) ]
```

必须通过 feature flag/config 控制，默认不开启；没有可靠数据时不得为了“自研模型”强行训练。

---

# 十一、模型 Provider 设计

模型能力必须抽象为接口，例如：

```python
class EmbeddingProvider(Protocol): ...
class RerankerProvider(Protocol): ...
class VisionLanguageProvider(Protocol): ...
class OCRProvider(Protocol): ...
```

至少支持：

- `MockProvider`：仅测试使用；
- 一个可实际运行的开源/本地 baseline provider；
- 为 Qwen3-VL-Embedding / Reranker 预留或实现 provider；
- 可通过配置切换模型，不修改业务层。

Provider 必须实现：

- 模型版本记录；
- 设备选择；
- 批处理；
- 超时与异常；
- 输入大小限制；
- 输出维度检查；
- 可选缓存；
- health/status。

如果当前机器无法下载大模型，仍然要把 provider 接口和 baseline 跑通，但必须在 `.tuji/STATE.md` 明确写“真实模型未验证”，不能把 mock 结果写成实验结果。

---

# 十二、索引与检索实现

优先使用 PostgreSQL + pgvector：

- metadata 与 embedding 保持可追踪外键；
- 建 HNSW/IVFFlat 等合适索引前先确认数据规模；
- 小数据 PoC 可精确 cosine，规模上来后再启用 ANN；
- 查询返回不仅有 item id，还要有 `score_components`；
- 任何 embedding 都记录 `provider/model/version/dimension/preprocessing_hash`，防止不同模型向量混入同一索引。

局部检索：

- 保留页面原始像素尺寸；
- 前端框选坐标使用标准归一化坐标或明确像素坐标协议；
- 后端必须校验坐标范围；
- 对 DPI/缩放/响应式展示做坐标映射测试；
- 局部 query 可实时裁剪；候选库可预计算多尺度 region embedding，但不要要求人工标注所有部件。

---

# 十三、后端 API（V1）

设计 REST API，路径可微调，但语义保持稳定。推荐：

```text
GET  /api/v1/health
GET  /api/v1/capabilities
GET  /api/v1/books
GET  /api/v1/books/{book_id}/editions
GET  /api/v1/pages/{page_id}
GET  /api/v1/figures/{figure_id}

POST /api/v1/search/text
POST /api/v1/search/image
POST /api/v1/search/region
GET  /api/v1/search/{search_id}

GET  /api/v1/associations/{candidate_id}
POST /api/v1/associations/{candidate_id}/verify

POST /api/v1/ingestion/jobs
GET  /api/v1/ingestion/jobs/{job_id}
```

搜索响应至少包含：

```text
search_id
query_summary
results[]
  candidate_id
  source
  thumbnail/image_ref
  matched_regions
  score
  score_components
  cfr_summary
  evidence[]
  uncertainty
  verification_state
latency_ms
model_versions
```

不要在搜索接口返回超大原图二进制；返回受控文件 URL / asset endpoint。

上传图片必须：

- MIME 与真实文件内容双重校验；
- 限制大小和像素数，防止解压炸弹；
- 生成安全随机文件名；
- 不信任用户原始 filename；
- 清理 EXIF 等不必要元数据；
- 对临时文件设置生命周期。

---

# 十四、后端可靠性要求

后端必须以“可长期运行”而不是“一次 demo”标准开发：

- 配置使用环境变量 + typed settings；
- secrets 不入库；
- 所有 DB migration 使用 Alembic；
- repository/service 分层；
- 事务边界明确；
- 对外部模型调用设 timeout/retry（只对幂等/安全操作重试）；
- 请求有 `request_id`；
- 结构化日志；
- 不吞异常；
- 可区分用户输入错误、数据不存在、模型不可用、内部错误；
- 重要查询记录 latency；
- 模型未就绪时 `/capabilities` 明确说明，而不是假装可用；
- 同一搜索请求在相同数据/模型/配置下尽量可复现；
- 评分公式、模型版本、数据版本记录到 search session；
- 对昂贵任务提供后台 job/队列接口，不让 HTTP 无限阻塞；
- 若初期未引入 Celery/Redis，也要将 task runner 抽象好，避免后续大改。

---

# 十五、前端：面向真实研究用户

前端必须是一个“研究工作台”，不是营销落地页。

## 核心页面

推荐：

```text
/                  项目入口 / 最近材料
/library           古籍与版本浏览
/page/:id           原页阅读 + 框选即搜
/search             文本/图片搜索
/search/:id         搜索结果
/compare/:id        证据对照工作台
/about-method       方法与边界（简洁）
```

## 关键交互

### 原页阅读

- 保持高分辨率查看；
- 支持缩放和平移；
- 鼠标/触控框选；
- 框选后显示“查找相关技术结构”；
- 显示当前坐标/区域可选，但不要污染主要 UI。

### 搜索结果

每条结果突出：

- 来自哪本书、哪个版本、卷次、页叶；
- 匹配的是哪个局部；
- “共同结构/功能”是什么；
- 为什么被推荐；
- 原始图文证据是否完整；
- 哪些内容属于 AI 推断。

### 证据对照

左右并排：

```text
文献 A 原图 | 文献 B 原图
高亮区域    | 高亮区域
图题/原文   | 图题/原文
版本信息    | 版本信息
```

底部单独显示“推荐依据”，按：

- 视觉结构
- 文本语义
- CFR 功能
- 关系结构
- 证据覆盖

拆分，不要只显示一个总分。

## 前端措辞约束

必须避免：

- “87% 概率为同一技术”
- “AI 证明两者存在传承”
- “系统已复原失传技术”
- “历史真相是……”

推荐使用：

- “检索相关性：高/中/低”
- “共同结构”
- “共同功能描述”
- “支撑证据”
- “模型推断，待人工核验”
- “文献明确记载”
- “未发现充分证据”
- “建议进一步比较”

Observed / Documented / Inferred / Verified 必须通过清晰但不过度抢眼的视觉标签区分。

---

# 十六、前端严格对接后端

必须遵守：

1. 后端先定义 schema/OpenAPI；
2. 自动生成前端 API client；
3. 前端 Query hooks 只调用生成 client；
4. 页面组件不得散落 `fetch('/api/...')`；
5. 后端错误统一映射到前端错误组件；
6. loading/empty/error/partial data 状态都要实现；
7. 不要用“有数据时很好看、接口慢了就崩”的 demo 写法；
8. 搜索结果类型改变必须由 OpenAPI generation 暴露，而不是运行时才发现。

开发环境可通过 Vite proxy / reverse proxy 对接，生产环境使用明确 `API_BASE_URL`。

---

# 十七、实验与 JiTuBench

创建 `experiments/`，与线上产品代码分离但复用核心算法库。

JiTuBench 不是简单图片分类集。单样本至少支持：

```text
source
image / page / optional region
context
function (CFR)
relation
positive
hard_negative
difficulty: Easy | Medium | Hard
verification
```

数据划分必须支持：

- Random split（仅诊断，不作为主要结论）；
- Book-disjoint split；
- Edition-disjoint split。

主要指标：

- Recall@K
- mAP
- nDCG@K
- local region hit / IoU（适用时）
- Evidence Precision / Recall / F1
- 查询耗时
- 人工核验耗时

必须单独报告 Hard 子集。

强基线至少包括：

- BM25/关键词全文检索；
- 通用视觉 embedding；
- 通用多模态 embedding；
- VLM 描述 -> text embedding；
- Qwen3-VL-Embedding/Reranker 或当前可用的同等级强基线；
- EAFR ablation：base / +CFR / +graph / +evidence / full。

不要挑弱 baseline 证明自己。

---

# 十八、反事实与泄漏测试

必须实现实验脚本验证模型是否靠版式作弊：

- 保留机械结构，替换/去除纸张背景；
- 保留机械结构，去除边框和非关键文字；
- 保留版式背景，遮挡主要机械结构；
- 将同一机械局部嵌入其他古籍版式。

记录 ranking delta / similarity delta。

目标不是“做一张漂亮热力图”，而是验证模型是否真的依赖技术结构。

---

# 十九、测试策略

至少包含：

## 后端单元测试

- 权重归一化；
- 缺失模态；
- cosine 数值边界；
- CFR 概率归一化；
- 不确定性熵计算；
- weighted Jaccard；
- evidence score；
- EAFR 总分；
- score component serialization；
- 坐标裁剪；
- provenance 校验；
- 权限/许可导出规则。

## API 测试

- 请求 schema；
- 成功响应；
- 404/422/模型不可用；
- 上传非法图片；
- 超大图片；
- 搜索结果 contract；
- 验证反馈。

## 前端测试

- OpenAPI client 类型检查；
- 搜索 loading/error/empty；
- 证据标签；
- region selection 坐标；
- compare view；
- API error mapping。

## E2E

至少跑通：

```text
打开古籍页
→ 框选区域
→ 发起 region search
→ 展示候选
→ 打开 compare
→ 查看证据
→ 标记“值得进一步比较/拒绝/争议”
```

测试环境不得依赖真实超大模型；使用固定 deterministic fake provider。另建 integration profile 对真实 provider 做少量烟测。

---

# 二十、性能与可观测性

PoC 阶段也要避免明显性能坑：

- 模型单例/lazy load；
- embedding batch；
- 缓存重复 query；
- 缩略图与原图分离；
- 不在 API 主线程重复加载模型；
- 数据库查询避免 N+1；
- 对 vector search 做 explain/benchmark；
- 记录 p50/p95 搜索耗时（有足够数据后）；
- 日志记录 query type、candidate count、rerank count、provider latency，但不泄露敏感输入。

---

# 二十一、代码质量标准

- Python 全部关键函数有类型标注；
- TypeScript 开启 strict；
- 不使用 `any` 逃避类型问题，除非第三方边界且有注释；
- 函数/类避免过长；
- 领域常量集中管理；
- 不在多个文件复制评分公式；
- 不在 React 组件里写算法；
- 不在 SQLAlchemy model 中堆业务服务逻辑；
- 不把 notebook 代码直接复制进生产服务；
- notebook/experiment 与 production library 共享测试过的核心函数；
- 所有公开函数/复杂算法有简短 docstring，说明输入、输出、边界，而不是重复代码本身；
- README 中必须有一键启动步骤和最小示例；
- 提交前运行 lint、typecheck、unit tests、contract tests。

---

# 二十二、安全与可靠性

虽然这是研究项目，也必须保证基础安全：

- `.env` 不提交；
- 提供 `.env.example`；
- 文件上传做 MIME/魔数/尺寸验证；
- 防止 path traversal；
- 禁止任意 shell 命令拼接用户输入；
- CORS 白名单化；
- 生产关闭 debug；
- 数据库使用 ORM/参数化查询；
- 限制上传/查询大小；
- 对可能暴露版权受限原图的接口根据许可控制；
- 日志不写 API Key、授权 cookie 或原始敏感文件。

---

# 二十三、分阶段实施计划

不要一次性实现全部系统。按以下阶段推进，每阶段结束都必须：更新 `.tuji`、运行测试、给出可复现命令。

## Phase 0：仓库审计与记忆初始化

完成：

- 阅读项目论文和现有代码；
- 初始化 `.tuji`；
- 输出当前架构图和风险；
- 检查 Python/Node/Postgres/模型环境；
- 不做大规模业务编码。

验收：`.tuji/STATE.md` 能让另一个 AI 在 5 分钟内理解当前项目。

## Phase 1：工程骨架与 API 契约

完成：

- backend/frontend 可启动；
- PostgreSQL migration；
- health/capabilities；
- OpenAPI -> TS client 自动生成；
- CI/质量脚本；
- 基础错误格式。

验收：前后端通过生成 client 完成一次 health 请求，无手写重复 DTO。

## Phase 2：领域数据模型与 ingestion

完成：

- Book/Edition/Page/Figure/TextChunk/Evidence 等；
- provenance；
- manifest 导入；
- 图像区域和文本关联；
- 数据校验。

验收：用一小批合法样例完成可重复导入，并能查回完整来源链。

## Phase 3：强 baseline 检索

完成：

- embedding provider；
- vector index；
- text/image/region 三类 query；
- score components；
- 基础 API。

验收：不依赖 CFR 已可真实搜索，结果来自数据库/索引而非硬编码。

## Phase 4：CFR / EAFR

完成：

- CFR 数据结构；
- uncertainty；
- graph similarity；
- evidence score；
- EAFR reranking；
- ablation config。

验收：所有公式有单元测试；同一候选可解释地输出各分项得分。

## Phase 5：研究工作台前端

完成：

- library/page/search/compare；
- 框选即搜；
- 证据卡；
- Observed/Documented/Inferred/Verified；
- 用户友好错误状态。

验收：通过 E2E 完整走通“框选→搜索→对照→人工核验”。

## Phase 6：实验框架与 Kill Gate

完成：

- JiTuBench schema；
- Book/Edition disjoint；
- 强 baseline；
- Hard subset；
- 反事实测试；
- 自动指标报告。

验收：真实指标可由一条命令重复生成，实验配置和结果写入 `.tuji/EXPERIMENTS.md`。

## Phase 7：可靠性与比赛交付

完成：

- 性能优化；
- 安全检查；
- 文档；
- Docker/部署；
- 演示数据；
- 比赛截图/演示流程所需稳定版本。

验收：新机器按 README 可启动；核心 Demo 不依赖开发者手工改数据库。

---

# 二十四、Kill Gate（编码过程中必须执行）

## Data Gate

若无法形成多部文献、多个功能族及足够 Medium/Hard 的真实跨书关联，不继续做复杂训练；转为描述性数据/基准与证据工作流。

## Model Gate

如果强通用模型在 Hard 子集已接近人工可用上限，不强行“造一个新模型”。保留系统，算法重点转向：基准、证据工作流、模型边界分析、人工核验效率。

## Value Gate

真实任务中若不能降低查找/核验时间，也不能提高有效线索发现率，就停止“高价值研究工具”的产品化叙事，重新审视任务。

Kill Gate 的实际结论必须写入 `.tuji/DECISIONS.md` 和 `.tuji/EXPERIMENTS.md`，不能只口头讨论。

---

# 二十五、每次长任务结束时的强制输出

在结束当前 Codex 工作会话前，必须完成：

1. 更新 `.tuji/STATE.md`；
2. 更新 `.tuji/TASKS.md`；
3. 如有架构/算法选择，更新 `.tuji/DECISIONS.md`；
4. 如有实验，更新 `.tuji/EXPERIMENTS.md`；
5. 更新 `.tuji/HANDOFF.md`；
6. 运行并记录实际执行的 lint/typecheck/test 命令与结果；
7. 列出真实已知问题，不得写“全部完成”掩盖失败项。

`HANDOFF.md` 至少包含：

```text
当前阶段：
当前分支/commit：
可运行状态：
本轮完成：
关键改动文件：
数据库 migration：
API 变更：
测试结果：
未解决问题：
下一步第一动作：
启动命令：
```

---

# 二十六、首次执行指令

收到本主提示词后，**不要直接开始写几千行代码**。

首次执行必须按顺序做：

1. 检查仓库根目录、现有代码和配置；
2. 阅读项目论文/需求文档；
3. 读取或初始化 `.tuji`；
4. 输出简短的“现状审计 + Phase 0 计划”；
5. 初始化最小工程质量工具；
6. 完成 Phase 0；
7. 如果 Phase 0 没有阻塞，继续 Phase 1，不需要因为任务长而停下来等待确认；
8. 每个 Phase 结束做测试和 `.tuji` 记录；
9. 除非遇到真正无法自主判断的阻塞，否则持续推进到当前环境能可靠完成的最远阶段。

不要用“任务太大，建议分几次完成”作为停止理由。任务本来就允许长时间和分步执行。你应自己管理阶段、上下文和交接记录，在不牺牲质量的前提下持续工作。

最终目标不是代码量最大，而是：**真实数据可追溯、算法可验证、API 契约稳定、前端表达严谨、后端功能可靠、实验可重复、后续 AI 可以无损接手。**
