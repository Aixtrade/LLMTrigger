# 测试脚本已迁移

测试脚本和示例已迁移到 `examples/` 目录。

## 新位置

```
examples/
├── 01-traditional-rule/    # Traditional 规则测试示例
│   ├── quick_test.sh
│   └── send_test_events.py
│
└── 02-llm-rule/            # LLM 规则测试示例
    ├── create_llm_price_rule.sh
    └── send_price_events.py
```

## 快速开始

```bash
# Traditional 规则测试
./examples/01-traditional-rule/quick_test.sh 1234567890

# LLM 规则测试
./examples/02-llm-rule/create_llm_price_rule.sh 1234567890
uv run python examples/02-llm-rule/send_price_events.py
```

详细说明请参阅 [examples/README.md](../examples/README.md)
