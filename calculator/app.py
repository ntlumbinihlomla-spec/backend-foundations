from operations import add, subtract, multiply, divide
from datetime import datetime

LOG_FILE = "logs/calculator.log"

def log(message):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with open(LOG_FILE, "a") as file:
        file.write(f"[{timestamp}] {message}\n")

def get_number(prompt):
    while True:
        try:
            return float(input(prompt))
        except ValueError:
            print("Invalid number. Try again.")

def main():
    print("Calculator")
    print("1. Add")
    print("2. Subtract")
    print("3. Multiply")
    print("4. Divide")

    choice = input("Choose an option (1-4): ")

    if choice not in {"1", "2", "3", "4"}:
        print("Invalid choice.")
        log("Invalid menu choice entered")
        return

    a = get_number("Enter first number: ")
    b = get_number("Enter second number: ")

    try:
        if choice == "1":
            result = add(a, b)
            operation = "ADD"
        elif choice == "2":
            result = subtract(a, b)
            operation = "SUBTRACT"
        elif choice == "3":
            result = multiply(a, b)
            operation = "MULTIPLY"
        elif choice == "4":
            result = divide(a, b)
            operation = "DIVIDE"

        print(f"Result: {result}")
        log(f"{operation}: {a} and {b} = {result}")

    except ValueError as e:
        print(f"Error: {e}")
        log(f"ERROR: {e}")

if __name__ == "__main__":
    main()


