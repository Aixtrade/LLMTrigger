# LLM 批量触发模式示例

本示例演示如何使用 **LLM 批量触发模式（Batch Mode）** 来降低 LLM 调用成本，同时保持智能分析能力。

## 触发模式特点

**批量模式 (Batch)** 会累积一定数量的事件后，再批量进行 LLM 分析，适合高频事件场景。

### 核心参数

- **trigger_mode**: `batch` (批量模式)
- **batch_size**: 累积事件数量（默认 10）
- **max_wait_seconds**: 最大等待时间（默认 60 秒）

### 触发逻辑

```
累积事件 → 达到 batch_size 或超时 → LLM 批量分析 → 触发/不触发
```

**优势**：
- 🔥 **大幅降低成本**：相比实时模式可减少 80-90% 的 LLM 调用
- 📊 **更好的上下文**：批量分析能看到更完整的趋势
- ⚡ **灵活超时**：即使未达到批量大小，超时后也会分析

**权衡**：
- ⏰ **响应延迟**：0 ~ max_wait_seconds 的延迟
- 📦 **批次管理**：需要合理设置 batch_size

## 测试场景

测试基于批量模式的交易信号聚合分析：
- **规则类型**: LLM (纯 LLM 推理)
- **事件类型**: `trade.signal`
- **触发条件**: "当连续出现多个买入信号且总交易量超过阈值时发送告警"
- **触发模式**: `batch` (批量分析)
- **批量大小**: 5 个事件
- **最大等待**: 30 秒
- **通知渠道**: Telegram

## 文件说明

```
03-llm-batch/
├── README.md                      # 本文件
├── create_batch_rule.sh           # 批量规则创建脚本
└── send_trade_signals.py          # 交易信号发送脚本
```

- **create_batch_rule.sh**: 创建 LLM 批量触发规则
  - 检查 API 服务健康状态
  - 创建基于批量模式的交易信号分析规则
  - 显示规则详情和后续操作提示

- **send_trade_signals.py**: 交易信号发送脚本
  - 发送 3 个测试场景的交易信号序列
  - 测试批量累积和触发逻辑

## 前置条件

在运行测试之前，确保以下服务已启动：

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

确保 `.env` 文件包含必要的配置：
- `REDIS_URL`: Redis 连接 URL
- `RABBITMQ_URL`: RabbitMQ 连接 URL
- `RABBITMQ_QUEUE`: 事件队列名称 (默认: trigger_events)
- `TELEGRAM_BOT_TOKEN`: Telegram Bot Token
- `OPENAI_API_KEY`: OpenAI API 密钥 (LLM 功能必需)
- `OPENAI_BASE_URL`: OpenAI API 基础 URL (可选)
- `OPENAI_MODEL`: 使用的模型 (可选)

## 快速开始

### 完整测试流程

```bash
# 步骤 1: 创建批量规则 (在项目根目录执行)
./examples/03-llm-batch/create_batch_rule.sh [YOUR_TELEGRAM_CHAT_ID]

# 示例:
./examples/03-llm-batch/create_batch_rule.sh 1234567890

# 步骤 2: 发送测试事件
uv run python examples/03-llm-batch/send_trade_signals.py

# 步骤 3: 检查 Telegram 是否收到场景1和场景3的告警
# 步骤 4: 查看 Worker 日志确认批量触发过程
```

### 单独运行事件发送

如果你已经创建了规则，可以单独发送测试事件：

```bash
# 使用默认配置
uv run python examples/03-llm-batch/send_trade_signals.py

# 或指定自定义 RabbitMQ 配置
uv run python examples/03-llm-batch/send_trade_signals.py amqp://user:pass@host:5672/ queue_name
```

## 测试场景详解

脚本会发送以下三组交易信号序列：

### 场景 1: 连续买入信号，高交易量 ✅ 应触发告警

- **信号序列**: 6 个连续的买入信号
- **单笔交易量**: 100,000 - 200,000 USDT
- **总交易量**: 约 900,000 USDT
- **事件数量**: 6 个
- **批量触发**: 累积到 5 个事件后触发 LLM 分析
- **预期结果**: LLM 识别出强烈的买入趋势，触发告警

**测试目的**: 验证批量模式能够识别聚合的买入信号和高交易量

### 场景 2: 混合信号，低交易量 ✗ 不应触发

- **信号序列**: 买入和卖出信号混合
- **单笔交易量**: 10,000 - 30,000 USDT
- **总交易量**: 约 120,000 USDT
- **事件数量**: 6 个
- **批量触发**: 累积到 5 个事件后触发 LLM 分析
- **预期结果**: LLM 识别出信号混乱且交易量低，不触发告警

**测试目的**: 验证 LLM 能够区分强烈趋势和混乱信号

### 场景 3: 缓慢累积后超时触发 ✅ 应触发告警

- **信号序列**: 3 个连续的强烈买入信号
- **单笔交易量**: 300,000 - 500,000 USDT (非常高)
- **总交易量**: 约 1,200,000 USDT
- **事件数量**: 3 个 (未达到 batch_size=5)
- **超时触发**: 等待 35 秒后触发 LLM 分析 (超过 max_wait_seconds=30)
- **预期结果**: LLM 识别出虽然事件少但交易量巨大，触发告警

**测试目的**: 验证批量模式的超时机制和对高价值事件的识别

## 验证测试结果

### 1. 检查 Worker 日志

在运行 Worker 的终端查看日志输出：

```
Processing event event_id=xxx event_type=trade.signal
Batch accumulation: 1/5 events accumulated
Batch accumulation: 2/5 events accumulated
...
Batch accumulation: 5/5 events accumulated - triggering LLM analysis
Calling LLM engine with batch context
LLM response: {"should_trigger": true, "confidence": 0.88, "reason": "连续6个买入信号，总交易量90万USDT"}
LLM engine matched (confidence: 0.88)
Notification task enqueued
Sending notification via telegram
Notification sent successfully ✅
```

### 2. 检查 Telegram 消息

打开 Telegram，查看指定 chat_id 对应的聊天：
- **应该收到**: 场景1 和场景3 的告警通知
- **不应收到**: 场景2 的通知

### 3. 检查 Redis 批量状态

```bash
# 查看所有批量状态
docker exec -it llmtrigger-redis-1 redis-cli KEYS "llmtrigger:trigger:mode:batch:*"

# 查看某个规则的批量累积
docker exec -it llmtrigger-redis-1 redis-cli LRANGE llmtrigger:trigger:mode:batch:{rule_id}:trade.signal.* 0 -1

# 查看批量大小
docker exec -it llmtrigger-redis-1 redis-cli LLEN llmtrigger:trigger:mode:batch:{rule_id}:trade.signal.*
```

### 4. 检查 RabbitMQ 队列

访问 http://localhost:15672 (guest/guest)，查看 `trigger_events` 队列的消息处理情况。

## 故障排查

### 问题: 批量未触发

**解决方案**:
1. 检查是否累积了足够的事件（batch_size）
2. 查看 Worker 日志中的批量累积计数
3. 验证 max_wait_seconds 超时设置

```bash
# 查看批量累积状态
docker exec llmtrigger-redis-1 redis-cli LLEN "llmtrigger:trigger:mode:batch:{rule_id}:{context_key}"
```

### 问题: 批量提前触发

**可能原因**:
- 上一批次的事件未清空
- batch_size 设置过小

**解决方案**:
1. 清空 Redis 批量状态
2. 调整 batch_size 参数

```bash
# 清空批量状态
docker exec llmtrigger-redis-1 redis-cli DEL "llmtrigger:trigger:mode:batch:{rule_id}:{context_key}"
```

### 问题: 超时未触发

**可能原因**:
- max_wait_seconds 设置过大
- Worker 进程未运行定期检查

**解决方案**:
1. 检查 Worker 日志是否有超时检查
2. 调整 max_wait_seconds 为更短的时间
3. 重启 Worker 进程

### 问题: LLM 调用仍然频繁

**解决方案**:
1. 增大 batch_size 参数
2. 考虑使用 Hybrid 规则先预过滤
3. 调整 max_wait_seconds 为更长时间

## 批量模式 vs 实时模式对比

| 维度 | 实时模式 | 批量模式 |
|------|---------|---------|
| **响应延迟** | <1 秒 | 0 ~ max_wait_seconds |
| **LLM 调用频率** | 每个事件 | 每 batch_size 个事件 |
| **成本** | 高 | 低（减少 80-90%） |
| **上下文质量** | 单个事件 | 批量事件（更完整） |
| **适用场景** | 低频高价值 | 高频成本敏感 |

## 清理测试数据

```bash
# 删除测试规则 (从 create_batch_rule.sh 输出中获取 rule_id)
curl -X DELETE "http://localhost:8000/api/v1/rules/{rule_id}"

# 清空 Redis 测试数据
docker exec llmtrigger-redis-1 redis-cli KEYS "llmtrigger:*" | \
  xargs docker exec llmtrigger-redis-1 redis-cli DEL

# 清空 RabbitMQ 队列
docker exec llmtrigger-rabbitmq-1 rabbitmqctl purge_queue trigger_events
```

## 自定义测试

### 修改批量参数

编辑 `create_batch_rule.sh` 中的规则配置：

```json
{
  "llm_config": {
    "description": "连续出现多个买入信号且总交易量超过阈值",
    "trigger_mode": "batch",
    "batch_size": 10,           // 增大批量大小
    "max_wait_seconds": 120,    // 增加最大等待时间
    "confidence_threshold": 0.75
  }
}
```

### 发送自定义交易信号

使用 Python 发送自定义交易信号：

```python
import asyncio
from datetime import datetime
from send_trade_signals import send_trade_signal
import aio_pika

async def test_custom_signal():
    connection = await aio_pika.connect_robust("amqp://guest:guest@localhost:5672/")
    channel = await connection.channel()

    await send_trade_signal(
        channel=channel,
        queue_name="trigger_events",
        symbol="BTCUSDT",
        signal="buy",
        volume=100000.0,
        price=50000.0,
        timestamp=datetime.utcnow()
    )

    await connection.close()

asyncio.run(test_custom_signal())
```

## 学习要点

通过这个示例，你可以学习到：

1. **批量触发配置**: 如何设置 batch_size 和 max_wait_seconds
2. **成本优化**: 批量模式如何大幅降低 LLM 调用成本
3. **超时机制**: 如何处理未达到批量大小的场景
4. **批量分析**: LLM 如何分析聚合的事件数据
5. **权衡取舍**: 响应延迟 vs 成本的平衡

## 下一步

- 尝试不同的 batch_size 和 max_wait_seconds 组合
- 对比实时模式和批量模式的 LLM 调用次数
- 尝试 Hybrid 规则结合预过滤和批量分析
- 监控 Redis 中的批量累积状态
- 参考 [../02-llm-realtime/](../02-llm-realtime/) 对比实时模式

## 最佳实践

1. **合理设置批量大小**: 根据事件频率和响应延迟要求设置
2. **必须配置超时**: 避免事件累积不足导致长时间不触发
3. **监控批量状态**: 定期检查 Redis 中的批量累积情况
4. **结合预过滤**: Hybrid 规则可以进一步降低成本
5. **成本监控**: 定期查看 LLM API 调用量和费用
