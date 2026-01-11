#!/usr/bin/env bash
# 快速端到端测试脚本
#
# 用法: ./scripts/quick_test.sh [YOUR_TELEGRAM_CHAT_ID]
# 示例: ./scripts/quick_test.sh 1234567890

set -euo pipefail

# 配置
API_BASE="http://127.0.0.1:8000"
TELEGRAM_CHAT_ID="${1:-1234567890}"  # 从参数获取，默认 1234567890

echo "=========================================="
echo "  LLMTrigger 端到端快速测试"
echo "=========================================="
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

# 创建测试规则
echo "📝 创建测试规则..."
RULE_RESPONSE=$(curl -s -X POST "${API_BASE}/api/v1/rules" \
  -H 'Content-Type: application/json' \
  -d "{
    \"name\": \"[测试] 高盈利率告警\",
    \"description\": \"自动化测试规则 - $(date '+%Y-%m-%d %H:%M:%S')\",
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

echo "✅ 规则创建成功"
echo "   Rule ID: $RULE_ID"
echo ""

# 等待规则生效
echo "⏳ 等待 2 秒让规则生效..."
sleep 2
echo ""

# 发送测试事件
echo "📤 发送测试事件到 RabbitMQ..."
echo ""

# 检查 Python 脚本是否存在
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TEST_SCRIPT="${SCRIPT_DIR}/send_test_events.py"

if [ ! -f "$TEST_SCRIPT" ]; then
    echo "❌ 找不到测试脚本: $TEST_SCRIPT"
    exit 1
fi

# 运行测试事件发送脚本
uv run python "$TEST_SCRIPT"

echo ""
echo "=========================================="
echo "  测试完成！"
echo "=========================================="
echo ""
echo "📱 请检查 Telegram (Chat ID: $TELEGRAM_CHAT_ID) 是否收到通知"
echo ""
echo "🔍 调试信息:"
echo "  - 查看规则: curl -s '${API_BASE}/api/v1/rules/${RULE_ID}' | python3 -m json.tool"
echo "  - 查看 Worker 日志（终端 2）"
echo "  - Redis 上下文: docker exec -it llmtrigger-redis-1 redis-cli KEYS 'llmtrigger:context:*'"
echo "  - 通知队列: docker exec -it llmtrigger-redis-1 redis-cli LRANGE 'llmtrigger:notification:queue' 0 -1"
echo ""
echo "🧹 清理测试规则:"
echo "  curl -X DELETE '${API_BASE}/api/v1/rules/${RULE_ID}'"
echo ""
