from operations import add, subtract, multiply, divide


def main():
    print("Structured Calculator")

    x = int(input("Enter first number: "))
    y = int(input("Enter second number: "))

    print("Add:", add(x, y))
    print("Subtract:", subtract(x, y))
    print("Multiply:", multiply(x, y))
    print("Divide:", divide(x, y))


if __name__ == "__main__":
    main()
