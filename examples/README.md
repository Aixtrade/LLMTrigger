# LLMTrigger 示例集

本目录包含 LLMTrigger 系统的完整测试示例,帮助你快速理解和上手不同类型的规则引擎。

## 目录结构

```
examples/
├── README.md                           # 本文件
├── 01-traditional-rule/                # Traditional 规则示例
│   ├── README.md                       # 详细使用说明
│   ├── create_traditional_rule.sh      # 规则创建脚本
│   └── send_test_events.py             # 测试事件发送脚本
└── 02-llm-rule/                        # LLM 规则示例
    ├── README.md                       # 详细使用说明
    ├── create_llm_price_rule.sh        # 规则创建脚本
    └── send_price_events.py            # 价格事件发送脚本
```

## 规则类型对比

| 特性 | Traditional | LLM | Hybrid |
|------|-------------|-----|--------|
| **触发条件定义** | 表达式 | 自然语言 | 表达式 + 自然语言 |
| **响应速度** | 快 (毫秒级) | 慢 (秒级) | 中等 |
| **运行成本** | 低 (无 API 调用) | 高 (LLM API) | 中等 (过滤后调用) |
| **适用场景** | 阈值判断 | 模式识别 | 两者结合 |
| **灵活性** | 低 (需明确条件) | 高 (理解语义) | 高 |

## 使用建议

1. **新手推荐**: 从 [01-traditional-rule](./01-traditional-rule/) 开始,理解基础流程
2. **进阶使用**: 尝试 [02-llm-rule](./02-llm-rule/),体验 LLM 的智能分析能力
3. **生产环境**: 考虑使用 Hybrid 规则平衡性能和智能

## 相关文档

- **项目说明**: [CLAUDE.md](../CLAUDE.md)
- **架构设计**: [docs/architecture.md](../docs/architecture.md)
- **API 文档**: [docs/rules_api_curl_tests.md](../docs/rules_api_curl_tests.md)
