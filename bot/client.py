"""
Thin wrapper around the Binance USDT-M Futures Testnet REST API.

Implemented with direct REST calls (requests + HMAC-SHA256 signing) rather
than the python-binance library so that every request/response can be
logged explicitly and the signing logic is fully transparent.

Docs: https://binance-docs.github.io/apidocs/testnet/en/
Base URL: https://testnet.binancefuture.com
"""

import hashlib
import hmac
import re
import time
from typing import Any, Dict, Optional
from urllib.parse import urlencode

import requests

from bot.logging_config import get_logger

logger = get_logger()

_SIGNATURE_RE = re.compile(r"(signature=)[0-9a-fA-F]{16,}")


class BinanceAPIError(Exception):
    """Raised when Binance returns a non-2xx response with an error payload."""

    def __init__(self, status_code: int, code: Optional[int], message: str):
        self.status_code = status_code
        self.code = code
        self.message = message
        super().__init__(f"[HTTP {status_code}] Binance error {code}: {message}")


class BinanceNetworkError(Exception):
    """Raised when the request could not reach Binance at all (timeout, DNS, etc.)."""


class FuturesTestnetClient:
    """
    Minimal client for placing/inspecting orders on Binance Futures Testnet.

    Only the endpoints needed by this bot are implemented:
      - GET  /fapi/v1/ping           (connectivity check)
      - GET  /fapi/v1/time           (server time, for clock-skew safe signing)
      - GET  /fapi/v2/account        (sanity check auth works)
      - POST /fapi/v1/order          (place MARKET / LIMIT orders)
      - GET  /fapi/v1/order          (query order status)
    """

    BASE_URL = "https://testnet.binancefuture.com"
    RECV_WINDOW_MS = 5000
    TIMEOUT_S = 10

    def __init__(self, api_key: str, api_secret: str, base_url: Optional[str] = None):
        if not api_key or not api_secret:
            raise ValueError("api_key and api_secret must be provided")
        self.api_key = api_key
        self.api_secret = api_secret.encode("utf-8")
        self.base_url = base_url or self.BASE_URL
        self.session = requests.Session()
        self.session.headers.update({"X-MBX-APIKEY": self.api_key})


    def _sign(self, params: Dict[str, Any]) -> Dict[str, Any]:
        params = dict(params)
        params["timestamp"] = int(time.time() * 1000)
        params["recvWindow"] = self.RECV_WINDOW_MS
        query_string = urlencode(params, doseq=True)
        signature = hmac.new(self.api_secret, query_string.encode("utf-8"), hashlib.sha256).hexdigest()
        params["signature"] = signature
        return params

    def _request(
        self,
        method: str,
        path: str,
        params: Optional[Dict[str, Any]] = None,
        signed: bool = False,
    ) -> Dict[str, Any]:
        url = f"{self.base_url}{path}"
        params = params or {}

        if signed:
            params = self._sign(params)

        logger.debug("REQUEST %s %s params=%s", method, url, _redact(params))

        try:
            response = self.session.request(method, url, params=params, timeout=self.TIMEOUT_S)
        except requests.exceptions.RequestException as exc:
            safe_exc_msg = _redact_signature_in_text(str(exc))
            logger.error("NETWORK ERROR calling %s %s: %s", method, url, safe_exc_msg)
            raise BinanceNetworkError(safe_exc_msg) from exc

        logger.debug("RESPONSE %s %s status=%s body=%s", method, url, response.status_code, response.text)

        try:
            payload = response.json()
        except ValueError:
            payload = {"raw": response.text}

        if not response.ok:
            code = payload.get("code") if isinstance(payload, dict) else None
            msg = payload.get("msg") if isinstance(payload, dict) else None
            if not msg:
                # Non-JSON error body (e.g. a proxy/WAF page) — surface raw text instead of masking it.
                msg = payload.get("raw") if isinstance(payload, dict) else str(payload)
            msg = msg or response.text or "Unknown error"
            logger.error("API ERROR %s %s -> HTTP %s code=%s msg=%s", method, url, response.status_code, code, msg)
            raise BinanceAPIError(response.status_code, code, msg)

        return payload


    def ping(self) -> bool:
        self._request("GET", "/fapi/v1/ping")
        return True

    def server_time(self) -> int:
        data = self._request("GET", "/fapi/v1/time")
        return data["serverTime"]

    def account_info(self) -> Dict[str, Any]:
        return self._request("GET", "/fapi/v2/account", signed=True)

    def get_symbol_price(self, symbol: str) -> Dict[str, Any]:
        return self._request("GET", "/fapi/v1/ticker/price", params={"symbol": symbol})



    def place_order(
        self,
        symbol: str,
        side: str,
        order_type: str,
        quantity: str,
        price: Optional[str] = None,
        time_in_force: str = "GTC",
    ) -> Dict[str, Any]:
        """
        Place an order on Futures Testnet.

        For MARKET orders, `price` and `time_in_force` are ignored (Binance
        does not accept a TIF for MARKET orders).
        """
        params: Dict[str, Any] = {
            "symbol": symbol,
            "side": side,
            "type": order_type,
            "quantity": quantity,
        }

        if order_type == "LIMIT":
            if price is None:
                raise ValueError("price is required for LIMIT orders")
            params["price"] = price
            params["timeInForce"] = time_in_force

        return self._request("POST", "/fapi/v1/order", params=params, signed=True)

    def get_order(self, symbol: str, order_id: int) -> Dict[str, Any]:
        return self._request(
            "GET",
            "/fapi/v1/order",
            params={"symbol": symbol, "orderId": order_id},
            signed=True,
        )


def _redact(params: Dict[str, Any]) -> Dict[str, Any]:
    """Never log the signature in full — keep logs safe to share."""
    redacted = dict(params)
    if "signature" in redacted:
        redacted["signature"] = redacted["signature"][:6] + "...redacted"
    return redacted


def _redact_signature_in_text(text: str) -> str:
    """Strip a full-length hex signature out of free-text (e.g. exception messages/URLs)."""
    return _SIGNATURE_RE.sub(r"\1[redacted]", text)
