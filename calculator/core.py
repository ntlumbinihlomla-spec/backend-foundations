from operations import add, subtract, multiply, divide

def calculate(choice, a, b):
    if choice == "1":
        return add(a, b), "ADD"
    elif choice == "2":
        return subtract(a, b), "SUBTRACT"
    elif choice == "3":
        return multiply(a, b), "MULTIPLY"
    elif choice == "4":
        return divide(a, b), "DIVIDE"
    else:
        raise ValueError("Invalid operation")
