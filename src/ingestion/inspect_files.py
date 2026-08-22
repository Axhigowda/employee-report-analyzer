from pathlib import Path


def inspect_files(data_directory):
    data_path = Path(data_directory)

    if not data_path.exists():
        print(f"Directory does not exist: {data_path}")
        return

    for file_path in sorted(data_path.rglob("*")):

        if not file_path.is_file():
            continue

        relative_path = file_path.relative_to(data_path)

        employee = relative_path.parts[0]

        print(f"Employee   : {employee}")
        print(f"File       : {file_path.name}")
        print(f"Extension  : {file_path.suffix}")
        print(f"Full Path  : {file_path}")
        print("-" * 60)


if __name__ == "__main__":
    inspect_files("data/raw/employee_reports")