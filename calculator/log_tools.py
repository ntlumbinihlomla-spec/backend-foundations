def count_errors(filepath):
    with open(filepath, "r", encoding="utf-8") as f:
        return sum(1 for line in f if "error" in line.lower())

