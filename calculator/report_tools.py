from pathlib import Path

from calculator.csv_tools import count_columns, count_rows
from calculator.file_tools import count_lines
from calculator.json_tools import count_keys
from calculator.log_tools import count_errors


SUPPORTED_LINE_SUFFIXES = {
    ".csv",
    ".json",
    ".log",
    ".md",
    ".py",
    ".txt",
    ".yml",
    ".yaml",
}


def _iter_files(folder):
    folder_path = Path(folder)
    if not folder_path.exists() or not folder_path.is_dir():
        raise NotADirectoryError("Folder does not exist")

    return sorted(path for path in folder_path.rglob("*") if path.is_file())


def build_workspace_audit(folder):
    files = _iter_files(folder)
    report = {
        "folder": str(Path(folder)),
        "total_files": len(files),
        "total_lines": 0,
        "csv_files": [],
        "json_files": [],
        "log_files": [],
    }

    for file_path in files:
        if file_path.suffix.lower() in SUPPORTED_LINE_SUFFIXES:
            report["total_lines"] += count_lines(file_path)

        suffix = file_path.suffix.lower()
        if suffix == ".csv":
            report["csv_files"].append(
                {
                    "name": file_path.name,
                    "rows": count_rows(file_path),
                    "columns": count_columns(file_path),
                }
            )
        elif suffix == ".json":
            report["json_files"].append(
                {
                    "name": file_path.name,
                    "keys": count_keys(file_path),
                }
            )
        elif suffix == ".log":
            report["log_files"].append(
                {
                    "name": file_path.name,
                    "errors": count_errors(file_path),
                }
            )

    return report


def format_workspace_audit(report):
    lines = [
        "=============================================",
        "        WORKSPACE AUDIT REPORT",
        "=============================================",
        f"Folder      : {report['folder']}",
        f"Total Files : {report['total_files']}",
        f"Total Lines : {report['total_lines']}",
        "---------------------------------------------",
        "CSV Files",
    ]

    if report["csv_files"]:
        for item in report["csv_files"]:
            lines.append(
                f"- {item['name']}: rows={item['rows']}, columns={item['columns']}"
            )
    else:
        lines.append("- None")

    lines.append("---------------------------------------------")
    lines.append("JSON Files")

    if report["json_files"]:
        for item in report["json_files"]:
            lines.append(f"- {item['name']}: top-level keys={item['keys']}")
    else:
        lines.append("- None")

    lines.append("---------------------------------------------")
    lines.append("LOG Files")

    if report["log_files"]:
        for item in report["log_files"]:
            lines.append(f"- {item['name']}: errors={item['errors']}")
    else:
        lines.append("- None")

    lines.append("=============================================")
    return "\n".join(lines)
