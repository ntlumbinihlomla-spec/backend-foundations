import argparse
from calculator.core import calculate
from calculator.utils import show_time
from calculator.file_tools import count_lines, count_words, count_lines_in_dir
from calculator.json_tools import pretty_print_json, count_keys
from calculator.csv_tools import count_rows, count_columns
from calculator.log_tools import count_errors
from calculator.finance_tools import summarize_csv_column




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
    lines_dir = subparsers.add_parser("lines-dir", help="Count lines in all files in a folder")
    lines_dir.add_argument("folder")

    words = subparsers.add_parser("words", help="Count words in file")
    words.add_argument("file")

    json_parser = subparsers.add_parser("json")
    json_sub = json_parser.add_subparsers(dest="action")

    json_pretty = json_sub.add_parser("pretty")
    json_pretty.add_argument("file")

    json_keys = json_sub.add_parser("keys")
    json_keys.add_argument("file")

    csv_parser = subparsers.add_parser("csv")
    csv_sub = csv_parser.add_subparsers(dest="action")

    csv_rows = csv_sub.add_parser("rows")
    csv_rows.add_argument("file")

    csv_cols = csv_sub.add_parser("cols")
    csv_cols.add_argument("file")

    log_parser = subparsers.add_parser("log")
    log_sub = log_parser.add_subparsers(dest="action")

    log_errors = log_sub.add_parser("errors")
    log_errors.add_argument("file")

    result = summarize_csv_column(args.file, args.column)

    print(f"Rows processed: {result['rows']}")
    print(f"Total: {result['sum']:.2f}")
    print(f"Average: {result['average']:.2f}")
    print(f"Minimum: {result['min']:.2f}")
    print(f"Maximum: {result['max']:.2f}")


    args = parser.parse_args()

    if args.command == "calc":
        result = calculate(args.operation, args.a, args.b)
        print("Result:", result)

    elif args.command == "time":
        print("Time:", show_time())

    elif args.command == "lines":
        print("Lines:", count_lines(args.file))
    elif args.command == "lines-dir":
        print("Total lines:", count_lines_in_dir(args.folder))

    elif args.command == "words":
        print("Words:", count_words(args.file))

    elif args.command == "json":
        if args.action == "pretty":
            print(pretty_print_json(args.file))

        elif args.action == "keys":
            print("Keys:", count_keys(args.file))


    elif args.command == "csv":
        if args.action == "rows":
            print("Rows:", count_rows(args.file))

        elif args.action == "cols":
            print("Columns:", count_columns(args.file))


    elif args.command == "log":
        if args.action == "errors":
            print("Errors:", count_errors(args.file))

    elif args.command == "finance":
        if args.action == "summary":
         result = summarize_csv_column(args.file, args.column)
         for k, v in result.items():
            print(f"{k}: {v}")

    else:
        parser.print_help()


if __name__ == "__main__":
    main()
