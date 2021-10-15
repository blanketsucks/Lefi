from __future__ import annotations


class A:
    def __init__(self):
        self.funcs = []

    def register(self):
        def inner(func):
            self.funcs.append(func)
            print(func.im_class)
            return func

        return inner


a = A()


class B:
    @a.register()
    def test(self):
        ...
