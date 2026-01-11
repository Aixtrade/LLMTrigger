# 测试脚本说明

本目录包含用于测试 LLMTrigger 系统的脚本。

## 快速开始

### 一键测试（推荐）

```bash
# 确保服务已启动（参见下面的"前置条件"）
./scripts/quick_test.sh 1234567890
```

这个脚本会自动:
1. 检查 API 服务状态
2. 创建测试规则
3. 发送测试事件到 RabbitMQ
4. 显示调试信息

### 手动测试

```bash
# 发送预设的测试事件序列
uv run python scripts/send_test_events.py

# 或指定自定义 RabbitMQ 配置
uv run python scripts/send_test_events.py amqp://user:pass@host:5672/ queue_name
```

## 前置条件

在运行测试脚本之前，确保以下服务已启动:

### 1. 启动基础设施

```bash
# 在项目根目录
docker-compose up -d redis rabbitmq
```

### 2. 启动 API 服务（终端 1）

```bash
uv run uvicorn llmtrigger.api.app:app --reload
```

### 3. 启动 Worker 进程（终端 2）

```bash
uv run python -m llmtrigger.worker
```

### 4. 确认 .env 配置

确保 `.env` 文件包含必要的配置:
- `REDIS_URL`
- `RABBITMQ_URL`
- `RABBITMQ_QUEUE`
- `TELEGRAM_BOT_TOKEN`（如果测试 Telegram 通知）
- `OPENAI_API_KEY`（如果测试 LLM 规则）

## 脚本详情

### quick_test.sh

**功能**: 一键完成端到端测试流程

**用法**:
```bash
./scripts/quick_test.sh [TELEGRAM_CHAT_ID]
```

**示例**:
```bash
# 使用默认 chat_id (1234567890)
./scripts/quick_test.sh

# 指定自定义 chat_id
./scripts/quick_test.sh 1234567890
```

**流程**:
1. 检查 API 服务健康状态
2. 创建 Traditional 类型测试规则
3. 调用 `send_test_events.py` 发送事件
4. 显示调试和清理命令

### send_test_events.py

**功能**: 发送测试事件到 RabbitMQ

**用法**:
```bash
# 使用默认配置
uv run python scripts/send_test_events.py

# 指定 RabbitMQ URL
uv run python scripts/send_test_events.py amqp://guest:guest@localhost:5672/

# 指定 URL 和队列名
uv run python scripts/send_test_events.py amqp://guest:guest@localhost:5672/ trigger_events

# 查看帮助
uv run python scripts/send_test_events.py --help
```

**测试场景**:
- **场景 1**: 3 个高盈利率事件（profit_rate > 0.05）→ 应触发 Traditional 规则
- **场景 2**: 2 个低盈利率事件（profit_rate < 0.05）→ 不应触发
- **场景 3**: 3 个批量高盈利率事件 → 触发 Hybrid/LLM 规则（如有）

**自定义事件**:

在 Python 中发送单个自定义事件:

```python
import asyncio
from scripts.send_test_events import send_custom_event

asyncio.run(send_custom_event(
    rabbitmq_url="amqp://guest:guest@localhost:5672/",
    queue_name="trigger_events",
    event_type="trade.profit",
    context_key="trade.profit.ETHUSDT.MyStrategy",
    data={
        "symbol": "ETHUSDT",
        "profit_rate": 0.15,
        "profit_amount": 200
    }
))
```

## 验证测试结果

### 1. 检查 Worker 日志

在运行 Worker 的终端查看日志输出:

```
Processing event event_id=xxx event_type=trade.profit
Routing rule evaluation rule_id=xxx rule_type=traditional
Evaluating expression expression='profit_rate > 0.05'
Traditional engine matched
Notification task enqueued
Sending notification via telegram
Notification sent successfully ✅
```

### 2. 检查 Telegram 消息

打开 Telegram，查看指定 chat_id 对应的聊天是否收到通知。

### 3. 检查 Redis 数据

```bash
# 查看上下文窗口
docker exec -it llmtrigger-redis-1 redis-cli LRANGE llmtrigger:context:trade.profit.BTCUSDT.TestStrategy 0 -1

# 查看通知队列
docker exec -it llmtrigger-redis-1 redis-cli LRANGE llmtrigger:notification:queue 0 -1

# 查看限流数据
docker exec -it llmtrigger-redis-1 redis-cli KEYS "llmtrigger:ratelimit:*"
```

### 4. 检查 RabbitMQ 队列

访问 http://localhost:15672 (guest/guest)，查看 `trigger_events` 队列的消息处理情况。

## 故障排查

### 问题: 事件发送成功但 Worker 没有处理

**解决方案**:
1. 检查 Worker 进程是否在运行
2. 确认队列名称匹配（.env 中的 `RABBITMQ_QUEUE`）
3. 查看 Worker 日志是否有错误

```bash
# 检查队列消息数
docker exec llmtrigger-rabbitmq-1 rabbitmqctl list_queues
```

### 问题: 规则匹配但没有发送通知

**解决方案**:
1. 确认规则 `enabled: true`
2. 检查事件类型和上下文键是否匹配规则
3. 验证 Telegram Bot Token 是否正确
4. 检查是否被限流

```bash
# 测试 Telegram Bot
curl -X POST "https://api.telegram.org/bot${TELEGRAM_BOT_TOKEN}/sendMessage" \
  -H 'Content-Type: application/json' \
  -d '{"chat_id": "1234567890", "text": "测试"}'
```

### 问题: LLM 规则不工作

**解决方案**:
1. 检查 `OPENAI_API_KEY` 配置
2. 验证 `OPENAI_BASE_URL` 可访问
3. 查看 Worker 日志中的 LLM 调用错误

```bash
# 测试 LLM API
curl -X POST "${OPENAI_BASE_URL}/chat/completions" \
  -H "Authorization: Bearer ${OPENAI_API_KEY}" \
  -H "Content-Type: application/json" \
  -d '{"model": "qwen2.5:7b", "messages": [{"role": "user", "content": "test"}]}'
```

## 清理测试数据

```bash
# 删除测试规则
curl -X DELETE "http://localhost:8000/api/v1/rules/{rule_id}"

# 清空 Redis 测试数据
docker exec llmtrigger-redis-1 redis-cli KEYS "llmtrigger:*" | \
  xargs docker exec llmtrigger-redis-1 redis-cli DEL

# 清空 RabbitMQ 队列
docker exec llmtrigger-rabbitmq-1 rabbitmqctl purge_queue trigger_events
```

## 进一步阅读

详细的端到端测试指南，请参阅: [docs/e2e_testing_guide.md](../docs/e2e_testing_guide.md)
