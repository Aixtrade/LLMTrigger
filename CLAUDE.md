# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 项目概述

LLMTrigger 是一个混合智能事件触发系统,结合传统规则引擎和 LLM 推理能力来监控事件并发送通知。

## 核心架构

### 三种规则类型
系统支持三种规则类型 (RuleType):
- **TRADITIONAL**: 基于表达式的传统规则引擎 (使用 simpleeval)
- **LLM**: 纯 LLM 驱动的智能推理规则
- **HYBRID**: 混合模式 - 先通过传统表达式预过滤,再使用 LLM 进行深度分析

### 事件处理流程
1. RabbitMQ 接收事件 → `messaging/consumer.py`
2. `messaging/handler.py` 从 Redis 加载匹配的规则
3. `engine/router.py` 根据规则类型路由到不同引擎:
   - Traditional: `engine/traditional.py` (使用 `engine/expression.py` 评估表达式)
   - LLM: `engine/llm/engine.py` (调用 OpenAI API,使用 `engine/llm/prompt.py` 构建提示)
   - Hybrid: 先 traditional 预过滤,通过后再调用 LLM
4. 触发的规则生成通知任务 → Redis 队列
5. `notification/worker.py` 消费通知任务,通过 `notification/dispatcher.py` 分发
6. 通知渠道: `notification/channels/` (telegram.py, wecom.py, email.py)

### 关键组件
- **上下文管理**: `context/manager.py` 管理事件上下文窗口, `context/summarizer.py` 使用 LLM 总结历史事件
- **存储层**: `storage/rule_store.py` (规则存储), `storage/context_store.py` (上下文存储), `storage/auxiliary.py` (通知队列/去重)
- **限流**: `notification/rate_limiter.py` 实现基于 Redis 的通知频率限制和冷却时间
- **可观测性**: `observability/metrics.py` (Prometheus 指标), `observability/tracing.py` (分布式追踪)

### FastAPI 路由
- `/api/v1/rules/`: 规则 CRUD 操作 (创建、查询、更新、删除、替换)
- `/api/v1/test/`: 规则测试端点 (模拟事件触发)
- `/api/v1/history/`: 执行历史查询
- `/health`: 健康检查

## 常用命令

### 环境设置
```bash
# 安装依赖 (推荐使用 uv)
uv sync --dev

# 启动基础设施
docker-compose up -d redis rabbitmq

# 复制环境配置
cp .env.example .env
```

### 运行服务
```bash
# 启动 FastAPI 服务 (开发模式,热重载)
uv run uvicorn llmtrigger.api.app:app --reload

# 启动 Worker 进程 (消费 RabbitMQ 事件 + 处理通知)
uv run python -m llmtrigger.worker
```

### 测试
```bash
# 运行所有测试
uv run pytest

# 运行单个测试文件
uv run pytest tests/unit/test_expression.py

# 运行单个测试函数
uv run pytest tests/unit/test_expression.py::test_evaluate_simple_expression

# 运行测试并查看覆盖率
uv run pytest --cov=llmtrigger --cov-report=html
```

### 开发工具
```bash
# 代码格式化 (如果配置了)
ruff format llmtrigger/

# 代码检查
ruff check llmtrigger/

# 类型检查 (如果需要)
mypy llmtrigger/
```

## 配置说明

所有配置通过环境变量或 `.env` 文件加载,参见 `llmtrigger/core/config.py`:

### 必需配置
- `REDIS_URL`: Redis 连接 URL (默认: redis://localhost:6379/0)
- `RABBITMQ_URL`: RabbitMQ 连接 URL (默认: amqp://guest:guest@localhost:5672/)
- `OPENAI_API_KEY`: OpenAI API 密钥 (LLM 功能必需)

### 可选配置
- `OPENAI_BASE_URL`: OpenAI API 基础 URL (可用于自定义端点)
- `OPENAI_MODEL`: 使用的模型 (默认: gpt-4-turbo-preview)
- `RABBITMQ_QUEUE`: 事件队列名称 (默认: llmtrigger.events)
- `NOTIFICATION_MAX_RETRY`: 通知最大重试次数 (默认: 3)
- `NOTIFICATION_DEFAULT_COOLDOWN`: 默认冷却时间 (默认: 300 秒)

## 开发注意事项

### 代码风格
- 使用 4 空格缩进,遵循 PEP 8
- 公共函数必须添加类型注解
- 模块和文件使用 snake_case,类使用 PascalCase,常量使用 UPPER_SNAKE_CASE
- 配置统一放在 `llmtrigger/core/config.py`,使用 pydantic-settings

### 异步编程
- 项目大量使用 async/await,注意 Redis 和 RabbitMQ 操作都是异步的
- 测试使用 `pytest-asyncio`,测试函数需要 `@pytest.mark.asyncio` 装饰器
- Worker 进程使用 `asyncio.gather()` 并发运行多个协程

### 规则配置验证
规则创建时会自动验证:
- TRADITIONAL 规则必须有 `pre_filter`
- LLM 规则必须有 `llm_config`
- HYBRID 规则必须同时有 `pre_filter` 和 `llm_config`
参见 `llmtrigger/models/rule.py:RuleConfig.validate_config()`

### 表达式引擎限制
- 使用 simpleeval 评估表达式,出于安全考虑,不支持函数调用和复杂操作
- 支持的运算符: `+, -, *, /, %, >, <, >=, <=, ==, !=, and, or, not, in`
- 表达式中的变量从 `event.data` 字典中获取

### LLM 集成
- LLM 引擎使用 OpenAI SDK,支持自定义 base_url (兼容其他 OpenAI API 实现)
- 响应需要严格遵循 JSON 格式: `{"should_trigger": bool, "confidence": float, "reason": str}`
- 解析逻辑在 `engine/llm/parser.py`,支持 Markdown 代码块包裹的 JSON

### 通知渠道扩展
添加新通知渠道:
1. 在 `notification/channels/` 创建新文件,继承 `BaseNotificationChannel`
2. 实现 `send()` 方法
3. 在 `NotifyTargetType` 枚举中添加新类型
4. 在 `notification/dispatcher.py` 注册新渠道

## 文档参考
- `docs/architecture.md`: 详细的系统架构设计
- `docs/technical_design_specification.md`: 技术设计规范
- `docs/rules_api_curl_tests.md`: API 测试用例示例
- `AGENTS.md`: 贡献者指南和编码规范

## 使用中文
- 代码注释和文档字符串使用英文
- 与用户交互、日志消息可以使用中文
- Commit message 和 PR 描述推荐使用中文
