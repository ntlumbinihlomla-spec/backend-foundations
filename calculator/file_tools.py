from pathlib import Path


def count_lines(file_path):
    path = Path(file_path)
    if not path.exists() or not path.is_file():
        raise FileNotFoundError("File does not exist")

    with path.open("r", encoding="utf-8") as f:
        return sum(1 for _ in f)


def count_words(file_path):
    path = Path(file_path)
    if not path.exists() or not path.is_file():
        raise FileNotFoundError("File does not exist")

    with path.open("r", encoding="utf-8") as f:
        return len(f.read().split())


def count_lines_in_dir(folder):
    folder_path = Path(folder)
    if not folder_path.exists() or not folder_path.is_dir():
        raise NotADirectoryError("Folder does not exist")

    total = 0
    for file in folder_path.iterdir():
        if file.is_file():
            total += count_lines(file)

    return total
