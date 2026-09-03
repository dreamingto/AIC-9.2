# 数据与许可

V1 fixture 使用 3 个合成来源和 9 个确定性生成 PNG。每个来源、版本、页面、图和资源都保留来源 URL、来源名、书名、版本、卷次、页叶、许可证、抓取时间、SHA-256、原始路径和 pipeline 版本等字段。

fixture 的许可证状态为 `synthetic_fixture`，只用于工程流程验证。来源 A/B 的 6 个资源允许演示分发；来源 C 的 3 个资源明确设置 `allow_redistribution=false`，专用于验证许可受限路径。资源公开接口统一检查该字段，禁止通过 API 绕过许可限制。
