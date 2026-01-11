#!/usr/bin/env python3
"""发送交易信号事件到 RabbitMQ 的脚本。

用于测试 LLM 批量触发模式的聚合分析能力。
"""

import asyncio
import json
import sys
from datetime import datetime, timedelta
from uuid import uuid4

import aio_pika
from aio_pika import DeliveryMode, Message


async def send_trade_signal(
    channel: aio_pika.abc.AbstractChannel,
    queue_name: str,
    symbol: str,
    signal: str,
    volume: float,
    price: float,
    timestamp: datetime,
) -> None:
    """发送单个交易信号事件到 RabbitMQ。

    Args:
        channel: RabbitMQ 通道
        queue_name: 队列名称
        symbol: 交易对符号
        signal: 信号类型 (buy/sell)
        volume: 交易量
        price: 价格
        timestamp: 时间戳
    """
    event_id = str(uuid4())
    context_key = f"trade.signal.{symbol}"

    event = {
        "event_id": event_id,
        "event_type": "trade.signal",
        "context_key": context_key,
        "timestamp": timestamp.isoformat(),
        "data": {
            "symbol": symbol,
            "signal": signal,
            "volume": volume,
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

    print(
        f"✓ 发送交易信号: {symbol} {signal.upper()} "
        f"volume=${volume:,.0f} @ ${price:,.2f} ({timestamp.strftime('%H:%M:%S')})"
    )


async def scenario_strong_buy_signals(
    channel: aio_pika.abc.AbstractChannel,
    queue_name: str,
) -> None:
    """场景1: 连续买入信号，高交易量（应触发告警）。

    模拟 6 个连续的买入信号，总交易量约 90 万 USDT
    批量触发：累积到 5 个事件后触发 LLM 分析
    """
    print("\n" + "=" * 70)
    print("📊 场景1: 连续买入信号，高交易量（应触发批量告警）")
    print("=" * 70)
    print()

    symbol = "BTCUSDT"
    base_time = datetime.utcnow()
    base_price = 50000.0

    signals = [
        {"signal": "buy", "volume": 100000, "price_offset": 0},
        {"signal": "buy", "volume": 150000, "price_offset": 100},
        {"signal": "buy", "volume": 120000, "price_offset": 150},
        {"signal": "buy", "volume": 180000, "price_offset": 200},
        {"signal": "buy", "volume": 200000, "price_offset": 250},  # 第5个，触发批量分析
        {"signal": "buy", "volume": 150000, "price_offset": 300},
    ]

    total_volume = sum(s["volume"] for s in signals)

    print(f"交易对: {symbol}")
    print(f"信号数量: {len(signals)} 个连续买入信号")
    print(f"总交易量: ${total_volume:,.0f}")
    print(f"批量触发: 累积到 5 个事件后触发 LLM 分析")
    print()

    for i, sig in enumerate(signals, 1):
        timestamp = base_time + timedelta(seconds=i * 5)
        price = base_price + sig["price_offset"]

        await send_trade_signal(
            channel, queue_name, symbol, sig["signal"], sig["volume"], price, timestamp
        )

        if i == 5:
            print("  → 批量大小已达到 5，应触发 LLM 分析")

        await asyncio.sleep(0.5)

    print()
    print("✅ 场景1 完成 - 预期批量触发 LLM 分析并发送告警")
    print()


async def scenario_mixed_signals(
    channel: aio_pika.abc.AbstractChannel,
    queue_name: str,
) -> None:
    """场景2: 混合信号，低交易量（不应触发告警）。

    模拟买入和卖出信号混合，总交易量约 12 万 USDT
    批量触发：累积到 5 个事件后触发 LLM 分析
    """
    print("\n" + "=" * 70)
    print("🔀 场景2: 混合信号，低交易量（不应触发告警）")
    print("=" * 70)
    print()

    symbol = "ETHUSDT"
    base_time = datetime.utcnow()
    base_price = 3000.0

    signals = [
        {"signal": "buy", "volume": 10000, "price_offset": 0},
        {"signal": "sell", "volume": 15000, "price_offset": -20},
        {"signal": "buy", "volume": 20000, "price_offset": 10},
        {"signal": "sell", "volume": 25000, "price_offset": -30},
        {"signal": "buy", "volume": 30000, "price_offset": 5},  # 第5个，触发批量分析
        {"signal": "sell", "volume": 20000, "price_offset": -10},
    ]

    total_volume = sum(s["volume"] for s in signals)
    buy_count = sum(1 for s in signals if s["signal"] == "buy")
    sell_count = sum(1 for s in signals if s["signal"] == "sell")

    print(f"交易对: {symbol}")
    print(f"信号数量: {len(signals)} 个信号 ({buy_count} 买 / {sell_count} 卖)")
    print(f"总交易量: ${total_volume:,.0f}")
    print(f"批量触发: 累积到 5 个事件后触发 LLM 分析")
    print()

    for i, sig in enumerate(signals, 1):
        timestamp = base_time + timedelta(seconds=i * 5)
        price = base_price + sig["price_offset"]

        await send_trade_signal(
            channel, queue_name, symbol, sig["signal"], sig["volume"], price, timestamp
        )

        if i == 5:
            print("  → 批量大小已达到 5，应触发 LLM 分析")

        await asyncio.sleep(0.5)

    print()
    print("✅ 场景2 完成 - 预期 LLM 识别出信号混乱且交易量低，不触发告警")
    print()


async def scenario_timeout_trigger(
    channel: aio_pika.abc.AbstractChannel,
    queue_name: str,
) -> None:
    """场景3: 缓慢累积后超时触发（应触发告警）。

    模拟 3 个强烈买入信号，交易量巨大（总计 120 万 USDT）
    未达到批量大小 5，但等待 35 秒后超时触发
    """
    print("\n" + "=" * 70)
    print("⏰ 场景3: 缓慢累积后超时触发（应触发告警）")
    print("=" * 70)
    print()

    symbol = "BTCUSDT"
    base_time = datetime.utcnow()
    base_price = 51000.0

    signals = [
        {"signal": "buy", "volume": 300000, "price_offset": 0},
        {"signal": "buy", "volume": 400000, "price_offset": 200},
        {"signal": "buy", "volume": 500000, "price_offset": 400},
    ]

    total_volume = sum(s["volume"] for s in signals)

    print(f"交易对: {symbol}")
    print(f"信号数量: {len(signals)} 个强烈买入信号（未达到 batch_size=5）")
    print(f"总交易量: ${total_volume:,.0f}（非常高）")
    print(f"超时触发: 等待 35 秒后应触发 LLM 分析（max_wait_seconds=30）")
    print()

    for i, sig in enumerate(signals, 1):
        timestamp = base_time + timedelta(seconds=i * 10)
        price = base_price + sig["price_offset"]

        await send_trade_signal(
            channel, queue_name, symbol, sig["signal"], sig["volume"], price, timestamp
        )
        await asyncio.sleep(0.5)

    print()
    print("⏳ 等待 35 秒，测试超时触发机制...")
    print("   (max_wait_seconds=30，批量大小 3 < batch_size 5)")

    # 等待超时触发
    await asyncio.sleep(35)

    print()
    print("✅ 场景3 完成 - 预期超时后 LLM 分析并发送告警")
    print()


async def send_test_scenarios(rabbitmq_url: str, queue_name: str) -> None:
    """发送所有测试场景的交易信号事件。

    Args:
        rabbitmq_url: RabbitMQ 连接 URL
        queue_name: 队列名称
    """
    # 连接 RabbitMQ
    connection = await aio_pika.connect_robust(rabbitmq_url)
    channel = await connection.channel()

    print()
    print("=" * 70)
    print("  LLM 批量触发模式测试")
    print("=" * 70)
    print()
    print(f"已连接到 RabbitMQ: {rabbitmq_url}")
    print(f"目标队列: {queue_name}")
    print()

    try:
        # 场景1: 连续买入信号，高交易量（应触发）
        await scenario_strong_buy_signals(channel, queue_name)
        print("⏸️  等待 10 秒后继续下一场景...")
        await asyncio.sleep(10)

        # 场景2: 混合信号，低交易量（不应触发）
        await scenario_mixed_signals(channel, queue_name)
        print("⏸️  等待 10 秒后继续下一场景...")
        await asyncio.sleep(10)

        # 场景3: 缓慢累积后超时触发（应触发）
        await scenario_timeout_trigger(channel, queue_name)

        print()
        print("=" * 70)
        print("  所有测试场景完成！")
        print("=" * 70)
        print()
        print("📊 测试总结:")
        print("  - 场景1: 连续买入信号，总量90万 → 应批量触发告警 ✓")
        print("  - 场景2: 混合信号，总量12万 → 不应触发 ✗")
        print("  - 场景3: 3个强烈买入，总量120万 → 应超时触发告警 ✓")
        print()
        print("🔍 调试信息:")
        print("  - 查看 Worker 日志确认批量触发过程")
        print("  - 检查 Telegram 是否收到场景1和场景3的告警")
        print("  - Redis 批量状态查询:")
        print("    docker exec -it llmtrigger-redis-1 redis-cli")
        print('    KEYS "llmtrigger:trigger:mode:batch:*"')
        print('    LRANGE "llmtrigger:trigger:mode:batch:{rule_id}:trade.signal.*" 0 -1')
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
            print("  发送一系列交易信号事件，测试 LLM 批量触发模式的聚合分析能力")
            print()
            print("测试场景:")
            print("  1. 连续买入信号，高交易量 - 应批量触发告警")
            print("  2. 混合信号，低交易量 - 不应触发")
            print("  3. 缓慢累积后超时触发 - 应触发告警")
            return

        rabbitmq_url = sys.argv[1]

    if len(sys.argv) > 2:
        queue_name = sys.argv[2]

    # 运行测试
    asyncio.run(send_test_scenarios(rabbitmq_url, queue_name))


if __name__ == "__main__":
    main()
