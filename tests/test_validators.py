"""
Unit tests for bot.validators.

Run with:  python -m pytest tests/ -v
(or python -m unittest discover tests -v if pytest isn't installed)
"""

import sys
import unittest
from decimal import Decimal
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from bot.validators import ValidationError, build_order_request  # noqa: E402


class TestBuildOrderRequest(unittest.TestCase):
    def test_valid_market_order(self):
        req = build_order_request("btcusdt", "buy", "market", "0.01")
        self.assertEqual(req.symbol, "BTCUSDT")
        self.assertEqual(req.side, "BUY")
        self.assertEqual(req.order_type, "MARKET")
        self.assertEqual(req.quantity, Decimal("0.01"))
        self.assertIsNone(req.price)

    def test_valid_limit_order(self):
        req = build_order_request("ETHUSDT", "SELL", "LIMIT", "1.5", price="3500.5")
        self.assertEqual(req.order_type, "LIMIT")
        self.assertEqual(req.price, Decimal("3500.5"))

    def test_limit_order_missing_price_raises(self):
        with self.assertRaises(ValidationError):
            build_order_request("BTCUSDT", "BUY", "LIMIT", "0.01")

    def test_invalid_side_raises(self):
        with self.assertRaises(ValidationError):
            build_order_request("BTCUSDT", "HOLD", "MARKET", "0.01")

    def test_invalid_order_type_raises(self):
        with self.assertRaises(ValidationError):
            build_order_request("BTCUSDT", "BUY", "STOP", "0.01")

    def test_negative_quantity_raises(self):
        with self.assertRaises(ValidationError):
            build_order_request("BTCUSDT", "BUY", "MARKET", "-0.01")

    def test_zero_quantity_raises(self):
        with self.assertRaises(ValidationError):
            build_order_request("BTCUSDT", "BUY", "MARKET", "0")

    def test_non_numeric_quantity_raises(self):
        with self.assertRaises(ValidationError):
            build_order_request("BTCUSDT", "BUY", "MARKET", "abc")

    def test_short_symbol_raises(self):
        with self.assertRaises(ValidationError):
            build_order_request("BTC", "BUY", "MARKET", "0.01")


if __name__ == "__main__":
    unittest.main()
