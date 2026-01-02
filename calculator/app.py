from operations import add, subtract, multiply, divide

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
        return

    a = get_number("Enter first number: ")
    b = get_number("Enter second number: ")

    try:
        if choice == "1":
            result = add(a, b)
        elif choice == "2":
            result = subtract(a, b)
        elif choice == "3":
            result = multiply(a, b)
        elif choice == "4":
            result = divide(a, b)

        print(f"Result: {result}")

    except ValueError as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    main()

