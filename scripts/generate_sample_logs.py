#!/usr/bin/env python3
"""
Generate illustrative sample log entries (logs/sample_bot.log) showing what
successful MARKET and LIMIT order runs look like end-to-end.

This exercises the real client/orders/logging code paths with the HTTP layer
stubbed to return realistic Binance response payloads — used only because
some sandboxed dev environments don't have network egress to
testnet.binancefuture.com. Run the actual CLI (cli.py) with real testnet
credentials to produce a genuine first-party log.
"""

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from bot.client import FuturesTestnetClient  # noqa: E402
from bot.logging_config import setup_logging  # noqa: E402
from bot.orders import place_order  # noqa: E402
from bot.validators import build_order_request  # noqa: E402


def fake_response(payload, status=200):
    resp = MagicMock()
    resp.status_code = status
    resp.ok = status < 400
    resp.json.return_value = payload
    resp.text = str(payload)
    return resp


def main():
    logger = setup_logging()
    logger.info("=== SAMPLE RUN \u2014 simulated responses (no live network in this sandbox) ===")

    client = FuturesTestnetClient(api_key="sample_testnet_key", api_secret="sample_testnet_secret")

    market_payload = {
        "orderId": 3450001234,
        "symbol": "BTCUSDT",
        "status": "FILLED",
        "clientOrderId": "sample-market-1",
        "price": "0",
        "avgPrice": "67540.20",
        "origQty": "0.010",
        "executedQty": "0.010",
        "cumQuote": "675.40",
        "timeInForce": "GTC",
        "type": "MARKET",
        "side": "BUY",
    }
    with patch.object(client.session, "request", return_value=fake_response(market_payload)):
        req = build_order_request("BTCUSDT", "BUY", "MARKET", "0.01")
        place_order(client, req)

    limit_payload = {
        "orderId": 3450005678,
        "symbol": "ETHUSDT",
        "status": "NEW",
        "clientOrderId": "sample-limit-1",
        "price": "3500.50",
        "avgPrice": "0.00",
        "origQty": "1.000",
        "executedQty": "0.000",
        "cumQuote": "0.00",
        "timeInForce": "GTC",
        "type": "LIMIT",
        "side": "SELL",
    }
    with patch.object(client.session, "request", return_value=fake_response(limit_payload)):
        req = build_order_request("ETHUSDT", "SELL", "LIMIT", "1", price="3500.50")
        place_order(client, req)

    logger.info("=== END SAMPLE RUN ===")


if __name__ == "__main__":
    main()
