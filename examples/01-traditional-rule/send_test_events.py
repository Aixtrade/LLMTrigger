#!/usr/bin/env python3
"""发送测试事件到 RabbitMQ 的脚本。

用于端到端测试整个事件处理流程。
"""

import asyncio
import json
import sys
from datetime import datetime
from uuid import uuid4

import aio_pika
from aio_pika import DeliveryMode, Message


async def send_event(
    channel: aio_pika.abc.AbstractChannel,
    queue_name: str,
    event_type: str,
    context_key: str,
    data: dict,
) -> None:
    """发送单个事件到 RabbitMQ。

    Args:
        channel: RabbitMQ 通道
        queue_name: 队列名称
        event_type: 事件类型
        context_key: 上下文分组键
        data: 事件数据
    """
    event_id = str(uuid4())
    event = {
        "event_id": event_id,
        "event_type": event_type,
        "context_key": context_key,
        "timestamp": datetime.utcnow().isoformat(),
        "data": data,
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

    print(f"✓ 发送事件: {event_id}")
    print(f"  类型: {event_type}")
    print(f"  上下文: {context_key}")
    print(f"  数据: {json.dumps(data, ensure_ascii=False)}")
    print()


async def send_test_events(rabbitmq_url: str, queue_name: str) -> None:
    """发送一系列测试事件。

    Args:
        rabbitmq_url: RabbitMQ 连接 URL
        queue_name: 队列名称
    """
    # 连接 RabbitMQ
    connection = await aio_pika.connect_robust(rabbitmq_url)
    channel = await connection.channel()

    print(f"已连接到 RabbitMQ: {rabbitmq_url}")
    print(f"目标队列: {queue_name}")
    print("=" * 60)
    print()

    try:
        # 场景1: 发送一些盈利交易事件（触发 Traditional 规则）
        print("📊 场景1: 发送高盈利率交易事件")
        print("-" * 60)

        context_key = "trade.profit.BTCUSDT.TestStrategy"

        # 发送3个高盈利率事件（profit_rate > 0.05）
        for i in range(3):
            await send_event(
                channel=channel,
                queue_name=queue_name,
                event_type="trade.profit",
                context_key=context_key,
                data={
                    "symbol": "BTCUSDT",
                    "strategy": "TestStrategy",
                    "profit_rate": 0.08 + i * 0.02,  # 0.08, 0.10, 0.12
                    "profit_amount": 100 + i * 50,
                    "trade_id": f"trade_{i+1}",
                },
            )
            await asyncio.sleep(0.5)

        print("\n" + "=" * 60)
        print()

        # 场景2: 发送一些低盈利率事件（不应触发）
        print("📊 场景2: 发送低盈利率交易事件（不应触发）")
        print("-" * 60)

        for i in range(2):
            await send_event(
                channel=channel,
                queue_name=queue_name,
                event_type="trade.profit",
                context_key=context_key,
                data={
                    "symbol": "BTCUSDT",
                    "strategy": "TestStrategy",
                    "profit_rate": 0.02 + i * 0.01,  # 0.02, 0.03
                    "profit_amount": 20 + i * 10,
                    "trade_id": f"trade_low_{i+1}",
                },
            )
            await asyncio.sleep(0.5)

        print("\n" + "=" * 60)
        print()

        # 场景3: 触发 Hybrid 规则（需要累积多个事件）
        print("📊 场景3: 发送更多高盈利率事件（触发 Hybrid/LLM 规则）")
        print("-" * 60)

        for i in range(3):
            await send_event(
                channel=channel,
                queue_name=queue_name,
                event_type="trade.profit",
                context_key=context_key,
                data={
                    "symbol": "BTCUSDT",
                    "strategy": "TestStrategy",
                    "profit_rate": 0.06 + i * 0.015,
                    "profit_amount": 80 + i * 30,
                    "cumulative_profit": 300 + i * 100,
                    "trade_id": f"trade_batch_{i+1}",
                },
            )
            await asyncio.sleep(1)

        print("\n" + "=" * 60)
        print()
        print("✅ 所有测试事件已发送完毕！")
        print()
        print("提示:")
        print("- 查看 Worker 日志以确认事件处理情况")
        print("- 检查 Telegram 消息是否收到通知")
        print("- 使用 Redis CLI 查看上下文数据: redis-cli")
        print("  - KEYS llmtrigger:context:*")
        print("  - LRANGE llmtrigger:context:trade.profit.BTCUSDT.TestStrategy 0 -1")

    finally:
        await connection.close()
        print()
        print("已断开 RabbitMQ 连接")


async def send_custom_event(
    rabbitmq_url: str,
    queue_name: str,
    event_type: str,
    context_key: str,
    data: dict,
) -> None:
    """发送自定义事件。

    Args:
        rabbitmq_url: RabbitMQ 连接 URL
        queue_name: 队列名称
        event_type: 事件类型
        context_key: 上下文分组键
        data: 事件数据（JSON 字符串）
    """
    connection = await aio_pika.connect_robust(rabbitmq_url)
    channel = await connection.channel()

    try:
        await send_event(channel, queue_name, event_type, context_key, data)
        print("✅ 自定义事件已发送！")
    finally:
        await connection.close()


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
            print("或发送自定义事件:")
            print('  python -c "import asyncio; from send_test_events import send_custom_event; \\')
            print('    asyncio.run(send_custom_event(\\')
            print('      \'amqp://guest:guest@localhost:5672/\', \\')
            print('      \'trigger_events\', \\')
            print('      \'trade.profit\', \\')
            print('      \'trade.profit.ETHUSDT.MyStrategy\', \\')
            print('      {\'profit_rate\': 0.15, \'amount\': 200}))"')
            return

        rabbitmq_url = sys.argv[1]

    if len(sys.argv) > 2:
        queue_name = sys.argv[2]

    # 运行测试
    asyncio.run(send_test_events(rabbitmq_url, queue_name))


if __name__ == "__main__":
    main()
