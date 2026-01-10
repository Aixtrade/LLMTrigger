"""Prometheus metrics definitions."""

from prometheus_client import Counter, Gauge, Histogram

# Event metrics
EVENTS_RECEIVED = Counter(
    "trigger_events_received_total",
    "Total number of events received",
    ["event_type"],
)

EVENTS_PROCESSED = Counter(
    "trigger_events_processed_total",
    "Total number of events processed",
    ["event_type", "status"],
)

# Rule metrics
RULES_EVALUATED = Counter(
    "trigger_rules_evaluated_total",
    "Total number of rule evaluations",
    ["rule_id", "rule_type"],
)

RULES_TRIGGERED = Counter(
    "trigger_rules_triggered_total",
    "Total number of rule triggers",
    ["rule_id"],
)

# LLM metrics
LLM_REQUESTS = Counter(
    "trigger_llm_requests_total",
    "Total number of LLM API requests",
    ["rule_id", "cache_hit"],
)

LLM_LATENCY = Histogram(
    "trigger_llm_latency_seconds",
    "LLM request latency in seconds",
    ["rule_id"],
    buckets=(0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0),
)

# Notification metrics
NOTIFICATIONS_QUEUED = Counter(
    "trigger_notifications_queued_total",
    "Total notifications queued",
    ["channel"],
)

NOTIFICATIONS_SENT = Counter(
    "trigger_notifications_sent_total",
    "Total notifications sent",
    ["channel", "status"],
)

# Context metrics
CONTEXT_SIZE = Gauge(
    "trigger_context_size",
    "Number of events in context window",
    ["context_key"],
)

# Queue metrics
NOTIFICATION_QUEUE_LENGTH = Gauge(
    "trigger_notification_queue_length",
    "Number of tasks in notification queue",
)
