"""
Input validation for order requests.

Kept independent of any API/client code so it can be unit tested in isolation
and reused by both the CLI layer and (if added later) a UI layer.
"""

from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from typing import Optional

VALID_SIDES = {"BUY", "SELL"}
VALID_ORDER_TYPES = {"MARKET", "LIMIT"}


class ValidationError(Exception):
    """Raised when user-supplied order parameters are invalid."""


@dataclass
class OrderRequest:
    """A validated, normalized order request ready to send to the API layer."""

    symbol: str
    side: str
    order_type: str
    quantity: Decimal
    price: Optional[Decimal] = None
    time_in_force: str = "GTC"


def _to_positive_decimal(value: str, field_name: str) -> Decimal:
    try:
        dec = Decimal(str(value))
    except (InvalidOperation, TypeError):
        raise ValidationError(f"{field_name} must be a valid number, got {value!r}")
    if dec <= 0:
        raise ValidationError(f"{field_name} must be greater than 0, got {value!r}")
    return dec


def validate_symbol(symbol: str) -> str:
    if not symbol or not isinstance(symbol, str):
        raise ValidationError("symbol is required")
    symbol = symbol.strip().upper()
    if not symbol.isalnum():
        raise ValidationError(f"symbol must be alphanumeric, got {symbol!r}")
    if len(symbol) < 5:
        raise ValidationError(f"symbol looks too short to be valid, got {symbol!r}")
    return symbol


def validate_side(side: str) -> str:
    if not side or not isinstance(side, str):
        raise ValidationError("side is required")
    side = side.strip().upper()
    if side not in VALID_SIDES:
        raise ValidationError(
            f"side must be one of {sorted(VALID_SIDES)}, got {side!r}"
        )
    return side


def validate_order_type(order_type: str) -> str:
    if not order_type or not isinstance(order_type, str):
        raise ValidationError("order_type is required")
    order_type = order_type.strip().upper()
    if order_type not in VALID_ORDER_TYPES:
        raise ValidationError(
            f"order_type must be one of {sorted(VALID_ORDER_TYPES)}, got {order_type!r}"
        )
    return order_type


def build_order_request(
    symbol: str,
    side: str,
    order_type: str,
    quantity: str,
    price: Optional[str] = None,
    time_in_force: str = "GTC",
) -> OrderRequest:
    """
    Validate all raw CLI input and return a normalized OrderRequest.

    Raises ValidationError with a human-readable message on any problem.
    """
    symbol = validate_symbol(symbol)
    side = validate_side(side)
    order_type = validate_order_type(order_type)
    qty = _to_positive_decimal(quantity, "quantity")

    price_dec: Optional[Decimal] = None
    if order_type == "LIMIT":
        if price is None:
            raise ValidationError("price is required for LIMIT orders")
        price_dec = _to_positive_decimal(price, "price")
    else:
        if price is not None:
            # Not an error, just ignored — MARKET orders don't take a price.
            price_dec = None

    return OrderRequest(
        symbol=symbol,
        side=side,
        order_type=order_type,
        quantity=qty,
        price=price_dec,
        time_in_force=time_in_force,
    )
