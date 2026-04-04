from pathlib import Path

from svg_compare.cli import main


def test_main_prints_hello_world(capsys) -> None:
    main()

    captured = capsys.readouterr()

    assert captured.out == "hello world\n"


def test_main_deletes_all_files_in_outputs_before_running() -> None:
    outputs_dir = Path("outputs")
    outputs_dir.mkdir(exist_ok=True)
    first_file = outputs_dir / "reports.txt"
    second_file = outputs_dir / "stale.txt"
    first_file.write_text("old report", encoding="utf-8")
    second_file.write_text("stale data", encoding="utf-8")

    main()

    assert list(outputs_dir.iterdir()) == []
