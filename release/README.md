# 冻结国内数据与恢复流程

使用当前仓库源码，搭配 [V1.2.0 固定数据资产](https://github.com/dreamingto/AIC-9.2/releases/tag/v1.2.0-competition-preview) 的 `jitu-domestic-34033a592c974cd7.zip`，执行下方恢复步骤。数据包身份及逐文件摘要以 [domestic-data.lock.json](domestic-data.lock.json) 为准。

参与来源、模型、协议和实现哈希的文件通过 `.gitattributes` 保留原字节，不应擅自转换换行。重新生成来源库存、OCR 或模型向量会产生新输入身份，应使用新报告范围。

源码与锁文件在Git；原始扫描、OCR、模型权重及运行报告独立管理。当前输入包不包含.env、审核者身份、访问密钥、模型权重、搜索记录或核验记录。

当前数据包：`jitu-domestic-34033a592c974cd7.zip`，48,587,383字节；SHA256与逐文件校验在[domestic-data.lock.json](domestic-data.lock.json)。本机保存于`D:/codex-releases/AIC-9.2/`。包含两个允许再分发来源的原PDF、8个选中扫描/备份、原库存/raw OCR、冻结manifest及88个基线/神经向量。AI文本、功能建议仍Inferred，研究指标not_evaluated。

在新的源码目录先创建Python3.12开发环境（不要安装到模型或OCR环境）：

```powershell
py -3.12 -m venv backend/.venv
backend/.venv/Scripts/python.exe -m pip install -e './backend[dev]'
backend/.venv/Scripts/python.exe -m pip check
Copy-Item .env.example .env
```

依赖锁`backend/requirements.lock`面向Linux容器。Windows开发环境按pyproject安装；模型与OCR各有独立Windows依赖锁。

在backend目录恢复数据，`--root`默认指当前项目根目录。程序先校验整包及所有目标；文件不一致时拒绝覆盖，不使用未检查的Zip解压路径：

```powershell
.venv/Scripts/python.exe -m scripts.release_bundle restore --bundle D:/codex-releases/AIC-9.2/jitu-domestic-34033a592c974cd7.zip
```

在根目录运行国内真实基线版并导入manifest：

```powershell
./scripts/start.ps1 -Profile real
$body = '{"manifest_name":"ai-real-domestic-8b4defa06141f66e.json","dry_run":false}'
$job = Invoke-RestMethod -Method Post -Uri http://localhost:8000/api/v1/ingestion/jobs -ContentType application/json -Body $body
Invoke-RestMethod ('http://localhost:8000/api/v1/ingestion/jobs/' + $job.id)
```

等待任务completed。然后在backend目录导入冻结的模型向量：

```powershell
.venv/Scripts/python.exe -m scripts.release_bundle import-vectors
```

导入器校验锁、manifest、实体范围、模型版本、预处理、模态和数值，只写入对应向量，不改变扫描、文本或核验。若自行重建模型索引，则建立新实验版本；不同硬件的向量不保证逐位相同。

按[模型运行说明](../backend/model_runtime/README.md)下载/校验权重和安装独立环境，再启动神经版：

```powershell
./scripts/start.ps1 -Profile neural
```

`http://localhost/demo`应显示两个就绪案例。在backend目录执行默认V2比较：

```powershell
.venv/Scripts/python.exe -X utf8 -m scripts.run_domestic_comparison
```

V1输入与报告保留；V2保持24个查询和相同语料，扩展全部12图的有据AI草稿并修正局部证据范围，不称为独立测试集。权重通过`EAFR_WEIGHTS` JSON配置，变化产生新的实现/输入报告身份。

原扫描发布依据冻结登记的许可字段和来源URL，保留水印及出处。没有数据包时只能复现synthetic工程版，不能声称恢复了固定国内实验。原有库存和raw OCR带时间戳，因此从PDF重新渲染/OCR会创建新指纹。

如果本机到 github.com 的连接受阻，可用资产 API 下载（不需凭据）；下载慢时 curl 的 `-C -` 可以续传，下载完成再校验 SHA256，不能把 partial 文件用于恢复：

```powershell
curl.exe --noproxy '*' -fL -H 'Accept: application/octet-stream' -o jitu-domestic-34033a592c974cd7.zip https://api.github.com/repos/dreamingto/AIC-9.2/releases/assets/612484183
Get-FileHash jitu-domestic-34033a592c974cd7.zip -Algorithm SHA256
```
