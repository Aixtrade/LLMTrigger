# Traditional 规则测试示例

本示例演示如何使用 **Traditional 规则引擎**来监控交易盈利率事件并发送通知。

## 测试场景

测试基于交易盈利率的告警规则:
- **规则类型**: Traditional (基于表达式)
- **事件类型**: `trade.profit`
- **触发条件**: `profit_rate > 0.05` (盈利率超过 5%)
- **通知渠道**: Telegram、邮件

## 文件说明

```
01-traditional-rule/
├── README.md                   # 本文件
├── create_traditional_rule.sh  # 规则创建脚本
└── send_test_events.py         # 测试事件发送脚本
```

- **create_traditional_rule.sh**: 创建 Traditional 告警规则
  - 检查 API 服务健康状态
  - 创建基于表达式的盈利率告警规则
  - 显示规则详情和后续操作提示

- **send_test_events.py**: 测试事件发送脚本
  - 发送多个测试场景的交易盈利事件
  - 模拟不同盈利率的交易

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

## 快速开始

### 完整测试流程

```bash
# 步骤 1: 创建规则 (在项目根目录执行)
./examples/01-traditional-rule/create_traditional_rule.sh [TELEGRAM_CHAT_IDS...] [EMAIL_ADDRESSES...]

# 示例 1: 单个 Telegram 聊天
./examples/01-traditional-rule/create_traditional_rule.sh 1234567890

# 示例 2: 多个 Telegram 聊天
./examples/01-traditional-rule/create_traditional_rule.sh 1234567890 -100987654321

# 示例 3: Telegram + 邮件
./examples/01-traditional-rule/create_traditional_rule.sh 1234567890 -- user1@example.com user2@example.com

# 步骤 2: 发送测试事件
uv run python examples/01-traditional-rule/send_test_events.py

# 步骤 3: 检查 Telegram 和邮件是否收到场景1和场景3的告警
# 步骤 4: 查看 Worker 日志确认规则匹配过程
```

### 单独运行事件发送

如果你已经创建了规则,可以单独发送测试事件:

```bash
# 使用默认配置
uv run python examples/01-traditional-rule/send_test_events.py

# 或指定自定义 RabbitMQ 配置
uv run python examples/01-traditional-rule/send_test_events.py amqp://user:pass@host:5672/ queue_name
```

## 测试场景详解

脚本会发送以下三组测试事件:

### 场景 1: 高盈利率事件 ✅ 应触发告警

发送 3 个高盈利率事件:
- **盈利率**: 0.08, 0.10, 0.12 (均 > 0.05)
- **预期结果**: 每个事件都触发规则,发送 Telegram 通知

**测试目的**: 验证 Traditional 规则能够正确识别超过阈值的事件

### 场景 2: 低盈利率事件 ✗ 不应触发

发送 2 个低盈利率事件:
- **盈利率**: 0.02, 0.03 (均 < 0.05)
- **预期结果**: 不触发规则,无通知

**测试目的**: 验证规则能够过滤不符合条件的事件

### 场景 3: 批量高盈利率事件 ✅ 应触发告警

发送 3 个高盈利率事件:
- **盈利率**: 0.06, 0.075, 0.09 (均 > 0.05)
- **预期结果**: 每个事件都触发规则,发送 Telegram 通知

**测试目的**: 验证规则能够持续监控事件流

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

### 2. 检查 Telegram 和邮件消息

打开 Telegram,查看指定 chat_id 对应的聊天:
- **应该收到**: 场景1 (3条) 和场景3 (3条) 共 6 条通知
- **不应收到**: 场景2 的通知

检查邮箱:
- **应该收到**: 场景1 (3封邮件) 和场景3 (3封邮件) 共 6 封邮件
- **不应收到**: 场景2 的邮件

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

访问 http://localhost:15672 (guest/guest),查看 `trigger_events` 队列的消息处理情况。

## 故障排查

### 问题: 事件发送成功但 Worker 没有处理

**解决方案**:
1. 检查 Worker 进程是否在运行
2. 确认队列名称匹配 (.env 中的 `RABBITMQ_QUEUE`)
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
4. 验证邮件 SMTP 配置是否正确
5. 检查是否被限流

```bash
# 测试 Telegram Bot
curl -X POST "https://api.telegram.org/bot${TELEGRAM_BOT_TOKEN}/sendMessage" \
  -H 'Content-Type: application/json' \
  -d '{"chat_id": "1234567890", "text": "测试"}'
```

### 问题: 表达式评估失败

**可能原因**:
- 表达式语法错误
- 事件数据中缺少必需字段
- 使用了不支持的运算符

**解决方案**:
1. 查看 Worker 日志中的详细错误信息
2. 验证表达式语法 (参考 simpleeval 文档)
3. 确认事件 data 字段包含表达式中引用的变量

## 清理测试数据

```bash
# 删除测试规则 (从 create_traditional_rule.sh 输出中获取 rule_id)
curl -X DELETE "http://localhost:8000/api/v1/rules/{rule_id}"

# 清空 Redis 测试数据
docker exec llmtrigger-redis-1 redis-cli KEYS "llmtrigger:*" | \
  xargs docker exec llmtrigger-redis-1 redis-cli DEL

# 清空 RabbitMQ 队列
docker exec llmtrigger-rabbitmq-1 rabbitmqctl purge_queue trigger_events
```

## 自定义测试

### 修改触发条件

编辑 `create_traditional_rule.sh` 中的表达式:

```json
{
  "rule_config": {
    "rule_type": "traditional",
    "pre_filter": {
      "type": "expression",
      "expression": "profit_rate > 0.1 and profit_amount > 100"
    }
  }
}
```

### 发送自定义事件

使用 Python 发送自定义事件:

```python
import asyncio
from send_test_events import send_custom_event

asyncio.run(send_custom_event(
    rabbitmq_url="amqp://guest:guest@localhost:5672/",
    queue_name="trigger_events",
    event_type="trade.profit",
    context_key="trade.profit.ETHUSDT.MyStrategy",
    data={
        "symbol": "ETHUSDT",
        "strategy": "MyStrategy",
        "profit_rate": 0.15,
        "profit_amount": 200,
        "trade_id": "custom_001"
    }
))
```

## 表达式语法

Traditional 规则支持的运算符:

- **算术运算**: `+`, `-`, `*`, `/`, `%`
- **比较运算**: `>`, `<`, `>=`, `<=`, `==`, `!=`
- **逻辑运算**: `and`, `or`, `not`
- **成员运算**: `in`

### 表达式示例

```python
# 简单阈值
profit_rate > 0.05

# 多条件组合
profit_rate > 0.05 and profit_amount > 100

# 范围判断
profit_rate >= 0.05 and profit_rate <= 0.15

# 字符串匹配
symbol in ['BTCUSDT', 'ETHUSDT']

# 复杂条件
(profit_rate > 0.1 or profit_amount > 500) and strategy == 'HighFreq'
```

## 学习要点

通过这个示例,你可以学习到:

1. **Traditional 规则配置**: 如何使用表达式定义触发条件
2. **事件结构**: LLMTrigger 的事件格式和必需字段
3. **上下文分组**: context_key 如何用于事件分组和去重
4. **多通道通知**: 如何配置多个 Telegram 聊天和邮件地址
5. **限流机制**: 如何配置通知频率限制
6. **端到端流程**: 从事件发送到通知接收的完整流程

## 下一步

- 尝试修改表达式条件 (例如: `profit_rate > 0.1`)
- 添加更复杂的表达式 (例如: `profit_rate > 0.05 and profit_amount > 100`)
- 测试多通道通知 (多个 Telegram 聊天、多个邮件地址)
- 测试其他通知渠道 (企业微信)
- 参考 [../02-llm-rule/](../02-llm-rule/) 示例学习 LLM 规则的智能分析能力
