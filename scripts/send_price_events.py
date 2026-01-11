#!/usr/bin/env python3
"""发送价格更新事件到 RabbitMQ 的脚本。

用于测试 LLM 规则引擎的时序分析能力。
"""

import asyncio
import json
import sys
from datetime import datetime, timedelta
from uuid import uuid4

import aio_pika
from aio_pika import DeliveryMode, Message


async def send_price_event(
    channel: aio_pika.abc.AbstractChannel,
    queue_name: str,
    symbol: str,
    price: float,
    timestamp: datetime,
) -> None:
    """发送单个价格更新事件到 RabbitMQ。

    Args:
        channel: RabbitMQ 通道
        queue_name: 队列名称
        symbol: 交易对符号
        price: 价格
        timestamp: 时间戳
    """
    event_id = str(uuid4())
    context_key = f"price.update.{symbol}"

    event = {
        "event_id": event_id,
        "event_type": "price.update",
        "context_key": context_key,
        "timestamp": timestamp.isoformat(),
        "data": {
            "symbol": symbol,
            "price": price,
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

    print(f"✓ 发送价格事件: {symbol} @ ${price:,.2f} ({timestamp.strftime('%H:%M:%S')})")


async def scenario_rapid_drop(
    channel: aio_pika.abc.AbstractChannel,
    queue_name: str,
) -> None:
    """场景1: 价格快速下跌超过5%（应触发告警）。

    模拟 BTCUSDT 价格在 5 分钟内从 $50,000 跌至 $47,000（-6%）
    """
    print("\n" + "=" * 70)
    print("📉 场景1: 价格快速下跌超过5%（应触发 LLM 规则）")
    print("=" * 70)
    print()

    symbol = "BTCUSDT"
    start_price = 50000.0
    end_price = 47000.0  # 下跌 6%
    num_events = 6
    base_time = datetime.utcnow()

    prices = [
        start_price - (start_price - end_price) * (i / (num_events - 1))
        for i in range(num_events)
    ]

    print(f"初始价格: ${start_price:,.2f}")
    print(f"最终价格: ${end_price:,.2f}")
    print(f"跌幅: {((end_price - start_price) / start_price * 100):.2f}%")
    print(f"时间跨度: 5 分钟")
    print()

    for i, price in enumerate(prices):
        timestamp = base_time + timedelta(seconds=i * 60)  # 每分钟一个事件
        await send_price_event(channel, queue_name, symbol, price, timestamp)
        await asyncio.sleep(0.5)

    print()
    print("✅ 场景1 完成 - 预期 LLM 应识别出价格快速下跌并触发告警")
    print()


async def scenario_slow_drop(
    channel: aio_pika.abc.AbstractChannel,
    queue_name: str,
) -> None:
    """场景2: 价格缓慢下跌（不应触发告警）。

    模拟 ETHUSDT 价格在 5 分钟内从 $3,000 跌至 $2,950（-1.67%）
    """
    print("\n" + "=" * 70)
    print("📊 场景2: 价格缓慢下跌（不应触发告警）")
    print("=" * 70)
    print()

    symbol = "ETHUSDT"
    start_price = 3000.0
    end_price = 2950.0  # 下跌 1.67%
    num_events = 6
    base_time = datetime.utcnow()

    prices = [
        start_price - (start_price - end_price) * (i / (num_events - 1))
        for i in range(num_events)
    ]

    print(f"初始价格: ${start_price:,.2f}")
    print(f"最终价格: ${end_price:,.2f}")
    print(f"跌幅: {((end_price - start_price) / start_price * 100):.2f}%")
    print(f"时间跨度: 5 分钟")
    print()

    for i, price in enumerate(prices):
        timestamp = base_time + timedelta(seconds=i * 60)
        await send_price_event(channel, queue_name, symbol, price, timestamp)
        await asyncio.sleep(0.5)

    print()
    print("✅ 场景2 完成 - 预期 LLM 不应触发告警（跌幅不足5%）")
    print()


async def scenario_price_surge(
    channel: aio_pika.abc.AbstractChannel,
    queue_name: str,
) -> None:
    """场景3: 价格快速上涨（不应触发告警）。

    模拟 SOLUSDT 价格在 5 分钟内从 $100 涨至 $108（+8%）
    """
    print("\n" + "=" * 70)
    print("📈 场景3: 价格快速上涨（不应触发告警）")
    print("=" * 70)
    print()

    symbol = "SOLUSDT"
    start_price = 100.0
    end_price = 108.0  # 上涨 8%
    num_events = 6
    base_time = datetime.utcnow()

    prices = [
        start_price + (end_price - start_price) * (i / (num_events - 1))
        for i in range(num_events)
    ]

    print(f"初始价格: ${start_price:,.2f}")
    print(f"最终价格: ${end_price:,.2f}")
    print(f"涨幅: {((end_price - start_price) / start_price * 100):.2f}%")
    print(f"时间跨度: 5 分钟")
    print()

    for i, price in enumerate(prices):
        timestamp = base_time + timedelta(seconds=i * 60)
        await send_price_event(channel, queue_name, symbol, price, timestamp)
        await asyncio.sleep(0.5)

    print()
    print("✅ 场景3 完成 - 预期 LLM 不应触发告警（价格上涨而非下跌）")
    print()


async def scenario_volatile_drop(
    channel: aio_pika.abc.AbstractChannel,
    queue_name: str,
) -> None:
    """场景4: 波动中快速下跌（应触发告警）。

    模拟 BTCUSDT 价格波动但整体快速下跌超过5%
    """
    print("\n" + "=" * 70)
    print("⚡ 场景4: 波动中快速下跌（应触发告警）")
    print("=" * 70)
    print()

    symbol = "BTCUSDT"
    # 价格序列：有波动但整体下跌
    prices = [48000, 47800, 48100, 47500, 47200, 46900, 47000, 45500]
    base_time = datetime.utcnow()

    start_price = prices[0]
    end_price = prices[-1]

    print(f"初始价格: ${start_price:,.2f}")
    print(f"最终价格: ${end_price:,.2f}")
    print(f"跌幅: {((end_price - start_price) / start_price * 100):.2f}%")
    print(f"时间跨度: 约 {len(prices)} 分钟")
    print(f"特点: 价格波动但整体下跌")
    print()

    for i, price in enumerate(prices):
        timestamp = base_time + timedelta(seconds=i * 45)  # 每45秒一个事件
        await send_price_event(channel, queue_name, symbol, price, timestamp)
        await asyncio.sleep(0.5)

    print()
    print("✅ 场景4 完成 - 预期 LLM 应识别出整体快速下跌趋势")
    print()


async def send_test_scenarios(rabbitmq_url: str, queue_name: str) -> None:
    """发送所有测试场景的价格事件。

    Args:
        rabbitmq_url: RabbitMQ 连接 URL
        queue_name: 队列名称
    """
    # 连接 RabbitMQ
    connection = await aio_pika.connect_robust(rabbitmq_url)
    channel = await connection.channel()

    print()
    print("=" * 70)
    print("  LLM 价格异常检测测试")
    print("=" * 70)
    print()
    print(f"已连接到 RabbitMQ: {rabbitmq_url}")
    print(f"目标队列: {queue_name}")
    print()

    try:
        # 场景1: 快速下跌（应触发）
        await scenario_rapid_drop(channel, queue_name)
        print("⏸️  等待 5 秒后继续下一场景...")
        await asyncio.sleep(5)

        # 场景2: 缓慢下跌（不应触发）
        await scenario_slow_drop(channel, queue_name)
        print("⏸️  等待 5 秒后继续下一场景...")
        await asyncio.sleep(5)

        # 场景3: 价格上涨（不应触发）
        await scenario_price_surge(channel, queue_name)
        print("⏸️  等待 5 秒后继续下一场景...")
        await asyncio.sleep(5)

        # 场景4: 波动中快速下跌（应触发）
        await scenario_volatile_drop(channel, queue_name)

        print()
        print("=" * 70)
        print("  所有测试场景完成！")
        print("=" * 70)
        print()
        print("📊 测试总结:")
        print("  - 场景1: 快速下跌 6% → 应触发告警 ✓")
        print("  - 场景2: 缓慢下跌 1.67% → 不应触发 ✗")
        print("  - 场景3: 快速上涨 8% → 不应触发 ✗")
        print("  - 场景4: 波动中快速下跌 5.2% → 应触发告警 ✓")
        print()
        print("🔍 调试信息:")
        print("  - 查看 Worker 日志确认 LLM 推理过程")
        print("  - 检查 Telegram 是否收到场景1和场景4的告警")
        print("  - Redis 上下文查询:")
        print("    docker exec -it llmtrigger-redis-1 redis-cli")
        print("    KEYS llmtrigger:context:price.update.*")
        print("    LRANGE llmtrigger:context:price.update.BTCUSDT 0 -1")
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
            print("  发送一系列价格更新事件，测试 LLM 规则引擎的时序分析能力")
            print()
            print("测试场景:")
            print("  1. 快速下跌超过5% - 应触发告警")
            print("  2. 缓慢下跌 - 不应触发")
            print("  3. 快速上涨 - 不应触发")
            print("  4. 波动中快速下跌 - 应触发告警")
            return

        rabbitmq_url = sys.argv[1]

    if len(sys.argv) > 2:
        queue_name = sys.argv[2]

    # 运行测试
    asyncio.run(send_test_scenarios(rabbitmq_url, queue_name))


if __name__ == "__main__":
    main()
