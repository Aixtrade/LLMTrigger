# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 项目概述

LLMTrigger 是一个混合智能事件触发系统,结合传统规则引擎和 LLM 推理能力来监控事件并发送通知。

**核心技术栈**: Python 3.12+ | FastAPI | RabbitMQ (aio-pika) | Redis | OpenAI API | uv

## 核心架构

### 三种规则类型 (RuleType)
- **TRADITIONAL**: 基于表达式的传统规则引擎 (使用 simpleeval)
- **LLM**: 纯 LLM 驱动的智能推理规则
- **HYBRID**: 混合模式 - 先通过传统表达式预过滤,再使用 LLM 进行深度分析

### 事件处理流程
```
RabbitMQ事件 → messaging/consumer.py
           ↓
       messaging/handler.py (加载规则)
           ↓
       engine/router.py (规则路由)
           ↓
   ┌───────┴────────┬─────────┐
   ↓                ↓         ↓
Traditional      LLM      Hybrid
   ↓                ↓         ↓
触发规则 → Redis队列 → notification/worker.py
                        ↓
               notification/dispatcher.py
                        ↓
            channels/ (telegram/wecom/email)
```

**关键组件**:
- **上下文**: `context/manager.py` (上下文窗口管理), `context/summarizer.py` (LLM事件总结)
- **存储**: `storage/rule_store.py`, `storage/context_store.py`, `storage/auxiliary.py`
- **限流**: `notification/rate_limiter.py` (Redis限流+冷却)
- **可观测性**: `observability/metrics.py` (Prometheus), `observability/tracing.py`

**API端点**:
- `/api/v1/rules/` - 规则CRUD
- `/api/v1/test/` - 规则测试
- `/api/v1/history/` - 执行历史
- `/health` - 健康检查

## 常用命令

### 环境设置
```bash
uv sync --dev                          # 安装依赖
docker-compose up -d redis rabbitmq    # 启动基础设施
cp .env.example .env                   # 配置环境 (需编辑设置OPENAI_API_KEY等)
```

### 运行服务
```bash
# API服务 (开发模式,热重载)
uv run uvicorn llmtrigger.api.app:app --reload

# Worker进程 (消费RabbitMQ事件 + 处理通知)
uv run python -m llmtrigger.worker
```
API文档: http://localhost:8000/docs

### 测试
```bash
uv run pytest                                                  # 所有测试
uv run pytest tests/unit/test_expression.py                   # 单个文件
uv run pytest tests/unit/test_expression.py::test_func_name   # 单个测试
uv run pytest --cov=llmtrigger --cov-report=html              # 覆盖率报告
```

### 代码质量
```bash
ruff check llmtrigger/     # 代码检查
ruff format llmtrigger/    # 代码格式化
mypy llmtrigger/           # 类型检查 (可选)
```

### 快速测试示例
```bash
# Traditional规则示例
cd examples/01-traditional-rule && ./create_traditional_rule.sh

# LLM规则示例
cd examples/02-llm-rule && ./create_llm_price_rule.sh
```

## 配置说明

所有配置通过环境变量或 `.env` 文件加载 (参见 `llmtrigger/core/config.py` 和 `.env.example`)

**必需配置**:
- `OPENAI_API_KEY` - OpenAI API密钥 (LLM功能必需)
- `REDIS_URL` - Redis连接 (默认: redis://localhost:6379/0)
- `RABBITMQ_URL` - RabbitMQ连接 (默认: amqp://guest:guest@localhost:5672/)

**常用可选配置**:
- `OPENAI_BASE_URL` - 自定义API端点 (默认示例用Ollama: http://localhost:11434/v1)
- `OPENAI_MODEL` - 模型名称 (默认: qwen2.5:7b)
- `RABBITMQ_QUEUE` - 事件队列名 (默认: trigger_events)
- `CONTEXT_WINDOW_SECONDS` - 上下文窗口时长 (默认: 300秒)
- `NOTIFICATION_MAX_RETRY` - 通知重试次数 (默认: 3)
- `NOTIFICATION_DEFAULT_COOLDOWN` - 通知冷却时间 (默认: 60秒)
- `TELEGRAM_BOT_TOKEN`, `SMTP_*` - 通知渠道配置

## 开发注意事项

### 代码风格和命名
- **缩进**: 4空格, 遵循PEP 8
- **类型注解**: 公共函数必须添加
- **命名**: `snake_case` (模块/函数/变量), `PascalCase` (类), `UPPER_SNAKE_CASE` (常量)
- **配置**: 统一使用 `llmtrigger/core/config.py` (pydantic-settings)

### 异步编程 (重要)
- 项目大量使用 `async/await`,所有I/O操作 (Redis/RabbitMQ) 都是异步的
- 测试函数需要 `@pytest.mark.asyncio` 装饰器
- Worker使用 `asyncio.gather()` 并发运行协程

### 规则配置验证
规则创建时自动验证 (见 `models/rule.py:RuleConfig.validate_config()`):
- **TRADITIONAL**: 必须有 `pre_filter`
- **LLM**: 必须有 `llm_config`
- **HYBRID**: 必须同时有 `pre_filter` 和 `llm_config`

### 表达式引擎 (simpleeval)
- **限制**: 不支持函数调用和复杂操作 (安全考虑)
- **支持运算符**: `+, -, *, /, %, >, <, >=, <=, ==, !=, and, or, not, in`
- **变量来源**: 从 `event.data` 字典获取
- **示例**: `profit_rate > 0.05 and volume > 1000`

### LLM集成要点
- 使用OpenAI SDK,支持自定义 `base_url` (兼容Ollama等)
- **响应格式**: 必须严格遵循 `{"should_trigger": bool, "confidence": float, "reason": str}`
- **解析**: `engine/llm/parser.py` 支持Markdown代码块包裹的JSON

### 扩展通知渠道
1. 在 `notification/channels/` 创建新文件,继承 `BaseNotificationChannel`
2. 实现 `async def send(notification: Notification) -> bool` 方法
3. 在 `models/rule.py:NotifyTargetType` 枚举添加新类型
4. 在 `notification/dispatcher.py` 注册新渠道类

### Worker进程架构
Worker进程 (`llmtrigger/worker.py`) 并发运行两个任务:
- **消费者**: `messaging/consumer.py` 消费RabbitMQ事件
- **通知Worker**: `notification/worker.py` 处理Redis通知队列

### 项目文档
- `AGENTS.md` - 开发指南和编码规范 (详细版)
- `docs/architecture.md` - 系统架构设计
- `docs/technical_design_specification.md` - 技术设计规范
- `examples/` - 完整示例 (Traditional/LLM规则)
