#!/usr/bin/env bash
# 创建 Traditional 高盈利率告警规则
#
# 用法: ./examples/01-traditional-rule/create_traditional_rule.sh [YOUR_TELEGRAM_CHAT_ID]
# 示例: ./examples/01-traditional-rule/create_traditional_rule.sh 1234567890

set -euo pipefail

# 配置
API_BASE="${API_BASE:-http://127.0.0.1:8000}"
TELEGRAM_CHAT_ID="${1:-1234567890}"  # 从参数获取，默认 1234567890

echo "==========================================="
echo "  创建 Traditional 高盈利率告警规则"
echo "==========================================="
echo ""
echo "📋 配置:"
echo "  - API 地址: $API_BASE"
echo "  - Telegram Chat ID: $TELEGRAM_CHAT_ID"
echo ""

# 检查 API 服务是否运行
echo "🔍 检查 API 服务..."
if ! curl -s -f "${API_BASE}/health" > /dev/null 2>&1; then
    echo "❌ API 服务未运行！"
    echo "   请先启动: uv run uvicorn llmtrigger.api.app:app --reload"
    exit 1
fi
echo "✅ API 服务正常"
echo ""

# 创建 Traditional 规则
echo "📝 创建 Traditional 规则..."
RULE_RESPONSE=$(curl -s -X POST "${API_BASE}/api/v1/rules" \
  -H 'Content-Type: application/json' \
  -d "{
    \"name\": \"[Traditional测试] 高盈利率告警\",
    \"description\": \"当交易盈利率超过5%时发送告警 - $(date '+%Y-%m-%d %H:%M:%S')\",
    \"enabled\": true,
    \"priority\": 100,
    \"event_types\": [\"trade.profit\"],
    \"context_keys\": [\"trade.profit.*\"],
    \"rule_config\": {
      \"rule_type\": \"traditional\",
      \"pre_filter\": {
        \"type\": \"expression\",
        \"expression\": \"profit_rate > 0.05\"
      }
    },
    \"notify_policy\": {
      \"targets\": [
        {
          \"type\": \"telegram\",
          \"chat_id\": \"${TELEGRAM_CHAT_ID}\"
        }
      ],
      \"rate_limit\": {
        \"max_per_minute\": 10,
        \"cooldown_seconds\": 30
      }
    }
  }")

# 提取 rule_id
RULE_ID=$(echo "$RULE_RESPONSE" | python3 -c "import sys,json; print(json.load(sys.stdin)['data']['rule_id'])" 2>/dev/null || echo "")

if [ -z "$RULE_ID" ]; then
    echo "❌ 创建规则失败！"
    echo "响应: $RULE_RESPONSE"
    exit 1
fi

echo "✅ Traditional 规则创建成功"
echo "   Rule ID: $RULE_ID"
echo ""

# 显示规则详情
echo "📄 规则详情:"
curl -s "${API_BASE}/api/v1/rules/${RULE_ID}" | python3 -m json.tool
echo ""

echo "==========================================="
echo "  规则创建完成！"
echo "==========================================="
echo ""
echo "📝 规则信息:"
echo "  - Rule ID: $RULE_ID"
echo "  - 事件类型: trade.profit"
echo "  - 规则类型: Traditional"
echo "  - 触发条件: profit_rate > 0.05"
echo ""
echo "🚀 下一步:"
echo "  运行测试脚本发送交易事件:"
echo "  uv run python examples/01-traditional-rule/send_test_events.py"
echo ""
echo "🧹 清理规则:"
echo "  curl -X DELETE '${API_BASE}/api/v1/rules/${RULE_ID}'"
echo ""
