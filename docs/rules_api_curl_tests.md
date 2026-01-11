# Rule API cURL Tests

Use the commands below to exercise the rule-management API. The script prints each response and
uses `python3` to extract the created `rule_id` for follow-up calls.

Notes:
- Use `http://127.0.0.1:8000` as the base URL (no trailing slash).
- Run with `bash` or `zsh`.

```bash
#!/usr/bin/env bash
set -euo pipefail

# 1) Create a rule (copy rule_id from the response)
curl -s -X POST "http://127.0.0.1:8000/api/v1/rules" \
  -H 'Content-Type: application/json' \
  -d '{
    "name": "Rule API Test",
    "description": "Initial rule for API verification",
    "enabled": true,
    "priority": 100,
    "event_types": ["trade.profit"],
    "context_keys": ["trade.profit.*"],
    "rule_config": {
      "rule_type": "hybrid",
      "pre_filter": { "type": "expression", "expression": "profit_rate > 0.05" },
      "llm_config": {
        "description": "When a strategy produces at least 3 profitable trades within the latest context window and the cumulative profit rate exceeds 10%, trigger a notification; otherwise do not trigger.",
        "trigger_mode": "batch",
        "batch_size": 5,
        "max_wait_seconds": 30,
        "confidence_threshold": 0.7
      }
    },
    "notify_policy": {
      "targets": [{ "type": "telegram", "chat_id": "123456" }],
      "rate_limit": { "max_per_minute": 5, "cooldown_seconds": 60 }
    }
  }'

# Set the rule_id from the response above.
rule_id="rule_xxxxxxxxxxxxxxxxx"
echo "RULE_ID=$rule_id"

# 2) List with filters + pagination
curl -s "http://127.0.0.1:8000/api/v1/rules?event_type=trade.profit&enabled=true&page=1&page_size=5"
curl -s "http://127.0.0.1:8000/api/v1/rules?event_type=trade.profit&enabled=false&name_contains=api&page=1&page_size=5"

# 3) Get by ID
curl -s "http://127.0.0.1:8000/api/v1/rules/${rule_id}"

# 4) PATCH (partial update)
curl -s -X PATCH "http://127.0.0.1:8000/api/v1/rules/${rule_id}" \
  -H 'Content-Type: application/json' \
  -d '{"description":"Updated description","enabled":false}'

# 5) PUT (replace)
curl -s -X PUT "http://127.0.0.1:8000/api/v1/rules/${rule_id}" \
  -H 'Content-Type: application/json' \
  -d '{
    "name": "Rule API Test Replaced",
    "description": "Replaced body",
    "enabled": true,
    "priority": 200,
    "event_types": ["trade.profit"],
    "context_keys": ["trade.profit.*"],
    "rule_config": {
      "rule_type": "traditional",
      "pre_filter": { "type": "expression", "expression": "profit_rate > 0.10" }
    },
    "notify_policy": {
      "targets": [{ "type": "telegram", "chat_id": "123456" }],
      "rate_limit": { "max_per_minute": 5, "cooldown_seconds": 60 }
    }
  }'

# 6) Update status
curl -s -X PATCH "http://127.0.0.1:8000/api/v1/rules/${rule_id}/status" \
  -H 'Content-Type: application/json' \
  -d '{"enabled": false}'

# 7) History (currently returns an empty list)
curl -s "http://127.0.0.1:8000/api/v1/rules/${rule_id}/history?page=1&page_size=10"

# 8) Delete + get after delete (expect 404)
curl -s -X DELETE "http://127.0.0.1:8000/api/v1/rules/${rule_id}"
curl -s "http://127.0.0.1:8000/api/v1/rules/${rule_id}"

# 9) Validation error (422)
curl -s -X POST "http://127.0.0.1:8000/api/v1/rules" \
  -H 'Content-Type: application/json' \
  -d '{"name":""}'

# 10) Rule config mismatch (422)
curl -s -X POST "http://127.0.0.1:8000/api/v1/rules" \
  -H 'Content-Type: application/json' \
  -d '{
    "name": "Invalid LLM",
    "event_types": ["trade.profit"],
    "rule_config": { "rule_type": "llm" }
  }'

# 11) Update with empty event_types (422)
curl -s -X PATCH "http://127.0.0.1:8000/api/v1/rules/${rule_id}" \
  -H 'Content-Type: application/json' \
  -d '{"event_types": []}'

# 12) Not found (404)
curl -s "http://127.0.0.1:8000/api/v1/rules/not-exist-rule-id"
```
