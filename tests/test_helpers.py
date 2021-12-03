from fuo_ytmusic import helpers


class SingletonClassExample(metaclass=helpers.Singleton):
    def __init__(self):
        self.variable = 0


def test_singleton():
    o1 = SingletonClassExample()
    o1.variable = 10
    o2 = SingletonClassExample()
    assert isinstance(o1, SingletonClassExample)
    assert isinstance(o2, SingletonClassExample)
    assert id(o1) == id(o2)
    assert o1.variable == 10
    assert o2.variable == 10
