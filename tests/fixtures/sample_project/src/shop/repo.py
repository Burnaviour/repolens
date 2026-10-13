import json

from shop.models import Order


class OrderRepo:
    def save(self, order: Order) -> str:
        return json.dumps({"total": order.total()})
