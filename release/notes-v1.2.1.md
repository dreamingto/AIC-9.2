机图索隐 V1.2.1 可复现源码修复版。

修复 Windows Git checkout/archive 的换行转换：`.gitattributes` 保留来源登记、模型锁、实验协议和参与实现哈希的源码原字节。严格恢复器没有放宽覆盖规则。实际 Git 归档恢复 24 个冻结输入、Compose 配置及所有实现/协议哈希校验通过。

冻结代码 `fe93ebc0aa32e55035855dd2c51d9ba365c5a497`；[线上 CI](https://github.com/dreamingto/AIC-9.2/actions/runs/37310431347) 已成功，后端 257 项（含真实 PostgreSQL 3）、前端 13 项。新增 2 项登记字节回归，本地 254 后端 + 独立 PostgreSQL 3；Chrome 10 的业务实现未变。

下载此处 `jitu-source-v1.2.1.zip`，710,112 字节，SHA256 `69cde1acab4ae08853e4d6b69a06be2385580bd16db8aa823fa66e6c315556e6`。请用此修复源码替代 V1.2.0 的源码包。

无凭据公开下载已完整回读、SHA256 一致。真实 Git 归档恢复 24 文件后重放固定对照，176 适用组合 / 16 不适用，各三次共 528 排名，失败 0、不稳定 0；与原业务实验全部 176 排名签名、协议/实现哈希及指纹 `253b7b50c756cf580dfc50cfe7e806e3e8588872cf979b137704e23dad447999` 完全一致。逐组比较通过，不把重放稳定性称作研究准确率。

国内真实数据和匿名预审材料内容未变，继续从 [V1.2.0 固定资产](https://github.com/dreamingto/AIC-9.2/releases/tag/v1.2.0-competition-preview) 下载：

- `jitu-domestic-34033a592c974cd7.zip`：24 文件与 88 向量，SHA256 `e108e27390b3b1200e7eeb314a2905e38ff609061bba8f58b67a725de8d1080e`。
- `jitu-competition-v1.2-preview.zip`：简介、8 页技术/答辩 PDF、HTML、4:40.96 实际系统 MP4、讲稿与原始排名。

研究指标仍 not_evaluated，AI 草稿 Inferred；团队信息与比赛系统/百度网盘正式提交待参赛者补充。模型权重按独立模型锁安装。没有改写旧 tag 或覆盖旧数据包。
