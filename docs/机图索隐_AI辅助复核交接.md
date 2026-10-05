# 机图索隐 AI 辅助扫描复核交接

## 当前比赛路线变更（2026-10-05）

用户明确要求优先国内出版，比赛阶段暂不人工审核。当前不需要操作旧人工复核页。
独立AI真实通道已导入《耕织图》8图及国图《天工开物》4图，三类搜索与浏览器验证通过；
正式真值/历史Verified未被AI建议替代。详见[国内古籍AI比赛演示](机图索隐_国内古籍AI比赛演示.md)。
以下人工复核交接作为历史/后续可选工作流保留。

## 第二轮最新结果（2026-10-05）

当前目录内实际UI导出为`ai-assisted-review-overrides.round2.json`，SHA-256：
`d71b571a002d423f59c5092fe7c56a35aef98ef1257e8bb60e5c29033f34d5f2`。
113项全部AI checked；16项读序重检完成，文字留空从11减至6，13个未知项继续保留。
旧导出/种子/候选/原OCR保持，round2.audit记录逐项未决依据。

第10页b028拟棍做成如，b029并回尾字也，b030单列若晴光又風色則不用火，b012补回以竹；
b005改拟竹头簷及宇，磨不/磨木保留争议。第16页b009拟的杠，第18页b002拟何擬當。
所有结果仍ai_assisted/inferred/待确认，不是独立人工真值。留空项为p0010-b022、
p0016-b011和p0018-b025/b029/b012/b024。

已生成7图/10指定正文框/6有引用功能草稿/2案例，目录`evidence-drafts-971fb3e505444829`。
人工接纳/冻结/导出仍实际退出2，没有人工annotation、研究快照或真实业务manifest，
CER/WER/图题召回与检索指标未评测。修复旧图片加载回调覆写裁剪，人工页绑定round2而不预填确认。
新版URL加`?review_round=2`避免旧缓存，入口与生成命令见[下一阶段执行计划](机图索隐_下一阶段执行计划.md)。
177测试通过/1独立PG跳过，compileall/Ruff/Mypy69源文件通过；Browser核查预览和人工0/543隔离。

下面97已检查、11留空等说明为第二轮之前的版本历史。

更新日期：2026-10-05。扫描检查于 2026-10-04 完成，范围为《天工开物》第二册原 PDF 第 10、12、14、16、18、22 页。此次通过 Codex 应用内 Browser 逐项检查扫描裁剪与整页图；结果是 AI 建议，不是独立人工评测真值。

## 当前使用的补框版本（2026-10-05）

当前目录为 `backend/data/real_pilot/review_revisions/supplements-v2-c4a07f9b9be9`，
`review_revisions/active_revision.json` 指向该版本。其他哈希目录是保留的准备草稿，不能按
目录名排序选取“最新”。旧 109 项候选、Label、Cache、原人工页/草稿及旧 AI 导出均保留。

核心范围仍为 6 页，现在是 **113 项 = 101 原 OCR 框 + 4 补框区域 + 7 图区 + 1 补框图题**。
全队列为 543 项，覆盖其他页并不表示都已检查。109 项旧建议已迁移，4 个新框已检查；
第 10 页补框使 16 项序号变化，对应 AI 检查状态已撤销。当前 AI 页显示 97 已检查，
其余 16 项仍保留文字/备注，待重新核对顺序。独立人工确认依然是 0。

| 新框 | 用途 | 扫描复核后的状态 |
| --- | --- | --- |
| p0010-b027 | 右页漏列，然後至斷絕之時 | 保存正文建议；迄/浣、于/干等字仍待判定 |
| p0010-b028 | 右页正文上方小字右列 | 扩正左边界至 x=.591、width=.021；首字偏旁不确定，转录留空 |
| p0010-b029 | 左页如風…出水乾大字列 | 保存正文建议；末部似也的字是否应并回正文仍待确认 |
| p0010-b030 | 左页漏列末部小字及尾字 | 保留完整可见字形；小字首字、双行顺序及与正文的边界仍待裁决，转录留空 |

新增区域的 `original_box_index=null`、`raw_text=null`、`server_ocr=null`，明确表示原预测中
没有该框。接纳器将人工确认后的补框追加到版面/corrected/change_log，保留 raw OCR 不变。
新框必须参加全页完整性确认；保留原框 CER/WER 排除补框，并另报排除数量，不能称为整页
端到端准确率。若补框后还发现缺项，继续新版本处理，不能直接勾选完整。

新人工页展示所有 113 项 AI 建议与备注，可点击“采用 AI 建议并重新确认”，随后逐字、类别、
边界和读序对照扫描。采用建议不会勾确认，不写人工结果文件；两种整页确认也保持未选。
11 项文字/旁注转录留空（旧 9 项及新 b028/b030），13 个原未知项仍待裁决；非空建议同样需复核。

- [新版人工复核页](http://127.0.0.1:8766/review_revisions/supplements-v2-c4a07f9b9be9/model_review_queue.html)
- [新版 AI 复核页](http://127.0.0.1:8766/review_revisions/supplements-v2-c4a07f9b9be9/model_review_queue.ai.html)
- 新目录中的 `ai-review-seed.json` 是可重复生成的迁移种子，`ai-assisted-review-overrides.json` 是实际 UI 导出，不能互相覆盖。
- `ai-assisted-review-overrides.audit.json` 记录 113 项、97 AI 检查、16 顺序重检、11 留空文字和 0/6 人工真值。

### 接纳与评测命令

在新人工页面完成真实确认并导出后，将文件保存到新目录的
`historical-review-overrides.json`，不要覆盖旧目录的确认文件。下面命令只在真实人工完成后执行：

```powershell
cd D:\codex-project\比赛\9.2\backend
$reviewVersion = 'data/real_pilot/review_revisions/supplements-v2-c4a07f9b9be9'
.\.venv\Scripts\python.exe -X utf8 -m scripts.convert_ppocrlabel_annotations `
  --accept-file-state --reviewer <实际复核人> `
  --candidate "$reviewVersion/annotations.candidates.json" `
  --review-overrides "$reviewVersion/historical-review-overrides.json" `
  --output "$reviewVersion/annotations.human-reviewed.json"
.\.venv\Scripts\python.exe -X utf8 -m scripts.evaluate_competition_ocr --freeze `
  --candidate "$reviewVersion/annotations.candidates.json" `
  --scope "$reviewVersion/competition_scope.json" `
  --annotation "$reviewVersion/annotations.human-reviewed.json" `
  --overrides "$reviewVersion/historical-review-overrides.json" `
  --report "$reviewVersion/competition_evaluation.json"
.\.venv\Scripts\python.exe -X utf8 -m scripts.export_reviewed_real_manifest `
  --manifest-name reviewed-real-core-v2.json `
  --candidate "$reviewVersion/annotations.candidates.json" `
  --scope "$reviewVersion/competition_scope.json" `
  --annotation "$reviewVersion/annotations.human-reviewed.json" `
  --overrides "$reviewVersion/historical-review-overrides.json" `
  --evaluation-report "$reviewVersion/competition_evaluation.json" `
  --report "$reviewVersion/real_export_report.json"
```

实际当前接纳 AI 文件、冻结和真实导出均退出 2；0/6 人工就绪、metrics=null、导出0图。
没有真实评测快照或业务 manifest。全量后端 158 passed/1 独立 PG skipped，Ruff/编译/Mypy
68 源文件通过；两个既有上游警告。新页面已在应用内 Browser 验证扫描与建议可见、
采用建议后确认仍为 false。三服务保持 healthy，本轮未重建镜像/重跑业务 E2E/commit/push。

## 上一轮已完成的 109 项扫描检查

| PDF 页 | 已检查候选 | 内容 |
| --- | ---: | --- |
| 10 | 26 | 治絲、調絲正文、章节标题、夹注与版心 |
| 12 | 11 | 山箔圖、治絲圖、标签与两个图区 |
| 14 | 12 | 溜眼、經耙、掌扇、标签与两个图区 |
| 16 | 21 | 花機圖、跨页图区、部件与图内说明 |
| 18 | 32 | 腰機式、花本正文、章节标题与夹注 |
| 22 | 7 | 趕棉、彈棉、烘火、两个图区及漏检标题补框 |
| 合计 | 109 | 101 个原框、7 个图区、1 个补框图题 |

109 项均已保存 AI 检查依据。50 个原 OCR 框提出了不同于 raw 的非空转录；这只是修改统计，不是准确率。所有原框顺序在各页内仍为完整、不重复的排列，但阅读顺序和清单完整性没有勾选为已确认。

当前建议分类为正文 32、图题/部件/图内说明 29、旁注 28、图区 7、未知 13。7 个图题角色与 4 个章节标题角色分开，避免将治絲、調絲、腰機式、花本计入插图标题。

## 可定位的修订例子

| 项目 | 原输出或原问题 | AI 对照扫描后的建议 |
| --- | --- | --- |
| p0022-f01-title | 原补框偏到树叶/屋顶 | 移到 `x=.71, y=.24, width=.07, height=.05`，拟录趕棉；棉/綿仍待人工裁定 |
| p0022-b002 | 棉彈 | 按横排方向拟录彈棉 |
| p0012-b003 / b002 | 圖箔山 / 圖絲治 | 山箔圖 / 治絲圖 |
| p0014-b002 | 眼溜 | 溜眼 |
| p0014-b010 | 三位 | 叶码三五 |
| p0016-b004 | 然 | 鐵鈴 |
| p0016-b013 | 雨脚 | 兩脚，保留印本脚字形 |
| p0016-b017 | HAPA | 一排悬垂构件，不是文字；建议 `unknown / illustration_false_positive` |
| p0018-b016 | 漏首字、误识末量词 | 首寬、末觔等按印本拟录；不直接替换成参考版的斤 |
| p0018-b020 | 受控建议結花本 | 扫描只有花本，不能凭词表添結 |

其他改动和逐项不确定点见本地 JSON 的 `review_note`。模型共识、参考对齐置信度及上述 AI 转录均不能升级为历史主张 `Verified`。

## 尚未解决的内容

13 项被建议归为未知：5 个图线误检、1 个版心残迹、5 个旁注碎片、2 个字形碎片。是否剔除、扩框或合并仍由人工判断；没有删除 Cache、Label 或扫描。

另外 9 个文字/旁注项有检查备注但 `corrected_text=null`，须人工裁决：

- p0010-b002：上栏三字小注中间字难辨。
- p0010-b022：片假名旁注不完整。
- p0016-b011、p0016-b009：横排标签字形/读序不够确定。
- p0018-b002：上栏小注末字被原框裁断。
- p0018-b025、p0018-b029、p0018-b012、p0018-b024：片假名旁注不完整或边界可疑。

以上只是最明确的留空项；非空建议中仍有棉/綿、蘭/繭、木/不、衝、登/疊等待判字。不能只确认留空项而自动接纳其他记录。

第 10 页发现至少两处现有候选未覆盖的正文区域，已用动态裁剪检查，不修改旧候选 ID：

- 右页约 `x=.574, y=.295, width=.034, height=.570`：从然後开始、到斷絕之時结束的大字列；上方还需拆清小字夹注。
- 左页约 `x=.216, y=.178, width=.034, height=.690`：如風時轉轉火意照乾是曰出水乾一列及末部小字说明；须分开正文与夹注。

坐标是补框定位建议。需要在新的标注副本中补框、核对读序，并建立新候选/范围版本；原 109 项和原候选哈希保留，不能直接覆盖 Label 导致已有草稿失配。第 16 等页的版心叶码也需要在完整清单检查中重新核对。

## 产物与使用方式

- AI 检查页：`http://127.0.0.1:8766/model_review_queue.ai.html`，独立草稿空间，可查看逐项备注和编辑框的实时裁剪。
- 原人工确认页：`backend/data/real_pilot/model_review_queue.html`；原用户标签页和人工草稿保留。
- 已保存导出：`backend/data/real_pilot/ai-assisted-review-overrides.json`。
- 定位/统计报告：`backend/data/real_pilot/ai-assisted-review-overrides.audit.json`。

AI 导出的每项包含原 raw、原框、原顺序、建议文字/框/顺序、复核备注和时间。`confirmed=true` 只表示 AI 已检查；每项仍为 `review_origin=ai_assisted`、`verification_state=inferred`、`evidence=scan_level_ai_review`、`requires_human_confirmation=true`。

文件与真实扫描均为本地受控产物，不提交 Git，也不进入默认 Docker 镜像。原 inventory、Label 和机器候选哈希已再次核对，均未改变。

## 正式评测门

当前独立人工转录就绪仍为 **0/6 页**，CER、WER、图题召回率及检索指标继续 `not_evaluated`。AI 文件不得改名或改字段后作为人工导出提交。

接纳器同时检查文件种类、文件级来源、记录级来源和待人工标记；即使将 AI 文件的顶层名称改成人工类型，仍会拒绝声明为 AI 或待人工的记录，并保留已有输出。

下一步先补齐漏框与夹注边界，再由人工逐项核对这些具体建议、确认全页顺序和完整清单。通过同一来源/哈希质量门后，才运行已有冻结、OCR 评测与真实导入流程。

## 2026-10-05 收尾验证

修复 `python -m scripts.convert_ppocrlabel_annotations` 对复核异常的捕获：原入口作为
`__main__` 运行，而接纳器按包名导入转换器，形成了两个不同的 `ConversionError` 类。
现在由 `scripts.annotation_errors` 提供共享异常；原转换器仍导出该名称，保持其他脚本兼容。
新增两个隔离项目 subprocess 测试，真实运行 `-m` 入口，验证 AI 拒绝时退出 2、没有 traceback、
不会创建人工结果，而且已有结果字节保持不变。

- `compileall`、Ruff 通过；Mypy 检查 67 个源文件通过。
- 全量 Pytest：149 passed、1 skipped、2 个既有上游弃用警告。跳过项为未配置独立测试数据库的 PostgreSQL 集成，本轮没有重跑该项。
- 实际 AI 导出接纳命令明确拒绝、退出 2；`annotations.human-reviewed.json` 和 `historical-review-overrides.json` 均不存在。
- 实际 `evaluate_competition_ocr --freeze`：0/6 页就绪、`metrics=null`、`not_evaluated`、`blocked_pending_human_truth`、退出 2。
- 已核对保存的 109 条记录均为 AI / Inferred / 待人工；两类整页确认清单均为空。原 candidate、inventory、Label SHA-256 与导出绑定值相符。
- 今天原服务停止，已启动现有 Docker 三服务和仅绑定 `127.0.0.1:8766` 的复核静态服务。三服务均 healthy，前端、后端健康、原人工页及 AI 页均 HTTP 200；数据库实际计数仍为 3 书、9 图、18 区域。
- 重新连接应用内 Browser，页面恢复显示 AI 已检查 109/539，保存的文字/备注和扫描裁剪可见；用户原人工页保留。

本轮未重建镜像，未重跑前端测试或业务端到端测试，未 commit/push。真实扫描、修订导出、
裁剪和审计仍在 Git/Docker 忽略范围内。服务地址是本地运行入口，电脑重启后需重新启动。
