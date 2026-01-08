from calculator.core import calculate


def test_add():
    assert calculate("add", 2, 3) == 5


def test_sub():
    assert calculate("sub", 5, 2) == 3


def test_mul():
    assert calculate("mul", 3, 4) == 12


def test_div():
    assert calculate("div", 8, 2) == 4
