机图索隐 V1.2 国内古籍可复现比赛预审版。

**源码已由 [V1.2.1 修复版](https://github.com/dreamingto/AIC-9.2/releases/tag/v1.2.1-competition-preview) 取代。** 请下载该版本的 `jitu-source-v1.2.1.zip`，搭配本页未变的数据与比赛材料资产。旧源码包存在 Git 换行转换与冻结哈希不一致问题；新源码已实际恢复全部 24 文件并重放一致，线上 257 后端 / 13 前端测试通过。以下保留 V1.2.0 的发布时记录，不移动旧 tag 或删除旧资产。

修复干净启动与冻结输入恢复、向量数据绑定、局部证据范围、环境权重、文档状态与 CI/OpenAPI 契约检查。补齐 BGE/Chinese-CLIP 独立运行、国内两个案例和 12 图完整 AI 功能草稿；研究指标仍 not_evaluated。

本地验证：252 后端测试通过；默认跳过的 3 项 PostgreSQL 集成在独立库另跑全部通过；前端 13 测试、lint、构建和 npm audit 0；实际干净目录 Compose 迁移/恢复、Chrome 10 项全栈通过。24 开发查询 / 8 方法 / 176 适用组合各三次，共 528 排名无失败或不稳定，恢复库 176 签名全部一致。

线上验证：[GitHub Actions 37307763298](https://github.com/dreamingto/AIC-9.2/actions/runs/37307763298) 已通过，后端 255 项（含真实 PostgreSQL 集成）、前端 13 项，迁移/静态/类型/审计/生产构建与 OpenAPI 漂移检查通过。冻结代码 `86edec6c37385997b41b9b7dc51a0f3e8121b98d`。

资产：

- `jitu-source-v1.2.zip`：258 文件完整源码冻结包，705,060 字节；SHA256 `9eedc3dcc2effe27e9816950eda8bae150d66abe06e69e09df5d73fe085b9f2c`。
- `jitu-domestic-34033a592c974cd7.zip`：国内真实输入恢复包，24 文件含选中扫描、raw OCR、原 manifest 和 88 冻结向量；SHA256 `e108e27390b3b1200e7eeb314a2905e38ff609061bba8f58b67a725de8d1080e`。恢复说明 `release/README.md`，逐文件锁 `release/domestic-data.lock.json`。
- `jitu-competition-v1.2-preview.zip`：198 字简介、技术 PDF、HTML/PDF 答辩、真实浏览器操作 MP4、讲稿、原始排名与附件锁。
- 技术 PDF、答辩 PDF、MP4 亦单独提供便于预览。

模型权重不打包，按 `backend/model_runtime/README.md` 单独下载并校验，安装到独立运行环境。基础 fixture 版不需要大模型。

AI 场景、功能和文字建议全部 Inferred，真实核验 0，无独立 qrels/校订真值，不报告研究准确率或历史传承结论。团队名/编号待填写；这是预审材料与工程发布，不代表已完成比赛报名系统/百度网盘提交。
