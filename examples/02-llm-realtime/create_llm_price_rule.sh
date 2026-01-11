#!/usr/bin/env bash
# 创建 LLM 价格异常告警规则
#
# 用法: ./scripts/create_llm_price_rule.sh [YOUR_TELEGRAM_CHAT_ID]
# 示例: ./scripts/create_llm_price_rule.sh 1234567890

set -euo pipefail

# 配置
API_BASE="${API_BASE:-http://127.0.0.1:8000}"
TELEGRAM_CHAT_ID="${1:-1234567890}"  # 从参数获取，默认 1234567890

echo "==========================================="
echo "  创建 LLM 价格异常告警规则"
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

# 创建 LLM 规则
echo "📝 创建 LLM 规则..."
RULE_RESPONSE=$(curl -s -X POST "${API_BASE}/api/v1/rules" \
  -H 'Content-Type: application/json' \
  -d "{
    \"name\": \"[LLM测试] 价格快速下跌告警\",
    \"description\": \"当价格在5分钟内快速下跌超过5%时发送告警 - $(date '+%Y-%m-%d %H:%M:%S')\",
    \"enabled\": true,
    \"priority\": 100,
    \"event_types\": [\"price.update\"],
    \"context_keys\": [\"price.update.*\"],
    \"rule_config\": {
      \"rule_type\": \"llm\",
      \"llm_config\": {
        \"description\": \"当价格在5分钟内快速下跌超过5%时，发送告警\",
        \"trigger_mode\": \"realtime\",
        \"confidence_threshold\": 0.7
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
        \"max_per_minute\": 5,
        \"cooldown_seconds\": 60
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

echo "✅ LLM 规则创建成功"
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
echo "  - 事件类型: price.update"
echo "  - 规则类型: LLM"
echo "  - 触发条件: 价格在5分钟内快速下跌超过5%"
echo ""
echo "🚀 下一步:"
echo "  运行测试脚本发送价格事件:"
echo "  ./scripts/send_price_events.py"
echo ""
echo "🧹 清理规则:"
echo "  curl -X DELETE '${API_BASE}/api/v1/rules/${RULE_ID}'"
echo ""
