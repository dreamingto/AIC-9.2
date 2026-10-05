# 独立中文检索模型服务

本目录是宿主机的可选推理服务，业务 FastAPI 镜像不安装 PyTorch。模型目录默认
`D:\codex-models\jitu-retrieval`，运行环境为 `D:\codex-runtime\jitu-retrieval`。
OCR 的 PaddleOCR 环境与后端 `.venv` 保持独立。

固定模型：

| 用途 | 模型 | 版本 | 输出 |
|---|---|---|---|
| 中文文本语义检索 | BAAI/bge-small-zh-v1.5 | 7999e1d3359715c523056ef9478215996d62a620 | 512 维 |
| 视觉、局部、中文图文检索 | OFA-Sys/chinese-clip-vit-base-patch16 | 36e679e65c2a2fead755ae21162091293ad37834 | 512 维 |

模型依据官方发布记录选择；下载可通过国内镜像，仍校验固定 revision、LFS SHA256
和普通配置文件的 Git blob SHA1。`models.lock.json` 保存文件 SHA256 与字节数。
Worker 每次启动复核这些文件，`local_files_only=True`、离线模式及
`trust_remote_code=False` 防止运行时下载或执行模型仓库代码。

初次准备，在仓库根目录执行：

```powershell
backend\.venv\Scripts\python.exe -m venv D:\codex-runtime\jitu-retrieval
D:\codex-runtime\jitu-retrieval\Scripts\python.exe -m pip install torch==2.7.1 --index-url https://download.pytorch.org/whl/cu128 --timeout 180
D:\codex-runtime\jitu-retrieval\Scripts\python.exe -m pip install -r backend/model_runtime/requirements.lock
cd backend
.venv\Scripts\python.exe -m model_runtime.download
cd ..
```

支持 downloader 的 `--root`、`--endpoint`、`--proxy`；代理只在实际监听时指定。
模型文件不放入 Git，不打入镜像。BGE 发布页列为 MIT；Chinese-CLIP 项目发布
[MIT 声明](https://github.com/OFA-Sys/Chinese-CLIP/blob/master/MIT-LICENSE.txt)，
使用和引用时保留上游声明；这与古籍扫描的来源/再分发许可分别管理。

每次启动：

```powershell
.\backend\model_runtime\start.ps1
docker compose -f docker-compose.yml -f docker-compose.ai-real.yml -f docker-compose.neural.yml up --build -d
```

GPU 默认由 Torch 检测，也可 `start.ps1 -Device cpu` / `-Device cuda`。
启动日志在 `D:\codex-runtime\jitu-retrieval\logs`；健康接口
`http://127.0.0.1:8767/health` 返回设备、Torch 版本和模型文件锁的哈希。
Worker 监听 8767 供本机 Docker 访问，仅用于本地受控演示，无账号服务。

完成数据库迁移、国内语料导入后建立索引，在 `backend` 目录：

```powershell
.venv\Scripts\python.exe -m scripts.reindex_retrieval --profile neural --output data/real_pilot/model_retrieval/neural-index.json
.venv\Scripts\python.exe -m scripts.smoke_neural_retrieval --output data/real_pilot/model_retrieval/neural-smoke.json
```

重建仅在事务中写所选模型的向量，不修改古籍、AI 文本、人工校订或核验。
基线 256 维与神经 512 维向量同时保留；匹配必须满足 Provider、模型、版本、维度、
预处理哈希一致。缺少兼容索引或推理服务时返回 `MODEL_UNAVAILABLE`，没有静默回退。
需要显式使用基线时，去掉 `docker-compose.neural.yml`，仍保留 `ai-real` 资产挂载。

中文 BGE 使用 CLS、L2、最多 512 tokens；检索 query 添加官方中文 instruction，
文档不添加。Chinese-CLIP 文本最多 52 tokens，图像先以 Lanczos 等比例缩至
最长边不超过 1536 以限制传输体积，再执行官方 224 像素处理与 L2。
均为 float32/eval/inference_mode，CUDA 禁用 TF32并请求确定性算法；不保证不同
硬件/库版本之间逐位相同。向量维度相同也不能将 BGE 与 Chinese-CLIP 直接比较。

这些是通用中文预训练模型，没有在古籍图像上微调；三模态实际排名仅为演示观察。
没有独立标注时 CER、WER、图题召回率、Recall/nDCG 等研究指标保持 `not_evaluated`。
