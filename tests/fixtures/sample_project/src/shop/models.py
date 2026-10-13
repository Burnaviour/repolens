"""Domain models."""


class Base:
    def describe(self) -> str:
        return type(self).__name__


class Order(Base):
    """An order with line items."""

    def __init__(self) -> None:
        self.items: list[int] = []

    def total(self) -> int:
        return self._sum()

    def _sum(self) -> int:
        self.items.append(0)
        return sum(self.items)

    @classmethod
    def empty(cls) -> "Order":
        order = cls()
        order.describe()
        return order
