from shop.service import Carrier, make_service
from shop.utils.fmt import *  # noqa: F403


def main() -> None:
    service = make_service()
    print(money(service.place(Carrier())))  # noqa: F405


if __name__ == "__main__":
    main()
