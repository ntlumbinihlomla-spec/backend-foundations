from datetime import datetime
from core import calculate

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

    a = get_number("Enter first number: ")
    b = get_number("Enter second number: ")

    try:
        result, operation = calculate(choice, a, b)
        print(f"Result: {result}")
        log(f"{operation}: {a} and {b} = {result}")

    except Exception as e:
        print(f"Error: {e}")
        log(f"ERROR: {e}")

if __name__ == "__main__":
    main()



