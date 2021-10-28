import lefi
import random


class FakeObj:
    def __init__(self, id: int, name: str) -> None:
        self.name = name
        self.id = id


def test_get_one() -> None:
    look_through = [FakeObj(id_, "test") for id_ in range(10)]

    res = lefi.utils.get(look_through, id=0)
    assert res is not None and res.id == 0


def test_get_multi() -> None:
    look_through = [FakeObj(id_, name) for id_, name in zip(range(3), ["A", "B", "C"])]

    res = lefi.utils.get(look_through, id=0, name="A")
    assert res is not None and res.id == 0 and res.name == "A"
