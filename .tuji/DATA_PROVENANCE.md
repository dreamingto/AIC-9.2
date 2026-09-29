# 数据与许可

V1 fixture 使用 3 个合成来源和 9 个确定性生成 PNG。每个来源、版本、页面、图和资源都保留来源 URL、来源名、书名、版本、卷次、页叶、许可证、抓取时间、SHA-256、原始路径和 pipeline 版本等字段。

fixture 的许可证状态为 `synthetic_fixture`，只用于工程流程验证。来源 A/B 的 6 个资源允许演示分发；来源 C 的 3 个资源明确设置 `allow_redistribution=false`，专用于验证许可受限路径。资源公开接口统一检查该字段，禁止通过 API 绕过许可限制。

# V1.1-B 真实来源登记

2026-09-04 通过 Wikimedia Commons 官方 MediaWiki API 核验并下载两份真实扫描：

| source_id | 作品 | 页数 | 本地文件 | SHA-256 | 权利元数据 |
|---|---|---:|---|---|---|
| `commons-najda-tiangong-kaiwu-2` | 《天工開物》第二册 | 28 | `tiangong-kaiwu-vol2-najda.pdf` | `084fbb36535699abfc7429ca3cad88f13dac4ab1ec9fb815212a9427d2e3b835` | Commons `Public domain`，无署名要求，限制字段为空 |
| `commons-najda-nongzheng-quanshu-1` | 《農政全書》第一册 | 79 | `nongzheng-quanshu-vol1-najda.pdf` | `327c103a99f7ecc2e92cd5fcdcdf5045c7b2cbb20fd3985e877f41732b6f4aba` | Commons `Public domain`，无署名要求，限制字段为空 |

原始文件位于 `backend/data/assets/real_pilot_v1/`，被 `.gitignore` 忽略。首批《天工开物》28 页已由 Poppler 渲染并在 `backend/data/real_pilot/derived_pages.json` 登记页面哈希；PNG 位于被忽略的 `backend/data/processed/real_pilot_v1/`。当前仍未完成 OCR、人工标注、数据库导入或真实指标评估，`evaluation_status=not_evaluated`。

`Public domain` 是抓取时 Commons 文件页的元数据状态，不自动等同于所有司法辖区的训练或再分发许可。对外发布前必须重新检查文件页和目标法域要求。
