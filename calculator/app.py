import argparse
import datetime

from calculator.core import calculate
from calculator.csv_tools import count_columns, count_rows
from calculator.file_tools import count_lines, count_lines_in_dir, count_words
from calculator.finance_tools import batch_summarize, summarize_csv_column
from calculator.json_tools import count_keys, pretty_print_json
from calculator.log_tools import count_errors
from calculator.utils import show_time


def build_parser():
    parser = argparse.ArgumentParser(description="Backend Foundations CLI Toolkit")
    subparsers = parser.add_subparsers(dest="command", required=True)

    calc = subparsers.add_parser("calc", help="Calculator operations")
    calc.add_argument("operation", choices=["add", "sub", "mul", "div"])
    calc.add_argument("a", type=float)
    calc.add_argument("b", type=float)

    subparsers.add_parser("time", help="Show system time")

    lines = subparsers.add_parser("lines", help="Count lines in file")
    lines.add_argument("file")

    lines_dir = subparsers.add_parser(
        "lines-dir", help="Count lines in all files in a folder"
    )
    lines_dir.add_argument("folder")

    words = subparsers.add_parser("words", help="Count words in file")
    words.add_argument("file")

    json_parser = subparsers.add_parser("json")
    json_sub = json_parser.add_subparsers(dest="action", required=True)

    json_pretty = json_sub.add_parser("pretty")
    json_pretty.add_argument("file")

    json_keys = json_sub.add_parser("keys")
    json_keys.add_argument("file")

    csv_parser = subparsers.add_parser("csv")
    csv_sub = csv_parser.add_subparsers(dest="action", required=True)

    csv_rows = csv_sub.add_parser("rows")
    csv_rows.add_argument("file")

    csv_cols = csv_sub.add_parser("cols")
    csv_cols.add_argument("file")

    log_parser = subparsers.add_parser("log")
    log_sub = log_parser.add_subparsers(dest="action", required=True)

    log_errors = log_sub.add_parser("errors")
    log_errors.add_argument("file")

    finance = subparsers.add_parser("finance", help="Financial tools")
    finance_sub = finance.add_subparsers(dest="action", required=True)

    summary = finance_sub.add_parser("summary", help="Summarize numeric column in CSV")
    summary.add_argument("file")
    summary.add_argument("column")
    summary.add_argument("--out", help="Save report to file")

    batch = finance_sub.add_parser("batch", help="Process all CSV files in a folder")
    batch.add_argument("folder")
    batch.add_argument("column")

    return parser


def format_sales_summary(file_name, column_name, result):
    return (
        "=============================================\n"
        "        SALES SUMMARY REPORT\n"
        "=============================================\n"
        f"File: {file_name}\n"
        f"Column: {column_name}\n"
        "---------------------------------------------\n"
        f"Transactions : {result['rows']}\n"
        f"Total Revenue: R{result['sum']:.2f}\n"
        f"Average Sale : R{result['average']:.2f}\n"
        f"Highest Sale : R{result['max']:.2f}\n"
        f"Lowest Sale  : R{result['min']:.2f}\n"
        "============================================="
    )


def main(argv=None):
    parser = build_parser()
    args = parser.parse_args(argv)

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
            output = format_sales_summary(args.file, args.column, result)
            print(output)

            if args.out:
                filename = args.out
            else:
                today = datetime.date.today()
                filename = f"sales_report_{today}.txt"

            with open(filename, "w", encoding="utf-8") as file_handle:
                file_handle.write(output)

            print(f"Report saved to {filename}")

        elif args.action == "batch":
            results, grand_total = batch_summarize(args.folder, args.column)

            print("\nProcessing folder:", args.folder)
            print("-" * 40)

            for file_name, total in results:
                print(f"{file_name} -> R{total:.2f}")

            print("-" * 40)
            print(f"TOTAL ACROSS FILES -> R{grand_total:.2f}")


if __name__ == "__main__":
    main()
