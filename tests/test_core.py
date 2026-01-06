from calculator.core import calculate

def test_add():
    result, op = calculate("1", 2, 3)
    assert result == 5
    assert op == "ADD"

def test_subtract():
    result, op = calculate("2", 10, 4)
    assert result == 6
    assert op == "SUBTRACT"

def test_multiply():
    result, op = calculate("3", 3, 5)
    assert result == 15
    assert op == "MULTIPLY"

def test_divide():
    result, op = calculate("4", 20, 4)
    assert result == 5
    assert op == "DIVIDE"

def test_invalid_choice():
    try:
        calculate("9", 1, 1)
        assert False  # should not reach here
    except ValueError:
        assert True
