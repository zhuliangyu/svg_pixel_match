from pathlib import Path


def main() -> None:
    _clear_output_files(Path("outputs"))
    print("Start svg pixel matching")

def _clear_output_files(outputs_dir: Path) -> None:
    outputs_dir.mkdir(exist_ok=True)

    for path in outputs_dir.iterdir():
        if path.is_file():
            path.unlink()
