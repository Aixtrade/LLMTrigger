#!/usr/bin/env python3
"""发送系统指标事件到 RabbitMQ 的脚本。

用于测试 LLM 间隔触发模式的定期监控能力。
"""

import asyncio
import json
import sys
from datetime import datetime
from uuid import uuid4
import random

import aio_pika
from aio_pika import DeliveryMode, Message


async def send_metric_event(
    channel: aio_pika.abc.AbstractChannel,
    queue_name: str,
    server: str,
    cpu_usage: float,
    memory_usage: float,
    disk_usage: float,
    timestamp: datetime,
) -> None:
    """发送单个系统指标事件到 RabbitMQ。

    Args:
        channel: RabbitMQ 通道
        queue_name: 队列名称
        server: 服务器名称
        cpu_usage: CPU 使用率 (0-1)
        memory_usage: 内存使用率 (0-1)
        disk_usage: 磁盘使用率 (0-1)
        timestamp: 时间戳
    """
    event_id = str(uuid4())
    context_key = f"system.metric.{server}"

    event = {
        "event_id": event_id,
        "event_type": "system.metric",
        "context_key": context_key,
        "timestamp": timestamp.isoformat(),
        "data": {
            "server": server,
            "cpu_usage": cpu_usage,
            "memory_usage": memory_usage,
            "disk_usage": disk_usage,
            "timestamp": timestamp.isoformat(),
        },
    }

    # 声明队列（如果不存在）
    queue = await channel.declare_queue(queue_name, durable=True)

    # 发送消息
    message = Message(
        body=json.dumps(event).encode(),
        delivery_mode=DeliveryMode.PERSISTENT,
        content_type="application/json",
    )

    await channel.default_exchange.publish(
        message,
        routing_key=queue_name,
    )

    print(
        f"✓ [{timestamp.strftime('%H:%M:%S')}] {server}: "
        f"CPU={cpu_usage*100:.1f}% MEM={memory_usage*100:.1f}% DISK={disk_usage*100:.1f}%"
    )


async def send_continuous_metrics(rabbitmq_url: str, queue_name: str) -> None:
    """持续发送系统指标事件，模拟定期监控。

    Args:
        rabbitmq_url: RabbitMQ 连接 URL
        queue_name: 队列名称
    """
    # 连接 RabbitMQ
    connection = await aio_pika.connect_robust(rabbitmq_url)
    channel = await connection.channel()

    print()
    print("=" * 70)
    print("  LLM 间隔触发模式测试")
    print("=" * 70)
    print()
    print(f"已连接到 RabbitMQ: {rabbitmq_url}")
    print(f"目标队列: {queue_name}")
    print()
    print("测试说明:")
    print("  - 脚本将运行 90 秒，每 2 秒发送一个系统指标")
    print("  - 0-40秒: 模拟系统异常（高CPU/内存）")
    print("  - 40-90秒: 模拟系统恢复正常")
    print("  - 间隔触发: 每 30 秒进行一次 LLM 分析")
    print("  - 预期: 第30秒触发告警，第60秒不触发")
    print()

    server = "server-01"
    start_time = datetime.utcnow()

    try:
        elapsed = 0
        while elapsed < 90:
            current_time = datetime.utcnow()
            elapsed = (current_time - start_time).total_seconds()

            # 0-40秒: 系统异常
            if elapsed < 40:
                cpu = 0.85 + random.uniform(0, 0.10)  # 85-95%
                memory = 0.80 + random.uniform(0, 0.10)  # 80-90%
                disk = 0.70 + random.uniform(0, 0.10)  # 70-80%
                status = "🔴 异常"
            # 40-90秒: 系统正常
            else:
                cpu = 0.20 + random.uniform(0, 0.10)  # 20-30%
                memory = 0.40 + random.uniform(0, 0.10)  # 40-50%
                disk = 0.50 + random.uniform(0, 0.10)  # 50-60%
                status = "🟢 正常"

            await send_metric_event(
                channel, queue_name, server, cpu, memory, disk, current_time
            )

            # 检查间隔触发点
            if 29 <= elapsed < 31:
                print(f"  → 间隔触发点: {int(elapsed)}秒，应触发 LLM 分析（状态: {status}）")
            elif 59 <= elapsed < 61:
                print(f"  → 间隔触发点: {int(elapsed)}秒，应触发 LLM 分析（状态: {status}）")

            await asyncio.sleep(2)

        print()
        print("=" * 70)
        print("  测试完成！")
        print("=" * 70)
        print()
        print("📊 测试总结:")
        print("  - 阶段1 (0-40s): 系统异常 → 应在30秒时触发告警 ✓")
        print("  - 阶段2 (40-90s): 系统正常 → 不应在60秒时触发告警 ✗")
        print()
        print("🔍 调试信息:")
        print("  - 查看 Worker 日志确认间隔触发过程")
        print("  - 检查 Telegram 是否收到第30秒的告警")
        print("  - Redis 间隔状态查询:")
        print("    docker exec -it llmtrigger-redis-1 redis-cli")
        print('    GET "llmtrigger:trigger:mode:last:{rule_id}:system.metric.server-01"')
        print('    GET "llmtrigger:trigger:mode:interval_lock:{rule_id}"')
        print()

    finally:
        await connection.close()
        print("已断开 RabbitMQ 连接")
        print()


def main():
    """主函数。"""
    # 默认配置
    rabbitmq_url = "amqp://guest:guest@localhost:5672/"
    queue_name = "trigger_events"

    # 检查命令行参数
    if len(sys.argv) > 1:
        if sys.argv[1] in ["-h", "--help"]:
            print("用法:")
            print(f"  {sys.argv[0]} [RABBITMQ_URL] [QUEUE_NAME]")
            print()
            print("示例:")
            print(f"  {sys.argv[0]}")
            print(f"  {sys.argv[0]} amqp://guest:guest@localhost:5672/ trigger_events")
            print()
            print("功能:")
            print("  持续发送系统指标事件（90秒），测试 LLM 间隔触发模式")
            print()
            print("测试场景:")
            print("  - 0-40秒: 系统异常（高CPU/内存）")
            print("  - 40-90秒: 系统恢复正常")
            print("  - 间隔触发: 第30秒和第60秒应触发 LLM 分析")
            return

        rabbitmq_url = sys.argv[1]

    if len(sys.argv) > 2:
        queue_name = sys.argv[2]

    # 运行测试
    asyncio.run(send_continuous_metrics(rabbitmq_url, queue_name))


if __name__ == "__main__":
    main()
