"""Context summarizer for LLM prompts."""

import json
from datetime import datetime

from llmtrigger.models.event import Event


class ContextSummarizer:
    """Generate structured summaries of context windows for LLM prompts."""

    def summarize(self, events: list[Event]) -> str:
        """Generate a structured summary of context events.

        Args:
            events: List of events in the context window

        Returns:
            Formatted summary string
        """
        if not events:
            return "No historical events in context window."

        # Sort by timestamp
        sorted_events = sorted(events, key=lambda e: e.timestamp)

        # Calculate time range
        start_time = sorted_events[0].timestamp
        end_time = sorted_events[-1].timestamp
        duration = end_time - start_time

        # Build summary
        lines = [
            f"Event Type: {sorted_events[0].event_type}",
            f"Time Range: {start_time.strftime('%H:%M:%S')} - {end_time.strftime('%H:%M:%S')} ({self._format_duration(duration)})",
            f"Total Events: {len(events)}",
            "",
            "Recent Events:",
        ]

        # Add event details (most recent 10)
        for i, event in enumerate(sorted_events[-10:], 1):
            event_line = self._format_event(i, event)
            lines.append(event_line)

        # Add statistics if applicable
        stats = self._calculate_statistics(sorted_events)
        if stats:
            lines.append("")
            lines.append("Statistics:")
            lines.extend(stats)

        return "\n".join(lines)

    def _format_event(self, index: int, event: Event) -> str:
        """Format a single event for summary.

        Args:
            index: Event index
            event: Event to format

        Returns:
            Formatted event line
        """
        time_str = event.timestamp.strftime("%H:%M:%S")
        data_str = self._format_data(event.data)
        return f"{index}. [{time_str}] {data_str}"

    def _format_data(self, data: dict) -> str:
        """Format event data for summary.

        Args:
            data: Event data dictionary

        Returns:
            Formatted data string
        """
        if not data:
            return "(no data)"

        # Extract key fields for common event types
        parts = []

        # Trading events
        if "symbol" in data:
            parts.append(data["symbol"])
        if "profit" in data:
            profit = data["profit"]
            parts.append(f"{profit:+.2f}" if isinstance(profit, (int, float)) else str(profit))
        if "profit_rate" in data:
            rate = data["profit_rate"]
            if isinstance(rate, (int, float)):
                parts.append(f"({rate*100:+.1f}%)")
            else:
                parts.append(str(rate))

        # Price events
        if "price" in data:
            parts.append(f"price={data['price']}")
        if "change_rate" in data:
            rate = data["change_rate"]
            if isinstance(rate, (int, float)):
                parts.append(f"({rate*100:+.1f}%)")

        # System events
        if "cpu_usage" in data:
            parts.append(f"CPU={data['cpu_usage']*100:.0f}%")
        if "memory_usage" in data:
            parts.append(f"MEM={data['memory_usage']*100:.0f}%")

        if parts:
            return " ".join(parts)

        # Fallback: compact JSON
        return json.dumps(data, ensure_ascii=False)[:100]

    def _format_duration(self, duration) -> str:
        """Format timedelta as human-readable string.

        Args:
            duration: Timedelta object

        Returns:
            Formatted duration string
        """
        total_seconds = int(duration.total_seconds())
        if total_seconds < 60:
            return f"{total_seconds}s"
        elif total_seconds < 3600:
            minutes = total_seconds // 60
            seconds = total_seconds % 60
            return f"{minutes}m {seconds}s"
        else:
            hours = total_seconds // 3600
            minutes = (total_seconds % 3600) // 60
            return f"{hours}h {minutes}m"

    def _calculate_statistics(self, events: list[Event]) -> list[str]:
        """Calculate statistics for numeric fields.

        Args:
            events: List of events

        Returns:
            List of statistic lines
        """
        stats = []

        # Collect numeric values by field
        numeric_fields: dict[str, list[float]] = {}
        for event in events:
            for key, value in event.data.items():
                if isinstance(value, (int, float)):
                    if key not in numeric_fields:
                        numeric_fields[key] = []
                    numeric_fields[key].append(float(value))

        # Calculate stats for common fields
        if "profit" in numeric_fields:
            values = numeric_fields["profit"]
            total = sum(values)
            positive = sum(1 for v in values if v > 0)
            negative = len(values) - positive
            stats.append(f"- Total profit: {total:+.2f}")
            stats.append(f"- Win/Loss: {positive}/{negative}")

        if "profit_rate" in numeric_fields:
            values = numeric_fields["profit_rate"]
            avg = sum(values) / len(values)
            stats.append(f"- Average profit rate: {avg*100:+.1f}%")

        if "price" in numeric_fields:
            values = numeric_fields["price"]
            if len(values) >= 2:
                change = (values[-1] - values[0]) / values[0] * 100
                stats.append(f"- Price change: {change:+.2f}%")

        return stats
