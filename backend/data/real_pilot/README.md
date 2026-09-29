# V1.1-B 真实古籍试点

本目录保存可版本化的来源与许可元数据。原始 PDF 下载到
`backend/data/assets/real_pilot_v1/`，该目录受项目 `.gitignore` 保护，不随 Git 提交。

当前来源均通过 Wikimedia Commons 官方 MediaWiki API 核验，Commons 文件元数据显示：

- `LicenseShortName`: `Public domain`
- `UsageTerms`: `Public domain`
- `AttributionRequired`: `false`
- `Restrictions`: 空

数字文件权利状态以抓取日期的 Commons 文件页为依据。对外发布数据包前仍应重新检查文件页，
并保留来源链接、抓取时间和哈希。不要仅根据古籍作者年代推断数字扫描件许可。

## 下载与校验

在项目根目录执行：

```powershell
python backend/scripts/download_real_pilot.py
```

脚本只接受登记在 `sources.json` 中、位于 `upload.wikimedia.org` 的 HTTPS PDF，验证
PDF 魔数、字节数、Commons SHA-1 和本地 SHA-256。重复执行会校验现有文件，不重复下载。

## 试点选择

- 《天工开物 2》共 28 页，作为第一批 20-50 页 OCR/版面标注试点。
- 《农政全书 1》共 79 页，作为第二来源保留；完成逐页图像审查后再选择技术图页面。

两个文件都是真实馆藏扫描，但当前尚未完成 OCR、页面标注或检索效果评估；
`evaluation_status` 必须保持为 `not_evaluated`。

## 页面准备

使用 Poppler 将首批来源渲染为可标注 PNG，并生成可追溯库存：

```powershell
python backend/scripts/prepare_real_pilot.py
```

默认只处理 `pilot_selection=primary_all_28_pages` 的《天工开物》第二册；可用 `--source-id` 指定来源或 `--all-sources` 渲染两份 PDF。脚本校验 PDF 字节数、SHA-256、页数和渲染页数后，输出 `derived_pages.json`。页面的版面和 OCR 字段保持 pending，不生成任何虚构文本或历史标签。

`annotation_schema.json` 是人工标注模板，要求保留 layout 区域、阅读顺序、raw OCR、corrected text、行坐标、置信度、输入哈希和修改轨迹。未安装 PaddleOCR 时，后端的可选 Provider 明确返回 `MODEL_UNAVAILABLE`。

Docker 构建默认排除 `data/assets/real_pilot_v1/` 和 `data/processed/real_pilot_v1/`，原始扫描和渲染图仅保留在本地受控目录。
