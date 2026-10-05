# 数据与许可

2026-10-05 V1.2恢复：已冻结允许再分发的2来源原PDF、8选中扫描/AI副本、原库存/raw OCR/manifest与88基线/神经向量，共24文件，包48,587,383字节/SHA256 e108e27390b3b1200e7eeb314a2905e38ff609061bba8f58b67a725de8d1080e。release/domestic-data.lock.json逐文件锁；独立恢复包与模型分开，不含.env、密钥、审核者身份、会话/核验记录。许可按登记来源原记录保留，水印不移除。

V2功能背景覆盖12图45建议/27unknown/10关系；实际查看contact sheet后形成AI草稿，保留unknown/null，不虚构古文或人审。真实线上35文本Inferred，corrected/功能/关系/核验仍0。

2026-10-05固定对照：新增backend/data/experiments中的24开发查询与4图AI功能/关系方案；不改变原始PDF/扫描/raw/业务文字/人工轨迹。运行产物绑定manifest、DB文本/证据/来源/状态、扫描与向量内容、模型空间及实现哈希，独立目录Git/Docker忽略。4图20功能+4unknown+10关系全部Inferred/confidence=null；扫描支持Observed、AI文本引用Inferred，无古文正文真值/qrels或历史Verified。国内出版与馆藏类别保持。

2026-10-05模型增量：真实语料原12图/14区域/35文本/59证据及8扫描内容不改，原PDF/raw/用户审核草稿保持；真实corrected/人工核验仍0。新增的神经向量为21图*3+32局部=95（真实与合成均含），与原74基线并存。BGE与Chinese-CLIP保存固定revision/预处理hash，完整文件锁与依赖锁在backend/model_runtime；权重存于D:/codex-models，真实运行报告不进Git/镜像。国内出版与国图馆藏、Commons获取渠道继续区分；模型许可与扫描许可不互相替代。

2026-10-05当前：国内《耕织图》5扫描/8图优先、国图《天工开物》3扫描/4图补充，
共同12图/14AI区域/35Inferred文本/65局部raw行/59证据/38向量已导入。
AI manifest sha256=7752ab965597de901ead44541006786a6c45012e1d96948f77d0cf1cd83d34f6；
选页domestic_ai_selection.json；导出8b4defa06141f66e按registry/inventory/raw/selection指纹寻址。
Commons获取渠道与国内出版/馆藏类型分开记录。原NLC水印保持，许可不扩展到现代编辑设计。
原始PDF/扫描/raw/Label/Cache/旧AI导出不覆盖；PNG副本只读挂载，输出和真实资产不入Git/镜像。
AI不是人工真值；corrected_text=null，研究not_evaluated。以下保留历史登记。


2026-10-03 已补充3个中国古籍扫描，共100页，来源库现在5个PDF/207页/3部古籍。
国图《天工开物》45页SHA-256 `32dafd49217b5fb460fe2dd2a5cd01defb0786ac5bb509bde95aff2a80175106`；
国内出版来源《耕织图》27页 `4542fff8470bfcb5137d238b3f3628a704d6c43dc862e9cc2d6b7a1b9dbd866b`；
Harvard《御制耕织图》28页 `d0f6686cf59979d61b94b16cec876cdaf12fd85118a2fe02db718a4249103fdb`。
国图水印保留；现代影印来源、原版目录断代和实际馆藏分开记载，中华再造善本原底本馆藏不推断。
新增页面为独立库存，原28页未变。全量PDF/PNG/检查图/候选/人工导出/评测报告/快照均不提交Git
且不进入默认Docker。来源完整性已核实，逐字转录和功能关联真值仍待人工；以下为历史登记。

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

## 2026-10-04 补充机器产物和业务转换

国图《天工开物》22—27页和中华再造善本《耕织图》21—26页的12页raw OCR已写入独立
supplementary_ocr_results.json，逐页input hash/Provider模型版本/预处理和结果完整性指纹均保留；
输出257框/830字符（含换行），不是人工转录真值，扫描水印保留。原28页inventory哈希仍为
c5cd13fe5a68de742d05b7effb0698bbb6a13f405493b768df48518797a255c1。

真实导出格式以完整人工scope和快照为门，保留原PDF/扫描/来源登记/候选/人工导出/annotation/
scope哈希、审阅身份时间、图题bbox与raw/corrected轨迹。只导入确认图区/图题，不凭机器类别
造功能三元组/相关性标签，不把转录确认变成历史Verified。默认容器不挂载raw扫描/复核草稿。
当前真值0/6、实际导出0图；PG测试模拟输入是工程测试，不是来源资料和评测真值。
