import lefi


def test_flags():
    flag = lefi.UserFlags(131141)
    assert flag.items() == list(flag)

    intents = lefi.Intents.all()
    assert intents.items() == list(intents)
