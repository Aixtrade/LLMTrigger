# LLM 触发模式设计说明

## 文档目的

本文档说明 LLMTrigger 系统中**规则类型（Rule Type）**和**触发模式（Trigger Mode）**的设计，以及两者的关系。

---

## 核心概念区分

### 1. 规则类型（Rule Type）- 架构层面

规则类型定义了**事件处理的架构模式**，决定如何组合传统引擎和 LLM 引擎。

| 规则类型 | 说明 | 配置要求 |
|---------|------|---------|
| `traditional` | 纯传统规则引擎 | 必须有 `pre_filter` |
| `llm` | 纯 LLM 智能推理 | 必须有 `llm_config` |
| `hybrid` | 混合模式（传统预筛选 + LLM） | 必须同时有 `pre_filter` 和 `llm_config` |

**关键点**：
- 规则类型是**互斥的**，一个规则只能选择一种类型
- `rule_type` 字段是**显式声明**，不是根据配置推断
- Traditional 规则**不使用 LLM**，因此没有触发模式的概念

---

### 2. 触发模式（Trigger Mode）- 执行策略层面

触发模式控制**何时执行 LLM 推理**，仅适用于 `llm` 和 `hybrid` 规则类型。

| 触发模式 | 说明 | 关键参数 |
|---------|------|---------|
| `realtime` | 每个事件都触发 LLM | - |
| `batch` | 累积事件批量分析 | `batch_size`, `max_wait_seconds` |
| `interval` | 定期分析（固定周期） | `interval_seconds` |

**关键点**：
- 触发模式控制 LLM 的**调用频率**，用于优化性能和成本
- Traditional 规则没有触发模式，直接基于表达式触发
- 同一个规则类型可以使用不同的触发模式

---

## 两者的关系

```
规则类型 (Rule Type)
    ↓
    ├─ traditional ──→ 无触发模式（直接触发）
    │
    ├─ llm ──────────→ 有触发模式（控制 LLM 调用）
    │                   ├─ realtime
    │                   ├─ batch
    │                   ├─ interval
    │
    └─ hybrid ───────→ 有触发模式（先预筛选，再控制 LLM 调用）
                        ├─ realtime
                        ├─ batch
                        ├─ interval
```

---

## 设计原理

### 为什么需要规则类型？

1. **性能分层**：简单规则用传统引擎（<1ms），复杂规则用 LLM（100-200ms）
2. **成本控制**：Traditional 规则零 LLM 成本
3. **架构清晰**：显式声明处理路径，避免推断歧义
4. **混合优化**：Hybrid 结合两者优势（预筛选 + 智能分析）

### 为什么需要触发模式？

LLM 推理成本高，**不是每个事件都需要 LLM 分析**。触发模式提供多种策略来平衡：
- **响应延迟**：实时 vs 批量 vs 定期
- **LLM 成本**：调用频率控制
- **上下文质量**：确保有足够事件供分析

---

## 配置示例对比

### 场景1：高频价格更新 + 智能判断

```json
{
  "rule_type": "hybrid",  // ← 规则类型：混合模式
  "pre_filter": {
    "expression": "abs(change_rate) > 0.03"  // 预筛选：变化 > 3%
  },
  "llm_config": {
    "description": "价格快速异常波动",
    "trigger_mode": "batch",  // ← 触发模式：批量
    "batch_size": 10,
    "max_wait_seconds": 30
  }
}
```

**处理流程**：
1. 事件到达 → 表达式过滤（99% 的小幅波动被过滤）
2. 通过预筛选的事件累积到批次
3. 批次满 10 个或等待 30 秒后 → 触发 LLM 分析

---

### 场景2：低频技术指标 + 实时响应

```json
{
  "rule_type": "llm",  // ← 规则类型：纯 LLM
  "llm_config": {
    "description": "MACD 金叉且成交量放大",
    "trigger_mode": "realtime"  // ← 触发模式：实时
  }
}
```

**处理流程**：
1. 指标更新事件到达（频率本身就低）
2. 每个事件立即触发 LLM 分析
3. 实时响应，不等待批次

---

### 场景3：简单阈值告警

```json
{
  "rule_type": "traditional",  // ← 规则类型：传统
  "pre_filter": {
    "expression": "cpu_usage > 0.8"
  }
  // 无 llm_config，无触发模式
}
```

**处理流程**：
1. 事件到达 → 表达式求值
2. CPU > 80% → 立即触发通知
3. 全程无 LLM 调用（<1ms 延迟）

---

## 实现架构

### 文件结构

```
llmtrigger/
├── models/rule.py                    # 规则类型和触发模式定义
├── engine/
│   ├── router.py                     # 规则类型路由
│   ├── traditional.py                # 传统引擎
│   └── llm/
│       ├── engine.py                 # LLM 引擎
│       └── trigger_mode.py           # 触发模式管理器 ⭐ 新增
└── storage/
    └── redis_client.py               # 触发模式状态存储
```

### 执行流程

```
事件 → EventHandler
    ↓
RuleRouter.evaluate(event, rule)
    ↓
根据 rule_type 分发：
    ├─ traditional → TraditionalEngine.evaluate()
    │                     ↓
    │                 表达式求值 → 触发/不触发
    │
    ├─ llm → LLMEngine.evaluate()
    │            ↓
    │        TriggerModeManager.should_trigger()  ⭐
    │            ↓
    │        根据 trigger_mode 决策：
    │            ├─ SKIP: 不满足触发条件
    │            ├─ PENDING: 累积中，等待
    │            └─ TRIGGER: 执行 LLM 推理
    │
    └─ hybrid → TraditionalEngine (预筛选)
                     ↓ [通过]
                LLMEngine (同上)
```

---

## 性能与成本对比

| 规则类型 | 触发模式 | 事件延迟 | LLM 调用频率 | 适用场景 |
|---------|---------|---------|-------------|---------|
| Traditional | - | <1ms | 0 | 简单阈值告警 |
| LLM | Realtime | ~150ms | 100% | 低频高价值事件 |
| LLM | Batch(10/30s) | 0-30s | ~10% | 趋势分析 |
| LLM | Interval(30s) | 0-30s | 固定 | 周期监控 |
| Hybrid | Batch(5/30s) | 0-30s | ~1-5% ⭐ | 高频事件+智能判断 |

**推荐**：大多数场景使用 **Hybrid + Batch**，可减少 **80-90%** 的 LLM 调用。

---

## 常见问题

### Q1: 为什么不根据 `pre_filter` 和 `llm_config` 的存在性自动推断规则类型？

**A**: 显式声明优于隐式推断：
1. **意图明确**：用户清楚表达规则意图
2. **验证依据**：`rule_type` 是真值，配置是验证对象
3. **防止歧义**：避免"同时设置两个字段但只想用一个"的情况
4. **代码清晰**：路由逻辑直接基于 `rule_type`，无需多处判断

### Q2: Hybrid 和 LLM + 预筛选表达式有什么区别？

**A**: Hybrid 是架构层面的优化：
- **Hybrid**：预筛选在 LLM 之前执行，不满足的事件**不进入触发模式管理**
- **LLM**：所有事件都进入触发模式管理，累积后才执行 LLM

性能差异：
```
高频场景（1000 事件/秒）：
- Hybrid: 950 个被预筛选丢弃 → 50 个进入批量累积 → 5 次 LLM 调用
- LLM: 1000 个都累积 → 100 次 LLM 调用
```

## 参考文档

- `docs/architecture.md` - 完整架构设计文档
- `llmtrigger/engine/llm/trigger_mode.py` - 触发模式实现
- `llmtrigger/models/rule.py` - 数据模型定义

---

**最后更新**: 2026-01-11
