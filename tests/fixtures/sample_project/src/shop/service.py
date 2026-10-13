from __future__ import annotations

import requests

from shop import Order
from shop.utils.fmt import audited

from .repo import OrderRepo


class Carrier:
    def dispatch_parcel(self) -> None:
        requests.post("https://example.invalid")


class OrderService:
    def __init__(self, repo: OrderRepo) -> None:
        self.repo = repo

    @audited
    def place(self, carrier) -> str:
        order = Order()
        order.total()
        carrier.dispatch_parcel()
        return self.repo.save(order)


def make_service() -> OrderService:
    return OrderService(OrderRepo())
