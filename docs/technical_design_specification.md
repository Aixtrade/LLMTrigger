# 混合智能事件触发系统技术设计方案

## 文档信息

- **文档版本**: v1.1
- **创建日期**: 2026-01-10
- **作者**: aixtrade 团队
- **状态**: 技术设计阶段
- **关联文档**: [架构设计文档](./hybrid_intelligent_trigger_architecture.md)

---

## 1. 概述

本文档是《混合智能事件触发系统架构设计》的技术实现方案，包含 API 接口规范、数据模型定义、Redis 存储设计、核心处理逻辑等内容。

---

## 2. API 接口设计

### 2.1 规则管理 API

| 接口 | 方法 | 说明 |
|------|------|------|
| `/api/v1/rules` | POST | 创建规则 |
| `/api/v1/rules` | GET | 列出规则（支持分页、过滤） |
| `/api/v1/rules/{rule_id}` | GET | 获取单条规则详情 |
| `/api/v1/rules/{rule_id}` | PUT | 更新规则 |
| `/api/v1/rules/{rule_id}` | DELETE | 删除规则 |
| `/api/v1/rules/{rule_id}/status` | PATCH | 启用/禁用规则 |
| `/api/v1/rules/test` | POST | 干跑测试（不实际触发通知） |
| `/api/v1/rules/validate` | POST | 验证规则语法 |
| `/api/v1/rules/{rule_id}/history` | GET | 查询规则触发历史 |

### 2.2 请求/响应示例

#### 创建规则

**请求**: `POST /api/v1/rules`

```json
{
  "name": "连续盈利告警",
  "description": "当策略连续3次盈利且累计收益超过10%时通知",
  "enabled": true,
  "priority": 100,
  "event_types": ["trade.profit"],

  "rule_config": {
    "rule_type": "hybrid",
    "pre_filter": {
      "type": "expression",
      "expression": "profit_rate > 0.05"
    },
    "llm_config": {
      "description": "连续3次盈利且累计收益超过10%",
      "trigger_mode": "batch",
      "batch_size": 5,
      "max_wait_seconds": 30,
      "confidence_threshold": 0.7
    }
  },

  "notify_policy": {
    "targets": [
      {"type": "telegram", "chat_id": "123456"}
    ],
    "rate_limit": {
      "max_per_minute": 5,
      "cooldown_seconds": 60
    }
  }
}
```

**响应**:
```json
{
  "code": 0,
  "message": "success",
  "data": {
    "rule_id": "rule_20260110_001",
    "created_at": "2026-01-10T10:00:00Z"
  }
}
```

#### 干跑测试

**请求**: `POST /api/v1/rules/test`

```json
{
  "rule_id": "rule_20260110_001",
  "events": [
    {
      "event_type": "trade.profit",
      "context_key": "trade.profit.MACD_Strategy",
      "timestamp": "2026-01-10T14:25:00Z",
      "data": {"profit_rate": 0.08}
    }
  ],
  "dry_run": true
}
```

**响应**:
```json
{
  "code": 0,
  "data": {
    "triggers": [
      {
        "event_index": 0,
        "should_trigger": true,
        "confidence": 0.85,
        "reason": "连续盈利，累计收益率超过阈值"
      }
    ],
    "llm_calls": 1,
    "total_latency_ms": 180
  }
}
```

---

## 3. 数据模型定义

### 3.1 规则模型 (Rule)

```json
{
  "rule_id": "string",           // 规则唯一标识
  "name": "string",              // 规则名称
  "description": "string",       // 规则描述
  "enabled": "boolean",          // 是否启用
  "priority": "integer",         // 优先级（越大越高）
  "event_types": ["string"],     // 匹配的事件类型列表

  "rule_config": {
    "rule_type": "traditional | llm | hybrid",

    // 传统规则配置（rule_type = traditional 或 hybrid 时）
    "pre_filter": {
      "type": "expression",
      "expression": "string"     // 表达式，如 "profit_rate > 0.05"
    },

    // LLM 规则配置（rule_type = llm 或 hybrid 时）
      "llm_config": {
      "description": "string",   // 自然语言规则描述
      "trigger_mode": "realtime | batch | interval",
      "batch_size": "integer",   // batch 模式：批次大小
      "max_wait_seconds": "integer",  // batch 模式：最大等待秒数
      "interval_seconds": "integer",  // interval 模式：间隔秒数
      "confidence_threshold": "float" // 置信度阈值（0-1）
    }
  },

  "notify_policy": {
    "targets": [
      {
        "type": "telegram | wecom | email",
        "chat_id": "string",     // telegram 用户/群组
        "webhook_key": "string", // 企业微信
        "to": ["string"]         // 邮件
      }
    ],
    "rate_limit": {
      "max_per_minute": "integer",
      "cooldown_seconds": "integer"
    }
  },

  "metadata": {
    "created_at": "timestamp",
    "updated_at": "timestamp",
    "created_by": "string",
    "version": "integer"
  }
}
```

### 3.2 事件模型 (Event)

```json
{
  "event_id": "string",          // 事件唯一标识（用于幂等）
  "event_type": "string",        // 事件类型，如 "trade.profit"
  "context_key": "string",       // 上下文分组键，如 "trade.profit.MACD_Strategy"
  "timestamp": "ISO8601",        // 事件时间
  "data": {                      // 事件数据（结构由 event_type 决定）
    "...": "..."
  }
}
```

### 3.3 通知任务模型 (NotificationTask)

```json
{
  "task_id": "string",
  "rule_id": "string",
  "context_key": "string",
  "targets": [{"type": "...", "...": "..."}],
  "message": "string",
  "retry_count": "integer",
  "created_at": "timestamp",
  "retry_after": "timestamp"     // 重试时间（重试任务专用）
}
```

### 3.4 执行记录模型 (ExecutionRecord)

```json
{
  "execution_id": "string",
  "rule_id": "string",
  "event_id": "string",
  "context_key": "string",
  "triggered": "boolean",
  "confidence": "float",
  "reason": "string",
  "notification_status": "queued | sent | failed",
  "latency_ms": "integer",
  "created_at": "timestamp"
}
```

---

## 4. Redis 数据结构设计

### 4.1 规则存储

| Key 模式 | 类型 | 说明 |
|----------|------|------|
| `trigger:rules:detail:{rule_id}` | HASH | 规则详情 |
| `trigger:rules:index:{event_type}` | SET | 按事件类型的规则索引 |
| `trigger:rules:all` | SET | 全局规则ID列表 |
| `trigger:rules:version` | STRING | 全局版本号（缓存失效标记） |

**规则详情 HASH 字段**:
- `config`: JSON 序列化的完整规则配置
- `enabled`: "true" / "false"
- `version`: 版本号
- `created_at`: 创建时间戳（毫秒）
- `updated_at`: 更新时间戳（毫秒）

**规则更新广播频道**: `trigger:rules:update`

消息格式:
```json
{"action": "create|update|delete", "rule_id": "xxx", "timestamp": 1704873000000}
```

### 4.2 上下文窗口存储

| Key 模式 | 类型 | 说明 |
|----------|------|------|
| `trigger:context:{context_key}` | ZSET | 事件上下文窗口 |

**ZSET 结构**:
- Score: 事件时间戳（毫秒）
- Member: JSON 序列化的事件数据

**管理策略**:
- 时间窗口清理: `ZREMRANGEBYSCORE key -inf {cutoff_timestamp}`
- 数量限制: `ZREMRANGEBYRANK key 0 -{max_events+1}`
- Key 过期: `EXPIRE key {window_seconds + 60}`

### 4.3 辅助存储

| Key 模式 | 类型 | TTL | 说明 |
|----------|------|-----|------|
| `trigger:processed:{event_id}` | STRING | 3600s | 幂等去重 |
| `trigger:llm_cache:{rule_id}:{context_hash}` | STRING | 60s | LLM 结果缓存 |
| `trigger:notify:queue` | LIST | - | 通知任务队列 |
| `trigger:notify:dead_letter` | LIST | - | 死信队列 |
| `trigger:notify:dedup:{rule_id}:{context_key}` | STRING | 动态 | 通知去重 |
| `trigger:notify:rate:{rule_id}:{minute}` | STRING | 120s | 频率限制计数 |

---

## 5. 核心处理逻辑

### 5.1 事件处理流程

```
1. 接收 MQ 消息
   ↓
2. 解析事件，提取 event_id、event_type、context_key
   ↓
3. 幂等检查
   - SETNX trigger:processed:{event_id}
   - 已存在则跳过
   ↓
4. 上下文更新
   - ZADD trigger:context:{context_key} {timestamp} {event_json}
   - ZREMRANGEBYSCORE 清理过期
   - ZREMRANGEBYRANK 限制数量
   ↓
5. 规则加载
   - 检查本地缓存版本 vs trigger:rules:version
   - 版本不一致则刷新缓存
   - 按 event_type 查询匹配规则
   ↓
6. 规则匹配（按优先级排序执行）
   - traditional: 表达式求值
   - llm: 生成上下文摘要 → 构建 Prompt → 调用 LLM → 解析结果
   - hybrid: pre_filter 预筛选 → LLM 深度分析
   ↓
7. 通知处理
   - 检查去重: EXISTS trigger:notify:dedup:{rule_id}:{context_key}
   - 检查频率: GET trigger:notify:rate:{rule_id}:{minute}
   - 入队: LPUSH trigger:notify:queue {task_json}
   ↓
8. 记录执行结果和指标
```

### 5.2 规则热更新机制

```
API 更新规则
   ↓
写入 Redis
   - HSET trigger:rules:detail:{rule_id} ...
   - SADD/SREM trigger:rules:index:{event_type} ...
   - INCR trigger:rules:version
   ↓
发布更新事件
   - PUBLISH trigger:rules:update {action, rule_id}
   ↓
Worker 收到通知
   - 对比本地 cache_version 与 trigger:rules:version
   - 不一致则标记缓存失效
   - 下次规则查询时刷新
```

### 5.3 通知发送流程

```
消费任务
   - BRPOP trigger:notify:queue {timeout}
   ↓
发送通知
   - 按 target.type 路由到对应通道
   - Telegram / 企业微信 / 邮件
   ↓
处理结果
   - 成功: 记录日志，更新指标
   - 失败: retry_count++
     - retry_count <= MAX_RETRY: 计算退避时间，重新入队
     - retry_count > MAX_RETRY: LPUSH 死信队列
```

### 5.4 LLM 推理流程

```
检查缓存
   - GET trigger:llm_cache:{rule_id}:{context_hash}
   - 命中则直接返回
   ↓
生成上下文摘要
   - ZRANGEBYSCORE 获取窗口内事件
   - 格式化为结构化文本
   ↓
构建 Prompt
   - 系统角色设定
   - 用户规则描述
   - 历史上下文摘要
   - 当前事件数据
   - 输出格式要求（JSON）
   ↓
调用 LLM 服务（OpenAI 兼容接口）
   - POST {OPENAI_BASE_URL}/chat/completions
   - 设置超时、温度等参数
   ↓
解析结果
   - 提取 JSON: {should_trigger, confidence, reason}
   - 解析失败则使用降级结果
   ↓
置信度过滤
   - confidence < threshold: should_trigger = false
   ↓
写入缓存
   - SETEX trigger:llm_cache:{rule_id}:{context_hash} {ttl} {result}
```

---

## 6. 配置规范

### 6.1 环境变量

| 变量名 | 说明 | 默认值 |
|--------|------|--------|
| `REDIS_URL` | Redis 连接地址 | `redis://localhost:6379/0` |
| `RABBITMQ_URL` | RabbitMQ 连接地址 | `amqp://guest:guest@localhost:5672/` |
| `RABBITMQ_QUEUE` | 事件队列名称 | `trigger_events` |
| `OPENAI_API_KEY` | LLM API 密钥 | - |
| `OPENAI_BASE_URL` | LLM API 地址（兼容 OpenAI 格式） | `http://localhost:11434/v1` |
| `OPENAI_MODEL` | 使用的模型名称 | `qwen2.5:7b` |
| `OPENAI_TIMEOUT` | API 请求超时时间（秒） | `30` |
| `CONTEXT_WINDOW_SECONDS` | 上下文时间窗口 | `300` |
| `CONTEXT_MAX_EVENTS` | 上下文最大事件数 | `100` |
| `NOTIFICATION_MAX_RETRY` | 通知最大重试次数 | `3` |
| `NOTIFICATION_DEFAULT_COOLDOWN` | 默认通知冷却时间 | `60` |

**LLM 配置说明**：
- 使用 OpenAI 兼容格式，支持多种 LLM 服务提供商
- 本地 Ollama: `OPENAI_BASE_URL=http://localhost:11434/v1`
- OpenAI 官方: `OPENAI_BASE_URL=https://api.openai.com/v1`
- Azure OpenAI: `OPENAI_BASE_URL=https://{resource}.openai.azure.com/openai/deployments/{deployment}`
- 其他兼容服务: 按各服务商文档配置

### 6.2 规则配置示例

**传统规则**:
```yaml
rule_id: rule_simple_001
name: 盈利率告警
rule_config:
  rule_type: traditional
  pre_filter:
    type: expression
    expression: "profit_rate > 0.1"
event_types:
  - trade.profit
notify_policy:
  targets:
    - type: telegram
      chat_id: "123456"
```

**LLM 规则**:
```yaml
rule_id: rule_llm_001
name: 连续盈利告警
rule_config:
  rule_type: llm
  llm_config:
    description: "当策略连续3次盈利且累计收益超过10%时通知"
    trigger_mode: batch
    batch_size: 5
    confidence_threshold: 0.7
event_types:
  - trade.profit
notify_policy:
  targets:
    - type: telegram
      chat_id: "-1001234567890"
  rate_limit:
    max_per_minute: 5
    cooldown_seconds: 300
```

**混合规则**:
```yaml
rule_id: rule_hybrid_001
name: 高收益连续盈利
rule_config:
  rule_type: hybrid
  pre_filter:
    type: expression
    expression: "profit_rate > 0.05"
  llm_config:
    description: "连续3次盈利且累计收益超过15%"
    trigger_mode: batch
    batch_size: 5
    confidence_threshold: 0.8
event_types:
  - trade.profit
notify_policy:
  targets:
    - type: telegram
      chat_id: "123456"
    - type: email
      to: ["trader@example.com"]
```

---

## 7. 监控指标

### 7.1 指标列表

| 指标名称 | 类型 | 标签 | 说明 |
|----------|------|------|------|
| `trigger_events_received_total` | Counter | event_type | 接收事件总数 |
| `trigger_events_processed_total` | Counter | event_type, status | 处理事件总数 |
| `trigger_rules_evaluated_total` | Counter | rule_id, rule_type | 规则评估次数 |
| `trigger_rules_triggered_total` | Counter | rule_id | 规则触发次数 |
| `trigger_llm_requests_total` | Counter | rule_id, cache_hit | LLM 请求次数 |
| `trigger_llm_latency_seconds` | Histogram | rule_id | LLM 请求延迟 |
| `trigger_notifications_queued_total` | Counter | channel | 通知入队数 |
| `trigger_notifications_sent_total` | Counter | channel, status | 通知发送数 |
| `trigger_context_size` | Gauge | context_key | 上下文窗口大小 |

### 7.2 关键告警规则

| 告警名称 | 条件 | 说明 |
|----------|------|------|
| `HighLLMLatency` | llm_latency_seconds > 5s | LLM 响应过慢 |
| `NotificationQueueBacklog` | queue_length > 1000 | 通知队列积压 |
| `HighNotificationFailureRate` | failure_rate > 10% | 通知失败率过高 |
| `LLMServiceUnavailable` | llm_errors > 10/min | LLM 服务不可用 |

---

## 8. context_key 命名规范

### 8.1 格式要求

- 使用点号 `.` 分隔各级标识
- 推荐格式: `{event_type}.{dimension1}.{dimension2}...`
- 必须稳定且低基数，避免使用时间戳、订单号等高基数字段

### 8.2 命名示例

| 场景 | context_key 示例 |
|------|------------------|
| 交易盈利（按策略） | `trade.profit.MACD_Strategy` |
| 交易盈利（按交易对+策略） | `trade.profit.BTCUSDT.MACD_Strategy` |
| 价格更新 | `price.update.BTCUSDT` |
| 技术指标 | `indicator.update.BTCUSDT` |
| 系统监控 | `system.metrics.trading-server-01` |

---

## 文档变更记录

| 版本 | 日期 | 作者 | 变更说明 |
|------|------|------|----------|
| v1.0 | 2026-01-10 | aixtrade 团队 | 初始版本 |
| v1.1 | 2026-01-10 | aixtrade 团队 | 精简文档，移除具体实现代码；更新 context_key 命名规范 |

---

**END OF DOCUMENT**
