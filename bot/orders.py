"""
Order placement orchestration.

Sits between the CLI layer and the API client layer:
  - takes a validated OrderRequest
  - logs a human-readable request summary
  - calls the client
  - normalizes/logs the response
  - returns a simple result object the CLI can print
"""

from dataclasses import dataclass
from typing import Any, Dict, Optional

from bot.client import BinanceAPIError, BinanceNetworkError, FuturesTestnetClient
from bot.logging_config import get_logger
from bot.validators import OrderRequest

logger = get_logger()


@dataclass
class OrderResult:
    success: bool
    order_id: Optional[int] = None
    status: Optional[str] = None
    executed_qty: Optional[str] = None
    avg_price: Optional[str] = None
    raw_response: Optional[Dict[str, Any]] = None
    error_message: Optional[str] = None


def place_order(client: FuturesTestnetClient, request: OrderRequest) -> OrderResult:
    """
    Place a single order and return a normalized OrderResult.

    Never raises: all client/network errors are caught and returned as a
    failed OrderResult so the CLI can present a clean success/failure message.
    """
    summary = (
        f"symbol={request.symbol} side={request.side} type={request.order_type} "
        f"quantity={request.quantity}" + (f" price={request.price}" if request.price else "")
    )
    logger.info("Order request: %s", summary)

    try:
        response = client.place_order(
            symbol=request.symbol,
            side=request.side,
            order_type=request.order_type,
            quantity=str(request.quantity),
            price=str(request.price) if request.price is not None else None,
            time_in_force=request.time_in_force,
        )
    except BinanceAPIError as exc:
        logger.error("Order FAILED (API error): %s", exc)
        return OrderResult(success=False, error_message=str(exc))
    except BinanceNetworkError as exc:
        logger.error("Order FAILED (network error): %s", exc)
        return OrderResult(success=False, error_message=f"Network error: {exc}")
    except Exception as exc:  # noqa: BLE001 - final safety net, never crash the CLI
        logger.exception("Order FAILED (unexpected error)")
        return OrderResult(success=False, error_message=f"Unexpected error: {exc}")

    result = OrderResult(
        success=True,
        order_id=response.get("orderId"),
        status=response.get("status"),
        executed_qty=response.get("executedQty"),
        avg_price=response.get("avgPrice"),
        raw_response=response,
    )
    logger.info(
        "Order SUCCESS: orderId=%s status=%s executedQty=%s avgPrice=%s",
        result.order_id,
        result.status,
        result.executed_qty,
        result.avg_price,
    )
    return result
