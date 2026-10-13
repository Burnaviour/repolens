from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from shop.models import Order


def audited(fn):
    return fn


def money(value) -> str:
    return f"{value} EUR"


def order_label(order: "Order") -> str:
    return order.describe()
