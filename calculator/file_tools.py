from pathlib import Path

def count_lines(file_path):
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError("File does not exist")

    with open(path, "r", encoding="utf-8") as f:
        return sum(1 for _ in f)

def count_words(file_path):
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError("File does not exist")

    with open(path, "r", encoding="utf-8") as f:
        text = f.read()
        return len(text.split())
    
def count_lines(filepath):
    with open(filepath, "r", encoding="utf-8") as f:
        return len(f.readlines())
    
def count_words(filepath):
    with open(filepath, "r", encoding="utf-8") as f:
        return len(f.read().split())


