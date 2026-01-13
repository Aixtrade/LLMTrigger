# LLM 规则测试示例

本示例演示如何使用 **LLM 规则引擎**来监控价格异常并发送智能告警。通过 LLM 进行时序分析和模式识别,实现更灵活、更智能的告警策略。

## 测试场景

测试基于 LLM 推理的价格异常检测规则:
- **规则类型**: LLM (纯 LLM 推理)
- **事件类型**: `price.update`
- **触发条件**: "当价格在5分钟内快速下跌超过5%时发送告警"
- **触发模式**: `realtime` (实时分析每个事件)
- **最低置信度**: 0.7
- **通知渠道**: Telegram

## 文件说明

```
02-llm-realtime/
├── README.md                   # 本文件
├── create_llm_price_rule.sh    # 规则创建脚本
└── send_price_events.py        # 测试事件发送脚本
```

- **create_llm_price_rule.sh**: 创建 LLM 价格异常告警规则
  - 检查 API 服务健康状态
  - 创建基于 LLM 推理的价格异常检测规则
  - 显示规则详情和后续操作提示

- **send_price_events.py**: 价格事件发送脚本
  - 发送 4 个测试场景的价格更新事件序列
  - 测试 LLM 的时序分析能力

## 前置条件

在运行测试之前,确保以下服务已启动:

### 1. 启动基础设施

```bash
# 在项目根目录
docker-compose up -d redis rabbitmq
```

### 2. 启动 API 服务 (终端 1)

```bash
uv run uvicorn llmtrigger.api.app:app --reload
```

### 3. 启动 Worker 进程 (终端 2)

```bash
uv run python -m llmtrigger.worker
```

### 4. 配置环境变量

确保 `.env` 文件包含必要的配置:
- `REDIS_URL`: Redis 连接 URL
- `RABBITMQ_URL`: RabbitMQ 连接 URL
- `RABBITMQ_QUEUE`: 事件队列名称 (默认: trigger_events)
- `TELEGRAM_BOT_TOKEN`: Telegram Bot Token
- `OPENAI_API_KEY`: OpenAI API 密钥 (LLM 功能必需)
- `OPENAI_BASE_URL`: OpenAI API 基础 URL (可选,支持自定义端点)
- `OPENAI_MODEL`: 使用的模型 (可选,默认: gpt-4-turbo-preview)

## 快速开始

### 完整测试流程

```bash
# 步骤 1: 创建 LLM 规则 (在项目根目录执行)
./examples/02-llm-realtime/create_llm_price_rule.sh [YOUR_TELEGRAM_CHAT_ID]

# 示例:
./examples/02-llm-realtime/create_llm_price_rule.sh 1234567890

# 步骤 2: 发送测试事件
uv run python examples/02-llm-realtime/send_price_events.py

# 步骤 3: 检查 Telegram 是否收到场景1和场景4的告警
# 步骤 4: 查看 Worker 日志确认 LLM 推理过程
```

### 单独运行事件发送

如果你已经创建了规则,可以单独发送测试事件:

```bash
# 使用默认配置
uv run python examples/02-llm-realtime/send_price_events.py

# 或指定自定义 RabbitMQ 配置
uv run python examples/02-llm-realtime/send_price_events.py amqp://user:pass@host:5672/ queue_name
```

## 测试场景详解

脚本会发送以下四组价格事件序列:

### 场景 1: 价格快速下跌超过5% ✅ 应触发告警

- **交易对**: BTCUSDT
- **价格变化**: $50,000 → $47,000 (下跌 6%)
- **时间跨度**: 5 分钟 (每分钟一个事件)
- **事件数量**: 6 个
- **预期结果**: LLM 识别出快速下跌,触发告警

**测试目的**: 验证 LLM 能够识别符合条件的价格快速下跌

### 场景 2: 价格缓慢下跌 ✗ 不应触发

- **交易对**: ETHUSDT
- **价格变化**: $3,000 → $2,950 (下跌 1.67%)
- **时间跨度**: 5 分钟
- **事件数量**: 6 个
- **预期结果**: LLM 识别出跌幅不足,不触发告警

**测试目的**: 验证 LLM 能够区分"快速"和"缓慢"下跌

### 场景 3: 价格快速上涨 ✗ 不应触发

- **交易对**: SOLUSDT
- **价格变化**: $100 → $108 (上涨 8%)
- **时间跨度**: 5 分钟
- **事件数量**: 6 个
- **预期结果**: LLM 识别出是上涨而非下跌,不触发告警

**测试目的**: 验证 LLM 能够区分"上涨"和"下跌"方向

### 场景 4: 波动中快速下跌 ✅ 应触发告警

- **交易对**: BTCUSDT
- **价格序列**: 48000 → 47800 → 48100 → 47500 → 47200 → 46900 → 47000 → 45500
- **整体跌幅**: 5.2%
- **时间跨度**: 约 6 分钟
- **特点**: 价格有波动但整体快速下跌
- **预期结果**: LLM 识别出整体下跌趋势,触发告警

**测试目的**: 验证 LLM 能够识别波动中的整体趋势

## 验证测试结果

### 1. 检查 Worker 日志

在运行 Worker 的终端查看日志输出:

```
Processing event event_id=xxx event_type=price.update
Routing rule evaluation rule_id=xxx rule_type=llm
Calling LLM engine with context window
LLM response: {"should_trigger": true, "confidence": 0.85, "reason": "价格在5分钟内快速下跌6%"}
LLM engine matched (confidence: 0.85)
Notification task enqueued
Sending notification via telegram
Notification sent successfully ✅
```

### 2. 检查 Telegram 消息

打开 Telegram,查看指定 chat_id 对应的聊天:
- **应该收到**: 场景1 和场景4 的告警通知
- **不应收到**: 场景2 和场景3 的通知

### 3. 检查 Redis 上下文数据

```bash
# 查看所有价格更新上下文
docker exec -it llmtrigger-redis-1 redis-cli KEYS "llmtrigger:context:price.update.*"

# 查看 BTCUSDT 的上下文窗口
docker exec -it llmtrigger-redis-1 redis-cli LRANGE llmtrigger:context:price.update.BTCUSDT 0 -1

# 查看通知队列
docker exec -it llmtrigger-redis-1 redis-cli LRANGE llmtrigger:notification:queue 0 -1
```

### 4. 检查 RabbitMQ 队列

访问 http://localhost:15672 (guest/guest),查看 `trigger_events` 队列的消息处理情况。

## 故障排查

### 问题: LLM 规则不工作

**解决方案**:
1. 检查 `OPENAI_API_KEY` 配置是否正确
2. 验证 `OPENAI_BASE_URL` 是否可访问 (如果配置了)
3. 查看 Worker 日志中的 LLM 调用错误

```bash
# 测试 LLM API 连接
curl -X POST "${OPENAI_BASE_URL}/chat/completions" \
  -H "Authorization: Bearer ${OPENAI_API_KEY}" \
  -H "Content-Type: application/json" \
  -d '{"model": "qwen2.5:7b", "messages": [{"role": "user", "content": "test"}]}'
```

### 问题: LLM 返回格式错误

**可能原因**:
- LLM 模型不支持 JSON 格式输出
- LLM 返回的置信度超出 [0, 1] 范围

**解决方案**:
1. 查看 Worker 日志中的原始 LLM 响应
2. 更换支持结构化输出的模型 (如 GPT-4)
3. 检查 `llmtrigger/engine/llm/parser.py` 的解析逻辑

### 问题: 所有场景都触发或都不触发

**可能原因**:
- LLM 模型能力不足
- 提示词不够清晰
- 最低置信度设置不当

**解决方案**:
1. 调整 `confidence_threshold` 参数 (默认 0.7)
2. 修改规则的 `description` 使其更明确
3. 更换更强大的 LLM 模型

### 问题: LLM 调用速度太慢

**解决方案**:
1. 使用 Hybrid 规则先用表达式过滤
2. 调整 `trigger_mode` 为 `batch` 批量处理
3. 使用更快的 LLM 模型
4. 考虑本地部署 LLM (如 Ollama)

## 清理测试数据

```bash
# 删除测试规则 (从 create_llm_price_rule.sh 输出中获取 rule_id)
curl -X DELETE "http://localhost:8000/api/v1/rules/{rule_id}"

# 清空 Redis 测试数据
docker exec llmtrigger-redis-1 redis-cli KEYS "llmtrigger:*" | \
  xargs docker exec llmtrigger-redis-1 redis-cli DEL

# 清空 RabbitMQ 队列
docker exec llmtrigger-rabbitmq-1 rabbitmqctl purge_queue trigger_events
```

## 自定义测试

### 修改触发条件

编辑 `create_llm_price_rule.sh` 中的规则配置:

```json
{
  "llm_config": {
    "description": "当价格暴跌超过10%或出现异常波动时发送告警",
    "trigger_mode": "realtime",
    "confidence_threshold": 0.8
  }
}
```

### 发送自定义价格事件

使用 Python 发送自定义价格事件:

```python
import asyncio
from datetime import datetime
from send_price_events import send_price_event
import aio_pika

async def test_custom_price():
    connection = await aio_pika.connect_robust("amqp://guest:guest@localhost:5672/")
    channel = await connection.channel()

    await send_price_event(
        channel=channel,
        queue_name="trigger_events",
        symbol="BTCUSDT",
        price=48000.0,
        timestamp=datetime.utcnow()
    )

    await connection.close()

asyncio.run(test_custom_price())
```

## LLM 配置说明

### trigger_mode 触发模式

- **realtime**: 实时模式,每个事件都调用 LLM 分析
  - 优点: 响应快速,实时告警
  - 缺点: LLM 调用次数多,成本高

- **batch**: 批量模式,累积事件后批量分析
  - 优点: 减少 LLM 调用,降低成本
  - 缺点: 响应延迟,需配置批量大小

### confidence_threshold 最低置信度

- 范围: 0.0 - 1.0
- 建议值: 0.7 - 0.8
- 说明: LLM 返回的置信度低于此值时不触发告警

## 学习要点

通过这个示例,你可以学习到:

1. **LLM 规则配置**: 如何用自然语言描述触发条件
2. **时序分析**: LLM 如何分析事件序列和时间趋势
3. **上下文窗口**: 系统如何管理和传递历史事件给 LLM
4. **置信度机制**: 如何使用置信度过滤不确定的判断
5. **触发模式**: realtime vs batch 的区别
6. **LLM 集成**: 如何将 LLM 推理能力集成到规则引擎

## LLM vs Traditional 对比

| 维度 | Traditional 规则 | LLM 规则 |
|------|-----------------|---------|
| **表达方式** | 表达式 (`profit_rate > 0.05`) | 自然语言描述 |
| **灵活性** | 需要明确的条件 | 可处理模糊、复杂的场景 |
| **性能** | 快速 (毫秒级) | 较慢 (秒级,依赖 API) |
| **成本** | 无 | LLM API 调用成本 |
| **可解释性** | 规则透明 | LLM 提供推理原因 |
| **适用场景** | 明确的阈值判断 | 模式识别、趋势分析 |

## 下一步

- 尝试修改触发条件描述 (例如: "价格暴跌超过10%")
- 测试 Batch 模式 (`trigger_mode: "batch"`)
- 调整上下文窗口大小 (规则的 `context_window_size`)
- 尝试 Hybrid 规则 (结合 Traditional 预过滤 + LLM 深度分析)
- 参考 [../01-traditional-rule/](../01-traditional-rule/) 示例对比两种规则类型

## 高级用法: Hybrid 规则

结合 Traditional 和 LLM 的优势:

```bash
curl -X POST "http://localhost:8000/api/v1/rules" \
  -H 'Content-Type: application/json' \
  -d '{
    "name": "[Hybrid] 价格异常综合分析",
    "event_types": ["price.update"],
    "rule_config": {
      "rule_type": "hybrid",
      "pre_filter": {
        "type": "expression",
        "expression": "abs((price - prev_price) / prev_price) > 0.03"
      },
      "llm_config": {
        "description": "分析价格变化是否属于异常波动,考虑历史趋势和市场环境",
        "trigger_mode": "realtime",
        "confidence_threshold": 0.75
      }
    },
    "notify_policy": {
      "targets": [{"type": "telegram", "chat_id": "1234567890"}]
    }
  }'
```

**Hybrid 规则优势**:
1. Traditional 预过滤减少 LLM 调用次数 (降低成本)
2. LLM 进行深度分析,避免误报
3. 兼顾性能和智能

## 最佳实践

1. **从 Traditional 开始**: 先用表达式定义明确条件
2. **LLM 处理复杂场景**: 对于模式识别和趋势分析使用 LLM
3. **Hybrid 平衡性能**: 结合两者优势
4. **合理设置置信度**: 根据业务需求调整阈值
5. **监控 LLM 成本**: 定期查看 API 调用量和费用
