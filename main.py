import sys
from calculator.core import calculate

def main():
    if len(sys.argv) != 4:
        print("Usage:")
        print("  python main.py add 5 3")
        print("  python main.py sub 10 4")
        print("  python main.py mul 3 6")
        print("  python main.py div 8 2")
        return

    command = sys.argv[1].lower()
    try:
        a = float(sys.argv[2])
        b = float(sys.argv[3])
    except ValueError:
        print("Numbers must be valid.")
        return

    mapping = {
        "add": "1",
        "sub": "2",
        "mul": "3",
        "div": "4"
    }

    if command not in mapping:
        print("Unknown command.")
        return

    try:
        result, op = calculate(mapping[command], a, b)
        print(result)
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    main()
