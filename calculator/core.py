from calculator.operations import add, subtract, multiply, divide


def calculate(operation, a, b):
    if operation == "add":
        return add(a, b)
    elif operation == "sub":
        return subtract(a, b)
    elif operation == "mul":
        return multiply(a, b)
    elif operation == "div":
        return divide(a, b)
    else:
        raise ValueError("Invalid operation")
