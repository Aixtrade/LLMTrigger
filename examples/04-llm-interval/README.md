# LLM 间隔触发模式示例

本示例演示如何使用 **LLM 间隔触发模式（Interval Mode）** 来实现定期监控和分析。

## 触发模式特点

**间隔模式 (Interval)** 按固定时间间隔定期进行 LLM 分析，无论累积了多少事件，适合需要定期报告和监控的场景。

### 核心参数

- **trigger_mode**: `interval` (间隔模式)
- **interval_seconds**: 分析间隔时间（默认 300 秒 = 5 分钟）

### 触发逻辑

```
定时器 → 每隔 interval_seconds → LLM 分析上下文窗口 → 触发/不触发
```

**优势**：
- 📅 **定期报告**：固定周期的监控报告
- 🎯 **可预测性**：LLM 调用次数固定，成本可控
- 📊 **趋势分析**：适合分析一段时间内的整体趋势
- ⚖️ **成本可控**：调用频率完全固定

**权衡**：
- ⏰ **固定延迟**：即使紧急事件也需等到下个周期
- 🔄 **可能空转**：即使没有事件也会定期调用 LLM
- 🚫 **实时性差**：不适合需要即时响应的场景

## 测试场景

测试基于间隔模式的系统健康监控：
- **规则类型**: LLM (纯 LLM 推理)
- **事件类型**: `system.metric`
- **触发条件**: "系统资源使用率异常或出现性能下降趋势"
- **触发模式**: `interval` (间隔分析)
- **分析间隔**: 30 秒
- **通知渠道**: Telegram

## 文件说明

```
04-llm-interval/
├── README.md                      # 本文件
├── create_interval_rule.sh        # 间隔规则创建脚本
└── send_metrics.py                # 系统指标发送脚本
```

- **create_interval_rule.sh**: 创建 LLM 间隔触发规则
  - 检查 API 服务健康状态
  - 创建基于间隔模式的系统监控规则
  - 显示规则详情和后续操作提示

- **send_metrics.py**: 系统指标发送脚本
  - 持续发送系统指标事件（CPU、内存、磁盘）
  - 模拟正常和异常两种状态
  - 测试间隔触发逻辑

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
# 步骤 1: 创建间隔规则 (在项目根目录执行)
./examples/04-llm-interval/create_interval_rule.sh [YOUR_TELEGRAM_CHAT_ID]

# 示例:
./examples/04-llm-interval/create_interval_rule.sh 1234567890

# 步骤 2: 发送测试事件（脚本会持续运行90秒）
uv run python examples/04-llm-interval/send_metrics.py

# 步骤 3: 检查 Telegram 是否在第30秒和第60秒收到告警
# 步骤 4: 查看 Worker 日志确认间隔触发过程
```

### 单独运行事件发送

如果你已经创建了规则，可以单独发送测试事件：

```bash
# 使用默认配置（运行90秒）
uv run python examples/04-llm-interval/send_metrics.py

# 或指定自定义 RabbitMQ 配置
uv run python examples/04-llm-interval/send_metrics.py amqp://user:pass@host:5672/ queue_name
```

## 测试场景详解

脚本会持续发送系统指标事件，模拟两种状态：

### 阶段 1: 0-40 秒 - 系统异常 ✅ 应在30秒时触发告警

- **CPU 使用率**: 85-95% (高)
- **内存使用率**: 80-90% (高)
- **磁盘使用率**: 70-80% (较高)
- **事件频率**: 每 2 秒一个指标
- **间隔触发**: 第 30 秒时触发 LLM 分析
- **预期结果**: LLM 识别出资源使用率异常，触发告警

**测试目的**: 验证间隔模式能够定期检测系统异常

### 阶段 2: 40-90 秒 - 系统正常 ✗ 60秒时不应触发告警

- **CPU 使用率**: 20-30% (正常)
- **内存使用率**: 40-50% (正常)
- **磁盘使用率**: 50-60% (正常)
- **事件频率**: 每 2 秒一个指标
- **间隔触发**: 第 60 秒时触发 LLM 分析（从上次分析起30秒后）
- **预期结果**: LLM 识别出系统恢复正常，不触发告警

**测试目的**: 验证 LLM 能够区分正常和异常状态

### 时间线

```
0s    10s   20s   30s   40s   50s   60s   70s   80s   90s
|-----|-----|-----|-----|-----|-----|-----|-----|-----|
      异常状态持续      |      正常状态持续              |
                     ↓ LLM分析(触发)      ↓ LLM分析(不触发)
```

## 验证测试结果

### 1. 检查 Worker 日志

在运行 Worker 的终端查看日志输出：

```
Processing event event_id=xxx event_type=system.metric
Interval check: 15 seconds since last analysis (interval: 30s) - skipping
Interval check: 30 seconds since last analysis - triggering LLM analysis
Calling LLM engine with interval context
LLM response: {"should_trigger": true, "confidence": 0.90, "reason": "CPU和内存使用率持续高位，系统资源紧张"}
LLM engine matched (confidence: 0.90)
Notification task enqueued
...
Interval check: 30 seconds since last analysis - triggering LLM analysis
LLM response: {"should_trigger": false, "confidence": 0.85, "reason": "系统资源使用率恢复正常"}
Event processing completed (no trigger)
```

### 2. 检查 Telegram 消息

打开 Telegram，查看指定 chat_id 对应的聊天：
- **应该收到**: 第30秒的异常告警
- **不应收到**: 第60秒的消息（系统已正常）

### 3. 检查 Redis 间隔状态

```bash
# 查看最后分析时间
docker exec -it llmtrigger-redis-1 redis-cli GET "llmtrigger:trigger:mode:last:{rule_id}:system.metric.server-01"

# 查看间隔锁状态
docker exec -it llmtrigger-redis-1 redis-cli GET "llmtrigger:trigger:mode:interval_lock:{rule_id}"

# 查看上下文窗口
docker exec -it llmtrigger-redis-1 redis-cli LRANGE "llmtrigger:context:system.metric.server-01" 0 -1
```

### 4. 检查 RabbitMQ 队列

访问 http://localhost:15672 (guest/guest)，查看 `trigger_events` 队列的消息处理情况。

## 故障排查

### 问题: 间隔触发不准时

**解决方案**:
1. 检查 Worker 进程是否正常运行
2. 查看 Worker 日志中的间隔检查记录
3. 验证 Redis 中的最后分析时间

```bash
# 查看最后分析时间
docker exec llmtrigger-redis-1 redis-cli GET "llmtrigger:trigger:mode:last:{rule_id}:{context_key}"
```

### 问题: 没有事件时仍然触发

**这是正常行为**:
- 间隔模式会定期触发，即使上下文窗口为空
- LLM 会根据"无事件"的情况进行判断
- 如果不希望这样，考虑使用 Batch 模式

### 问题: LLM 调用过于频繁

**解决方案**:
1. 增大 interval_seconds 参数
2. 考虑使用 Batch 模式
3. 结合 Hybrid 规则先预过滤

### 问题: 错过紧急事件

**解决方案**:
- 间隔模式不适合需要即时响应的场景
- 对于紧急告警，使用 Realtime 模式
- 或创建两个规则：Interval 定期报告 + Realtime 紧急告警

## 间隔模式 vs 其他模式对比

| 维度 | Realtime | Batch | Interval |
|------|---------|-------|----------|
| **触发时机** | 每个事件 | 累积到N个 | 固定周期 |
| **响应延迟** | <1秒 | 0~60秒 | 固定延迟 |
| **成本可控** | ✗ | ✓ | ✓✓ |
| **适合场景** | 低频高价值 | 高频聚合 | 定期报告 |

## 清理测试数据

```bash
# 删除测试规则 (从 create_interval_rule.sh 输出中获取 rule_id)
curl -X DELETE "http://localhost:8000/api/v1/rules/{rule_id}"

# 清空 Redis 测试数据
docker exec llmtrigger-redis-1 redis-cli KEYS "llmtrigger:*" | \
  xargs docker exec llmtrigger-redis-1 redis-cli DEL

# 清空 RabbitMQ 队列
docker exec llmtrigger-rabbitmq-1 rabbitmqctl purge_queue trigger_events
```

## 自定义测试

### 修改间隔参数

编辑 `create_interval_rule.sh` 中的规则配置：

```json
{
  "llm_config": {
    "description": "系统资源使用率异常或出现性能下降趋势",
    "trigger_mode": "interval",
    "interval_seconds": 60,  // 改为每分钟分析一次
    "confidence_threshold": 0.75
  }
}
```

### 发送自定义指标

使用 Python 发送自定义系统指标：

```python
import asyncio
from datetime import datetime
from send_metrics import send_metric_event
import aio_pika

async def test_custom_metric():
    connection = await aio_pika.connect_robust("amqp://guest:guest@localhost:5672/")
    channel = await connection.channel()

    await send_metric_event(
        channel=channel,
        queue_name="trigger_events",
        server="server-01",
        cpu_usage=0.95,
        memory_usage=0.88,
        disk_usage=0.75,
        timestamp=datetime.utcnow()
    )

    await connection.close()

asyncio.run(test_custom_metric())
```

## 学习要点

通过这个示例，你可以学习到：

1. **间隔触发配置**: 如何设置 interval_seconds
2. **定期监控**: 如何实现定时报告和周期性分析
3. **成本控制**: 间隔模式如何提供最可预测的成本
4. **状态追踪**: 如何使用 Redis 追踪最后分析时间
5. **适用场景**: 何时选择间隔模式而非其他模式

## 典型应用场景

1. **系统健康报告**: 每5分钟生成系统健康报告
2. **性能趋势分析**: 每小时分析性能趋势
3. **定期合规检查**: 每天检查配置合规性
4. **周期性汇总**: 每30分钟汇总交易统计
5. **资源使用报告**: 每15分钟检查资源使用情况

## 下一步

- 尝试不同的 interval_seconds 设置
- 对比 Interval 和 Batch 模式的触发行为
- 结合 Hybrid 规则实现智能定期报告
- 监控 Redis 中的间隔状态
- 参考 [../03-llm-batch/](../03-llm-batch/) 对比批量模式

## 最佳实践

1. **合理设置间隔**: 根据监控需求和成本预算设置
2. **处理空窗口**: 确保 LLM 能够处理无事件的情况
3. **成本预算**: interval_seconds 直接决定每天的 LLM 调用次数
4. **结合其他模式**: 定期报告 + 实时告警的双规则策略
5. **监控分析时间**: 确保间隔检查正常工作
