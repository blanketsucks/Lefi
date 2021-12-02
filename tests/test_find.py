import lefi


class FakeObj:
    def __init__(self, id: int, name: str) -> None:
        self.name = name
        self.id = id


def test_find() -> None:
    look_through = [FakeObj(id_, "test") for id_ in range(10)]
    res = lefi.utils.find(look_through, lambda o: o.id == 0)

    if not isinstance(res, list):
        assert res is not None and res.id == 0


def test_find_list() -> None:
    look_through = [FakeObj(id_, name) for id_, name in zip(range(4), ["A", "A", "B", "B"])]
    res = lefi.utils.find(look_through, lambda o: o.id < 3 and o.name == "A")

    assert isinstance(res, list)
    for item in res:
        assert item.id < 3 and item.name == "A"
