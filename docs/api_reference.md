# LLMTrigger 接口文档

## 概览

- Base URL: `http://<host>:<port>`
- API 版本前缀: `/api/v1`
- 默认返回 JSON，`Content-Type: application/json`
- 除 `/health` 外，其余接口返回统一包裹结构

## 通用响应结构

### APIResponse

```json
{
  "code": 0,
  "message": "success",
  "data": {}
}
```

字段说明：
- `code`: 业务码，`0` 表示成功
- `message`: 提示信息
- `data`: 响应数据，可能为 `null`

### PaginatedResponse

```json
{
  "code": 0,
  "message": "success",
  "data": [],
  "total": 0,
  "page": 1,
  "page_size": 20
}
```

字段说明：
- `total`: 总条数
- `page`: 当前页，从 `1` 开始
- `page_size`: 每页数量，默认 `20`，最大 `100`

## 错误响应

- HTTPException: `code` 为 HTTP 状态码
  - `detail` 为字符串时：`message = detail`, `data = null`
  - `detail` 为对象时：`message = "HTTP error"`, `data = detail`
- 参数校验失败：HTTP 422

```json
{
  "code": 422,
  "message": "Validation error",
  "data": [
    {"loc": ["body", "name"], "msg": "Field required", "type": "missing"}
  ]
}
```

## 枚举与数据模型

### 枚举

- `RuleType`: `traditional` | `llm` | `hybrid`
- `TriggerMode`: `realtime` | `batch` | `interval`
- `NotifyTargetType`: `telegram` | `wecom` | `email`
- `NotificationResultStatus`: `queued` | `sent` | `failed` | `skipped`

### RuleConfig

```json
{
  "rule_type": "traditional|llm|hybrid",
  "pre_filter": {
    "type": "expression",
    "expression": "profit_rate > 0.05"
  },
  "llm_config": {
    "description": "...",
    "trigger_mode": "realtime|batch|interval",
    "batch_size": 5,
    "max_wait_seconds": 30,
    "interval_seconds": 30,
    "confidence_threshold": 0.7
  }
}
```

字段说明：
- `rule_type` 必填，规则类型
- `pre_filter` 仅 `traditional`/`hybrid` 必填，传统规则预过滤配置
- `pre_filter.type` 过滤类型，当前固定为 `expression`
- `pre_filter.expression` 过滤表达式（如 `profit_rate > 0.05`）
- `llm_config` 仅 `llm`/`hybrid` 必填，LLM 规则配置
- `llm_config.description` 必填，自然语言规则描述
- `llm_config.trigger_mode` 触发模式，默认 `realtime`
- `llm_config.batch_size` 批量模式单批数量，仅 `batch` 使用
- `llm_config.max_wait_seconds` 批量模式等待上限，仅 `batch` 使用
- `llm_config.interval_seconds` 间隔模式周期秒数，仅 `interval` 使用
- `llm_config.confidence_threshold` 置信度阈值，默认 `0.7`

校验规则：
- `traditional` 需要 `pre_filter`
- `llm` 需要 `llm_config`
- `hybrid` 需要 `pre_filter` + `llm_config`

### NotifyPolicy

```json
{
  "targets": [
    {
      "type": "telegram|wecom|email",
      "chat_id": "123456",
      "webhook_key": "...",
      "to": ["a@example.com"]
    }
  ],
  "rate_limit": {
    "max_per_minute": 5,
    "cooldown_seconds": 60
  }
}
```

字段说明：
- `targets` 通知目标列表
- `targets.type` 必填，目标类型
- `targets.chat_id` 当 `type=telegram` 必填，群/用户 ID
- `targets.webhook_key` 当 `type=wecom` 必填，企业微信 webhook key
- `targets.to` 当 `type=email` 必填，收件人列表
- `rate_limit.max_per_minute` 每分钟最大通知次数，默认 `5`
- `rate_limit.cooldown_seconds` 相同通知冷却秒数，默认 `60`

## 接口列表

### 健康检查

- **GET** `/health`
- 响应：

```json
{
  "status": "ok",
  "version": "<app_version>"
}
```

### 创建规则

- **POST** `/api/v1/rules`
- 请求体：`RuleCreate`

字段：
- `name` string(必填)，规则名称
- `description` string，规则描述
- `enabled` boolean，是否启用
- `priority` int，优先级（越大越优先）
- `event_types` string[] (必填)，匹配事件类型
- `context_keys` string[]，上下文 key 匹配模式（支持 `*`）
- `rule_config` object (必填)，规则配置
  - `rule_config.rule_type` 必填，规则类型
  - `rule_config.pre_filter` 在 `traditional`/`hybrid` 必填
  - `rule_config.llm_config` 在 `llm`/`hybrid` 必填
- `notify_policy` object，通知策略

- 响应：`APIResponse<RuleCreateResponse>`

```json
{
  "code": 0,
  "message": "success",
  "data": {
    "rule_id": "rule_20240101_abcdef12",
    "created_at": "2024-01-01T00:00:00Z"
  }
}
```

### 规则列表

- **GET** `/api/v1/rules`
- Query 参数：
  - `page` int，页码（从 1 开始）
  - `page_size` int，分页大小（1-100）
  - `event_type` string，按事件类型过滤
  - `enabled` boolean，按启用状态过滤
  - `name_contains` string，按名称子串过滤
- 响应：`PaginatedResponse<RuleResponse>`

### 获取规则

- **GET** `/api/v1/rules/{rule_id}`
- 响应：`APIResponse<RuleResponse>`

### 替换规则

- **PUT** `/api/v1/rules/{rule_id}`
- 请求体：`RuleCreate`
- 响应：`APIResponse<RuleResponse>`

### 更新规则

- **PATCH** `/api/v1/rules/{rule_id}`
- 请求体：`RuleUpdate`（仅提交需要更新的字段）

字段：
- `name` string，规则名称
- `description` string，规则描述
- `enabled` boolean，是否启用
- `priority` int，优先级
- `event_types` string[]，事件类型列表（不能为空数组）
- `context_keys` string[]，上下文 key 匹配模式
- `rule_config` object，规则配置
- `notify_policy` object，通知策略

- 响应：`APIResponse<RuleResponse>`

### 删除规则

- **DELETE** `/api/v1/rules/{rule_id}`
- 响应：`APIResponse`

### 更新规则启用状态

- **PATCH** `/api/v1/rules/{rule_id}/status`
- 请求体：

```json
{
  "enabled": true
}
```

- 响应：`APIResponse<RuleResponse>`

### 测试规则（Dry-run）

- **POST** `/api/v1/rules/test`
- 请求体：

```json
{
  "rule_id": "rule_xxx",
  "events": [
    {
      "event_type": "trade.profit",
      "context_key": "trade.profit.123",
      "timestamp": "2024-01-01T00:00:00Z",
      "data": {"profit_rate": 0.12}
    }
  ],
  "dry_run": true
}
```

字段说明：
- `rule_id` 必填，待测试规则 ID
- `events` 必填，事件列表
  - `events[].event_type` 事件类型
  - `events[].context_key` 上下文 key
  - `events[].timestamp` 事件时间（UTC）
  - `events[].data` 事件载荷
- `dry_run` 是否仅验证不发送通知

- 响应：`APIResponse<TestResponse>`

说明：当前实现返回占位结果（未执行真实规则评估）。

### 规则配置校验

- **POST** `/api/v1/rules/validate`
- 请求体：

```json
{
  "rule_config": {
    "rule_type": "llm",
    "llm_config": {"description": "..."}
  }
}
```

字段说明：
- `rule_config` 必填，待校验的规则配置

- 响应：`APIResponse<ValidateResponse>`

```json
{
  "code": 0,
  "message": "success",
  "data": {
    "valid": true,
    "errors": []
  }
}
```

### 规则执行历史

- **GET** `/api/v1/rules/{rule_id}/history`
- Query 参数：
  - `page` int，页码
  - `page_size` int，分页大小
  - `triggered` boolean，是否触发过滤
  - `start_time` datetime，开始时间（UTC）
  - `end_time` datetime，结束时间（UTC）
- 响应：`PaginatedResponse<ExecutionRecord>`

ExecutionRecord 字段说明：
- `execution_id` 执行记录 ID
- `rule_id` 规则 ID
- `event_id` 事件 ID
- `context_key` 上下文 key
- `triggered` 是否触发
- `confidence` 置信度（LLM 规则可能返回）
- `reason` 触发/未触发原因
- `notification_status` 通知状态
- `latency_ms` 处理耗时（毫秒）
- `created_at` 执行时间

说明：当前实现返回空列表（历史存储待实现）。
