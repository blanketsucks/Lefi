import lefi


class FakeMessage:
    def __init__(self, id: int):
        self.id = id


def test_cache_maxlen():
    cache = lefi.Cache[FakeMessage](10)
    for i in range(11):
        cache[i] = FakeMessage(i)

    assert len(cache) == 10
