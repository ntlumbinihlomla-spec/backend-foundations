import csv

def count_rows(filepath):
    with open(filepath, newline="", encoding="utf-8") as f:
        return sum(1 for _ in csv.reader(f))

def count_columns(filepath):
    with open(filepath, newline="", encoding="utf-8") as f:
        reader = csv.reader(f)
        return len(next(reader))

