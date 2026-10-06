# V1 API 使用说明

前端同源入口为 `/api/v1`，后端默认 `http://localhost:8000/api/v1`。Swagger 位于 `/docs`，完整 schema 位于 `/openapi.json`；字段以实际 OpenAPI 为准。

## 接口

| 方法 | 路径 | 用途 |
|---|---|---|
| GET | `/health` | 数据库与服务健康 |
| GET | `/capabilities` | 实际 Provider、上传限制、核验状态及数据类型 |
| GET | `/books` | 书籍目录 |
| GET | `/books/{book_id}/editions` | 书籍版本 |
| GET | `/pages/{page_id}` | 原页及对应技术图 |
| GET | `/figures/{figure_id}` | 原图、区域、文本、功能、关系与证据 |
| GET | `/assets/{asset_id}` | 许可允许的资源 |
| POST | `/search/text` | 文本检索 |
| POST | `/search/image` | 图片检索 |
| POST | `/search/region` | 局部区域检索 |
| GET | `/search/{search_id}` | 重读搜索会话 |
| GET | `/associations/{candidate_id}` | 候选详情 |
| POST | `/associations/{candidate_id}/verify` | 保存候选核验及备注 |
| POST | `/ingestion/jobs` | 创建导入任务 |
| GET | `/ingestion/jobs/{job_id}` | 导入状态、统计及错误 |
| GET | `/demo/cases` | 固定国内案例及可用状态 |
| POST | `/demo/cases/{case_id}/search` | 执行案例的真实检索 |

所有实体编号使用 UUID。固定案例的字符串 ID 为 `gengzhi-loom`、`tiangong-waterpower`，具体输入由案例响应读取，不应固定候选排名。

## 搜索输入

文本为 JSON；`query` 1—1000 字符，`top_k` 1—50、默认 10。可按书籍、版本和数据类型过滤：

```json
{
  "query": "织机 经线",
  "top_k": 10,
  "filters": {"dataset_kinds": ["ai_assisted_real_pilot"]}
}
```

图片使用 multipart/form-data，包含 `file`、`top_k`，可选 `filters` 为 JSON 字符串。客户端不手动指定 multipart boundary。上传限制从 `/capabilities` 的 `upload_limits` 读取，后端再次校验实际文件。

区域为 JSON，`page_id` 或 `figure_id` 必须且只能一个；`coordinate_space` 为 `normalized`。下面 `figure_id` 为占位 UUID，使用前须替换成目录或案例返回的真实编号：

```json
{
  "figure_id": "00000000-0000-0000-0000-000000000000",
  "bbox": {"x": 0.055, "y": 0.16, "width": 0.9, "height": 0.73},
  "coordinate_space": "normalized",
  "top_k": 10
}
```

`x/y` 在 [0,1]，`width/height` 大于 0，且 `x+width≤1`、`y+height≤1`；各项必须有限。裁剪检索排除来源图，匹配区域与查询框是两个不同字段。

搜索返回 `search_id`、`query_summary`、`results`、`latency_ms` 与 `model_versions`。每条候选含 `candidate_id`、标题、来源、`image_ref`、匹配区域、分数/分项、CFR、证据、不确定性、核验状态和数据状态。图片查询摘要保留文件元数据，不能据此恢复原上传文件。

`image_ref=null` 表示无可用图；`allow_redistribution=false` 表示图片受限，不应继续请求该资源。分项中的可用性、可靠性、权重和贡献需分别展示，分数不称为史实概率。

## 候选核验

```json
{
  "state": "worth_comparing",
  "note": "待进一步对照原图与文献来源。"
}
```

状态包括 `worth_comparing`、`rejected`、`disputed`、`verified`、`insufficient_evidence`，备注最多 2000 字符。核验保存针对当前候选关联，不把底层 Inferred 证据自动改为 Verified。工程演示使用 synthetic fixture，不能当作真实古籍真值。

## 导入与错误

```json
{"manifest_name": "jitu-fixture-v1.json", "dry_run": false}
```

导入返回任务 ID，随后轮询 `queued/running/completed/failed`。manifest 仅接受配置目录中的文件名；拒绝绝对路径和路径穿越。来源字段、资源哈希与许可在写入前校验，重复导入按稳定实体身份处理。

统一错误：

```json
{
  "error": {
    "code": "RESOURCE_NOT_FOUND",
    "message": "资源不存在",
    "request_id": "00000000-0000-0000-0000-000000000000",
    "details": {}
  }
}
```

常见状态为 404 资源不存在、422 输入无效、403 许可受限、409 状态冲突、503 数据库/模型不可用。客户端显示简洁提示与 request ID；中止旧请求时避免用迟到响应覆盖新页面。

接口修改后，在 backend 目录运行 `python -m scripts.export_openapi --output ../frontend/src/types/openapi.json`，再执行前后端契约测试。具体响应必填/null 规则以 OpenAPI 和前端 Zod schema 为准。
