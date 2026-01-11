import argparse
from calculator.core import calculate
from calculator.utils import show_time
from calculator.file_tools import count_lines, count_words



def main():
    parser = argparse.ArgumentParser(description="Backend Foundations CLI Toolkit")

    subparsers = parser.add_subparsers(dest="command")

    # Calculator
    calc = subparsers.add_parser("calc", help="Calculator operations")
    calc.add_argument("operation", choices=["add", "sub", "mul", "div"])
    calc.add_argument("a", type=float)
    calc.add_argument("b", type=float)

    # Time tool
    subparsers.add_parser("time", help="Show system time")

    # File tools
    lines = subparsers.add_parser("lines", help="Count lines in file")
    lines.add_argument("file")

    words = subparsers.add_parser("words", help="Count words in file")
    words.add_argument("file")

    args = parser.parse_args()

    if args.command == "calc":
        result = calculate(args.operation, args.a, args.b)
        print("Result:", result)

    elif args.command == "time":
        print("Time:", show_time())

    elif args.command == "lines":
        print("Lines:", count_lines(args.file))

    elif args.command == "words":
        print("Words:", count_words(args.file))

    else:
        parser.print_help()


if __name__ == "__main__":
    main()
