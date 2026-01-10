# LLMTrigger

[English](README.md) | [中文](README.zh-CN.md)

基于规则引擎与 LLM 推理的智能事件触发系统，用于事件监控与通知。

## 概览
- FastAPI API：规则管理、测试与历史查询。
- 混合规则引擎：表达式过滤 + LLM 校验。
- RabbitMQ 负责事件输入，Redis 负责状态与上下文。
- 通知通道支持 Email、Telegram、企业微信（可扩展）。
- 提供指标与链路追踪的可观测性入口。

## 快速开始
### 前置条件
- Python 3.12+
- Docker（用于 Redis + RabbitMQ）
- `uv`（推荐）或其他 Python 环境管理工具

### 初始化
```bash
cp .env.example .env
docker-compose up -d
uv sync --dev
```

### 启动 API
```bash
uv run uvicorn llmtrigger.api.app:app --reload
```

### 启动 Worker
```bash
uv run python -m llmtrigger.worker
```

API 文档：`http://localhost:8000/docs`

## 配置说明
配置项从环境变量与 `.env` 读取，常用项包括：
- `REDIS_URL`, `RABBITMQ_URL`, `RABBITMQ_QUEUE`
- `OPENAI_API_KEY`, `OPENAI_BASE_URL`, `OPENAI_MODEL`
- `NOTIFICATION_MAX_RETRY`, `NOTIFICATION_DEFAULT_COOLDOWN`

请勿提交密钥，建议使用 `.env` 本地管理。

## 目录结构
- `llmtrigger/api/`: FastAPI 应用、依赖、路由
- `llmtrigger/engine/`: 规则引擎与 LLM 推理
- `llmtrigger/messaging/`: RabbitMQ 消费与处理
- `llmtrigger/storage/`: Redis 客户端与存储
- `llmtrigger/notification/`: 通知调度、Worker、通道
- `llmtrigger/core/`: 配置与日志
- `tests/`: 单元与集成测试
- `docs/`: 架构与设计文档

## 测试
```bash
uv run pytest
```

测试使用 `pytest` + `pytest-asyncio`，位于 `tests/` 目录。

## 参与贡献
贡献规范见 `AGENTS.md`。

## License
MIT License，详见 `LICENSE`。
