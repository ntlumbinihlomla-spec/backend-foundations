import argparse
from calculator.core import calculate


def main():
    parser = argparse.ArgumentParser(description="Simple CLI Calculator")

    parser.add_argument("operation", choices=["add", "sub", "mul", "div"], help="Operation to perform")
    parser.add_argument("a", type=float, help="First number")
    parser.add_argument("b", type=float, help="Second number")

    args = parser.parse_args()

    result = calculate(args.operation, args.a, args.b)
    print(f"Result: {result}")


if __name__ == "__main__":
    main()
