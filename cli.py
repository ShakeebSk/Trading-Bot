#!/usr/bin/env python3
"""
CLI entry point for the simplified Binance Futures Testnet trading bot.

Examples
--------
Market order:
    python cli.py --symbol BTCUSDT --side BUY --type MARKET --quantity 0.01

Limit order:
    python cli.py --symbol BTCUSDT --side SELL --type LIMIT --quantity 0.01 --price 70000

Credentials are read from environment variables BINANCE_API_KEY /
BINANCE_API_SECRET (or a .env file — see README), or can be passed with
--api-key / --api-secret for a one-off run.
"""

import argparse
import os
import sys
from pathlib import Path

# Allow running as `python cli.py` from the project root.
sys.path.insert(0, str(Path(__file__).resolve().parent))

from bot.client import FuturesTestnetClient  # noqa: E402
from bot.logging_config import setup_logging  # noqa: E402
from bot.orders import place_order  # noqa: E402
from bot.validators import ValidationError, build_order_request  # noqa: E402

try:
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:
    pass  # python-dotenv is optional; env vars can be set directly


def parse_args(argv=None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="cli.py",
        description="Place MARKET or LIMIT orders on Binance Futures Testnet (USDT-M).",
    )
    parser.add_argument("--symbol", required=True, help="Trading pair, e.g. BTCUSDT")
    parser.add_argument(
        "--side",
        required=True,
        choices=["BUY", "SELL", "buy", "sell"],
        help="Order side",
    )
    parser.add_argument(
        "--type",
        dest="order_type",
        required=True,
        choices=["MARKET", "LIMIT", "market", "limit"],
        help="Order type",
    )
    parser.add_argument("--quantity", required=True, help="Order quantity, e.g. 0.01")
    parser.add_argument(
        "--price", required=False, help="Limit price (required for LIMIT orders)"
    )
    parser.add_argument(
        "--time-in-force",
        default="GTC",
        choices=["GTC", "IOC", "FOK"],
        help="Time in force for LIMIT orders (default: GTC)",
    )
    parser.add_argument(
        "--api-key",
        default=os.getenv("BINANCE_API_KEY"),
        help="Overrides BINANCE_API_KEY env var",
    )
    parser.add_argument(
        "--api-secret",
        default=os.getenv("BINANCE_API_SECRET"),
        help="Overrides BINANCE_API_SECRET env var",
    )
    parser.add_argument(
        "--base-url",
        default=os.getenv("BINANCE_BASE_URL", "https://testnet.binancefuture.com"),
        help="API base URL (default: Futures Testnet)",
    )
    return parser.parse_args(argv)


def print_summary(request) -> None:
    print("\n--- Order Request Summary ---")
    print(f"  Symbol:        {request.symbol}")
    print(f"  Side:          {request.side}")
    print(f"  Type:          {request.order_type}")
    print(f"  Quantity:      {request.quantity}")
    if request.price is not None:
        print(f"  Price:         {request.price}")
        print(f"  Time in force: {request.time_in_force}")
    print("------------------------------\n")


def print_result(result) -> None:
    if result.success:
        print("--- Order Response ---")
        print(f"  Order ID:      {result.order_id}")
        print(f"  Status:        {result.status}")
        print(f"  Executed Qty:  {result.executed_qty}")
        print(f"  Avg Price:     {result.avg_price}")
        print("-----------------------")
        print("\n SUCCESS: order placed.\n")
    else:
        print("\n FAILED: order was not placed.")
        print(f"   Reason: {result.error_message}\n")


def main(argv=None) -> int:
    logger = setup_logging()
    args = parse_args(argv)

    # --- Validate input ---
    try:
        order_request = build_order_request(
            symbol=args.symbol,
            side=args.side,
            order_type=args.order_type,
            quantity=args.quantity,
            price=args.price,
            time_in_force=args.time_in_force,
        )
    except ValidationError as exc:
        logger.error("Validation failed: %s", exc)
        print(f"\n Invalid input: {exc}\n")
        return 1

    if not args.api_key or not args.api_secret:
        msg = (
            "Missing API credentials. Set BINANCE_API_KEY and BINANCE_API_SECRET "
            "environment variables (or pass --api-key/--api-secret)."
        )
        logger.error(msg)
        print(f"\n {msg}\n")
        return 1

    print_summary(order_request)

    # --- Place order ---
    client = FuturesTestnetClient(
        api_key=args.api_key, api_secret=args.api_secret, base_url=args.base_url
    )
    result = place_order(client, order_request)
    print_result(result)

    return 0 if result.success else 2


if __name__ == "__main__":
    sys.exit(main())
