# LLMTrigger 示例集

本目录包含 LLMTrigger 系统的完整测试示例，帮助你快速理解和上手不同类型的规则引擎和触发模式。

## 目录结构

```
examples/
├── README.md                           # 本文件
├── 01-traditional-rule/                # Traditional 规则示例
│   ├── README.md                       # 详细使用说明
│   ├── create_traditional_rule.sh      # 规则创建脚本
│   └── send_test_events.py             # 测试事件发送脚本
├── 02-llm-realtime/                    # LLM Realtime 触发模式示例
│   ├── README.md                       # 详细使用说明
│   ├── create_llm_price_rule.sh        # 规则创建脚本
│   └── send_price_events.py            # 价格事件发送脚本
├── 03-llm-batch/                       # LLM Batch 触发模式示例
│   ├── README.md                       # 详细使用说明
│   ├── create_batch_rule.sh            # 规则创建脚本
│   └── send_trade_signals.py           # 交易信号发送脚本
└── 04-llm-interval/                    # LLM Interval 触发模式示例
    ├── README.md                       # 详细使用说明
    ├── create_interval_rule.sh         # 规则创建脚本
    └── send_metrics.py                 # 系统指标发送脚本
```

## 核心概念

### 规则类型 (Rule Type)

规则类型定义了**事件处理的架构模式**，决定如何组合传统引擎和 LLM 引擎。

| 规则类型 | 说明 | 配置要求 | 适用场景 |
|---------|------|---------|---------|
| `traditional` | 纯传统规则引擎 | `pre_filter` | 明确的阈值判断 |
| `llm` | 纯 LLM 智能推理 | `llm_config` | 模式识别、趋势分析 |
| `hybrid` | 混合模式 | `pre_filter` + `llm_config` | 预筛选 + 智能分析 |

### LLM 触发模式 (Trigger Mode)

触发模式控制**何时执行 LLM 推理**，仅适用于 `llm` 和 `hybrid` 规则类型。

| 触发模式 | 说明 | 关键参数 | 响应延迟 | 成本 |
|---------|------|---------|---------|------|
| `realtime` | 每个事件都触发 LLM | - | <1秒 | 高 |
| `batch` | 累积事件批量分析 | `batch_size`, `max_wait_seconds` | 0~60秒 | 低 |
| `interval` | 定期分析（固定周期） | `interval_seconds` | 固定 | 可控 |

## 示例说明

### 01-traditional-rule - 传统规则引擎

**特点**: 基于表达式的快速判断，无 LLM 调用成本

**测试场景**:
- 订单利润率阈值告警
- 简单的数值比较和逻辑判断

**学习重点**:
- 如何编写表达式（simpleeval）
- Traditional 规则的配置结构
- 基础的事件触发流程

**推荐**: ⭐⭐⭐⭐⭐ 初学者必看，理解系统基础

---

### 02-llm-realtime - LLM 实时触发模式

**特点**: 每个事件立即进行 LLM 分析，响应速度最快

**测试场景**:
- 价格快速下跌检测
- 4 个场景：快速下跌、缓慢下跌、快速上涨、波动下跌

**学习重点**:
- LLM 规则的基本配置
- 实时模式的触发逻辑
- LLM 时序分析能力
- 置信度机制

**推荐**: ⭐⭐⭐⭐ 理解 LLM 智能分析的基础

**注意**: 高频场景成本高，适合低频高价值事件

---

### 03-llm-batch - LLM 批量触发模式

**特点**: 累积一定数量事件后批量分析，大幅降低成本

**测试场景**:
- 交易信号聚合分析
- 3 个场景：连续买入、混合信号、超时触发

**学习重点**:
- 批量累积机制
- 超时触发逻辑
- 成本优化策略（减少 80-90% 的 LLM 调用）

**推荐**: ⭐⭐⭐⭐⭐ 生产环境推荐，平衡性能和成本

**最佳实践**: 结合 Hybrid 规则进一步优化

---

### 04-llm-interval - LLM 间隔触发模式

**特点**: 按固定时间间隔定期分析，成本最可控

**测试场景**:
- 系统健康监控
- 2 个阶段：系统异常期、系统正常期

**学习重点**:
- 定期分析机制
- 固定周期触发逻辑
- 适合定期报告和监控

**推荐**: ⭐⭐⭐⭐ 定期报告和趋势分析的首选

**典型应用**: 每 5 分钟系统健康报告、每小时性能趋势分析

---

## 快速开始

### 前置条件

所有示例都需要以下服务运行：

```bash
# 1. 启动基础设施
docker-compose up -d redis rabbitmq

# 2. 启动 API 服务（终端 1）
uv run uvicorn llmtrigger.api.app:app --reload --port 8203

# 3. 启动 Worker 进程（终端 2）
uv run python -m llmtrigger.worker

# 4. 配置环境变量（编辑 .env 文件）
# 必需: OPENAI_API_KEY, REDIS_URL, RABBITMQ_URL, TELEGRAM_BOT_TOKEN
```

### 运行示例

每个示例目录都包含两个脚本：

```bash
# 步骤 1: 创建规则
./examples/{示例目录}/create_*_rule.sh [YOUR_TELEGRAM_CHAT_ID]

# 步骤 2: 发送测试事件
uv run python examples/{示例目录}/send_*.py

# 步骤 3: 检查结果
# - 查看 Telegram 消息
# - 查看 Worker 日志
# - 查询 Redis 状态
```

**示例**：

```bash
# Traditional 规则
./examples/01-traditional-rule/create_traditional_rule.sh 1234567890
uv run python examples/01-traditional-rule/send_test_events.py

# LLM Realtime 模式
./examples/02-llm-realtime/create_llm_price_rule.sh 1234567890
uv run python examples/02-llm-realtime/send_price_events.py

# LLM Batch 模式
./examples/03-llm-batch/create_batch_rule.sh 1234567890
uv run python examples/03-llm-batch/send_trade_signals.py

# LLM Interval 模式
./examples/04-llm-interval/create_interval_rule.sh 1234567890
uv run python examples/04-llm-interval/send_metrics.py
```

## 学习路径

### 初学者路径

1. **开始**: [01-traditional-rule](./01-traditional-rule/) - 理解基础流程
2. **进阶**: [02-llm-realtime](./02-llm-realtime/) - 体验 LLM 智能分析
3. **优化**: [03-llm-batch](./03-llm-batch/) - 学习成本控制

### 高级用户路径

1. **成本优化**: [03-llm-batch](./03-llm-batch/) - 批量模式
2. **定期报告**: [04-llm-interval](./04-llm-interval/) - 间隔模式
3. **混合策略**: 结合 Hybrid 规则 + 合适的触发模式

### 生产环境推荐

**高频事件场景** (如价格更新、交易信号):
- 推荐: **Hybrid + Batch**
- 配置: 表达式预筛选 + 批量 LLM 分析
- 优势: 减少 **99%** 的 LLM 调用，保持智能判断

**定期监控场景** (如系统健康、资源使用):
- 推荐: **LLM + Interval**
- 配置: 每 5-15 分钟定期分析
- 优势: 成本可控，适合趋势分析

**低频高价值场景** (如重要交易、关键指标):
- 推荐: **LLM + Realtime**
- 配置: 实时响应
- 优势: 快速响应，精准判断

**复杂判断场景** (如连续成功检测、异常聚集):
- 推荐: **Hybrid + Batch**
- 配置: 预筛选 + 批量分析，保证上下文样本量
- 优势: 成本可控，减少误判

## 性能与成本对比

| 规则类型 | 触发模式 | 事件延迟 | LLM 调用频率 | 月成本估算* | 适用场景 |
|---------|---------|---------|-------------|-----------|---------|
| Traditional | - | <1ms | 0% | $0 | 简单阈值 |
| LLM | Realtime | ~150ms | 100% | $500 | 低频高价值 |
| LLM | Batch(10/30s) | 0-30s | ~10% | $50 | 趋势分析 |
| LLM | Interval(30s) | 固定30s | 固定 | $30 | 定期报告 |
| Hybrid | Batch(5/30s) | 0-30s | ~1% | $5 ⭐ | 高频+智能 |

\* 基于 100 事件/秒，30 天，GPT-4 定价估算

## 调试技巧

### 查看 Worker 日志

```bash
# Worker 日志会显示：
# - 事件处理流程
# - 触发模式决策
# - LLM 调用和响应
# - 通知发送状态
```

### 查询 Redis 状态

```bash
# 进入 Redis CLI
docker exec -it llmtrigger-redis-1 redis-cli

# 查看上下文窗口
LRANGE llmtrigger:context:{context_key} 0 -1

# 查看批量状态
LLEN llmtrigger:trigger:mode:batch:{rule_id}:{context_key}

# 查看最后分析时间
GET llmtrigger:trigger:mode:last:{rule_id}:{context_key}

# 查看间隔锁
GET llmtrigger:trigger:mode:interval_lock:{rule_id}
```

### 查看 RabbitMQ 队列

访问 http://localhost:15672 (guest/guest)，查看 `trigger_events` 队列。

## 清理测试数据

```bash
# 删除规则（从创建脚本输出中获取 rule_id）
curl -X DELETE "http://localhost:8203/api/v1/rules/{rule_id}"

# 清空 Redis
docker exec llmtrigger-redis-1 redis-cli KEYS "llmtrigger:*" | \
  xargs docker exec llmtrigger-redis-1 redis-cli DEL

# 清空 RabbitMQ 队列
docker exec llmtrigger-rabbitmq-1 rabbitmqctl purge_queue trigger_events
```

## 故障排查

### 问题: 规则不触发

**检查清单**:
1. Worker 进程是否运行？
2. 规则是否启用 (`enabled: true`)?
3. 事件类型和 context_key 是否匹配？
4. 查看 Worker 日志是否有错误

### 问题: LLM 不工作

**检查清单**:
1. `OPENAI_API_KEY` 是否配置正确？
2. `OPENAI_BASE_URL` 是否可访问？
3. LLM 模型是否支持？
4. 查看 Worker 日志中的 LLM 调用错误

### 问题: Telegram 未收到消息

**检查清单**:
1. `TELEGRAM_BOT_TOKEN` 是否正确？
2. `chat_id` 是否正确？
3. 是否已添加 Bot 为好友？
4. 查看 Worker 日志中的通知发送状态

### 问题: 触发模式行为异常

**检查清单**:
1. 查看 Worker 日志中的触发模式决策
2. 查询 Redis 中的触发状态
3. 验证参数配置（batch_size, interval_seconds 等）
4. 参考对应示例的故障排查部分

## 相关文档

- **项目说明**: [CLAUDE.md](../CLAUDE.md)
- **架构设计**: [docs/architecture.md](../docs/architecture.md)
- **触发模式设计**: [docs/TRIGGER_MODE_DESIGN.md](../docs/TRIGGER_MODE_DESIGN.md)
- **API 文档**: [docs/rules_api_curl_tests.md](../docs/rules_api_curl_tests.md)

## 贡献新示例

欢迎贡献新的示例！每个示例应包含：

1. **README.md**: 详细的使用说明和学习要点
2. **create_*_rule.sh**: 规则创建脚本
3. **send_*.py**: 测试事件发送脚本
4. **测试场景**: 至少 2-4 个覆盖不同情况的场景

## 常见问题

### Q1: 应该使用哪种触发模式？

**A**: 根据场景选择：
- **低频高价值** → Realtime
- **高频成本敏感** → Batch 或 Hybrid + Batch
- **定期报告** → Interval
- **按需分析** → Batch（小批次 + 短等待）

### Q2: Hybrid 规则和 LLM 规则有什么区别？

**A**: Hybrid 在 LLM 之前先用表达式预筛选，可以减少 **80-99%** 的 LLM 调用。

### Q3: 如何选择批量大小和超时时间？

**A**:
- `batch_size`: 根据事件频率，通常 5-20 个
- `max_wait_seconds`: 根据延迟要求，通常 30-120 秒
- 原则: 批量越大越省钱，但延迟越高

## 下一步

1. 依次运行所有示例，理解不同模式的特点
2. 尝试修改配置参数，观察行为变化
3. 阅读架构文档，深入理解设计原理
4. 根据实际业务需求，设计自己的规则
