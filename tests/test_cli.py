from pathlib import Path

import pytest

from svg_compare.cli import main, parse_args, run_cli


def test_main_prints_start_message(capsys) -> None:
    main()

    captured = capsys.readouterr()

    assert captured.out == "Start svg pixel matching\n"


def test_main_deletes_all_files_in_outputs_before_running() -> None:
    outputs_dir = Path("outputs")
    outputs_dir.mkdir(exist_ok=True)
    first_file = outputs_dir / "reports.txt"
    second_file = outputs_dir / "stale.txt"
    first_file.write_text("old report", encoding="utf-8")
    second_file.write_text("stale data", encoding="utf-8")

    main()

    assert list(outputs_dir.iterdir()) == []


def test_main_opens_outputs_directory_when_finished(monkeypatch) -> None:
    opened_path: Path | None = None

    def fake_open_outputs_directory(outputs_dir: Path) -> None:
        nonlocal opened_path
        opened_path = outputs_dir

    monkeypatch.setattr("svg_compare.cli._open_outputs_directory", fake_open_outputs_directory)

    main()

    assert opened_path == Path("outputs")


def test_main_passes_debug_render_output_to_before_directory(monkeypatch) -> None:
    debug_svg_path = Path("tests") / "fixtures" / "before" / "sample_same_1.svg"
    captured: dict[str, object] = {}

    def fake_render_svg_to_png(
        svg_text: str,
        debug: bool = False,
        debug_output_path: Path | None = None,
    ) -> bytes:
        captured["svg_text"] = svg_text
        captured["debug"] = debug
        captured["debug_output_path"] = debug_output_path
        return b"png"

    monkeypatch.setattr("svg_compare.cli.render_svg_to_png", fake_render_svg_to_png)

    main(
        debug=True,
        debug_svg_path=debug_svg_path,
        debug_output_group="before",
    )

    assert captured["debug"] is True
    assert captured["debug_output_path"] == Path("outputs") / "before" / "sample_same_1.png"
    assert "sample_same_1" not in str(captured["svg_text"])


def test_main_does_not_call_render_when_debug_is_false(monkeypatch) -> None:
    called = False

    def fake_render_svg_to_png(
        svg_text: str,
        debug: bool = False,
        debug_output_path: Path | None = None,
    ) -> bytes:
        nonlocal called
        called = True
        return b"png"

    monkeypatch.setattr("svg_compare.cli.render_svg_to_png", fake_render_svg_to_png)

    main(debug=False)

    assert called is False


def test_main_pairs_svg_files_and_preprocesses_before_and_after(monkeypatch) -> None:
    before_path = Path("tests/fixtures/before/sample_same_1.svg")
    after_path = Path("tests/fixtures/after/sample_same_1.svg")
    preprocess_calls: list[tuple[str, list[str]]] = []

    monkeypatch.setattr(
        "svg_compare.cli.find_matched_svg_pairs",
        lambda before_dir, after_dir, report_path=None: [(before_path, after_path)],
    )

    def fake_preprocess_svg(svg_text: str, remove_ids: list[str]) -> str:
        preprocess_calls.append((svg_text, remove_ids))
        return svg_text

    monkeypatch.setattr("svg_compare.cli.preprocess_svg", fake_preprocess_svg)
    monkeypatch.setattr("svg_compare.cli.render_svg_to_png", lambda svg_text, debug=False, debug_output_path=None: b"png")
    monkeypatch.setattr("svg_compare.cli.compare_png_bytes", lambda before_png, after_png: True)

    main(
        before_dir=Path("tests/fixtures/before"),
        after_dir=Path("tests/fixtures/after"),
        remove_ids=["mycurrenttime", "dot-before-a"],
    )

    assert len(preprocess_calls) == 2
    assert preprocess_calls[0][1] == ["mycurrenttime", "dot-before-a"]
    assert preprocess_calls[1][1] == ["mycurrenttime", "dot-before-a"]
    assert "2026-04-03T23:45:10.101" in preprocess_calls[0][0]
    assert "2026-04-03T23:45:10.202" in preprocess_calls[1][0]


def test_main_renders_preprocessed_svgs_and_compares_pngs(monkeypatch) -> None:
    before_path = Path("tests/fixtures/before/sample_same_1.svg")
    after_path = Path("tests/fixtures/after/sample_same_1.svg")
    render_calls: list[str] = []
    compare_calls: list[tuple[bytes, bytes]] = []

    monkeypatch.setattr(
        "svg_compare.cli.find_matched_svg_pairs",
        lambda before_dir, after_dir, report_path=None: [(before_path, after_path)],
    )
    monkeypatch.setattr(
        "svg_compare.cli.preprocess_svg",
        lambda svg_text, remove_ids: f"processed::{svg_text}",
    )

    def fake_render_svg_to_png(
        svg_text: str,
        debug: bool = False,
        debug_output_path: Path | None = None,
    ) -> bytes:
        render_calls.append(svg_text)
        return f"png::{len(render_calls)}".encode()

    def fake_compare_png_bytes(before_png: bytes, after_png: bytes) -> bool:
        compare_calls.append((before_png, after_png))
        return True

    monkeypatch.setattr("svg_compare.cli.render_svg_to_png", fake_render_svg_to_png)
    monkeypatch.setattr("svg_compare.cli.compare_png_bytes", fake_compare_png_bytes)

    main(
        before_dir=Path("tests/fixtures/before"),
        after_dir=Path("tests/fixtures/after"),
        remove_ids=["mycurrenttime"],
    )

    assert len(render_calls) == 2
    assert render_calls[0].startswith("processed::")
    assert render_calls[1].startswith("processed::")
    assert compare_calls == [(b"png::1", b"png::2")]


def test_main_writes_different_filename_when_compare_returns_false(monkeypatch) -> None:
    before_path = Path("tests/fixtures/before/sample_diff_1.svg")
    after_path = Path("tests/fixtures/after/sample_diff_1.svg")

    monkeypatch.setattr(
        "svg_compare.cli.find_matched_svg_pairs",
        lambda before_dir, after_dir, report_path=None: [(before_path, after_path)],
    )
    monkeypatch.setattr("svg_compare.cli.preprocess_svg", lambda svg_text, remove_ids: svg_text)
    monkeypatch.setattr("svg_compare.cli.render_svg_to_png", lambda svg_text, debug=False, debug_output_path=None: b"png")
    monkeypatch.setattr("svg_compare.cli.compare_png_bytes", lambda before_png, after_png: False)

    main(
        before_dir=Path("tests/fixtures/before"),
        after_dir=Path("tests/fixtures/after"),
        remove_ids=["mycurrenttime"],
    )

    assert (Path("outputs") / "different.txt").read_text(encoding="utf-8") == "sample_diff_1.svg\n"


def test_parse_args_accepts_before_after_paths_and_multiple_remove_ids() -> None:
    args = parse_args(
        [
            "--before-dir",
            "tests/fixtures/before",
            "--after-dir",
            "tests/fixtures/after",
            "--remove-id",
            "mycurrenttime",
            "--remove-id",
            "dot-before-a",
        ]
    )

    assert args.before_dir == Path("tests/fixtures/before")
    assert args.after_dir == Path("tests/fixtures/after")
    assert args.remove_ids == ["mycurrenttime", "dot-before-a"]


def test_run_cli_passes_parsed_values_to_main(monkeypatch) -> None:
    captured: dict[str, object] = {}

    def fake_main(
        before_dir: Path | None = None,
        after_dir: Path | None = None,
        remove_ids: list[str] | None = None,
        debug: bool = False,
        debug_svg_path: Path | None = None,
        debug_output_group: str = "before",
    ) -> None:
        captured["before_dir"] = before_dir
        captured["after_dir"] = after_dir
        captured["remove_ids"] = remove_ids
        captured["debug"] = debug
        captured["debug_svg_path"] = debug_svg_path
        captured["debug_output_group"] = debug_output_group

    monkeypatch.setattr("svg_compare.cli.main", fake_main)

    run_cli(
        [
            "--before-dir",
            "tests/fixtures/before",
            "--after-dir",
            "tests/fixtures/after",
            "--remove-id",
            "mycurrenttime",
            "--remove-id",
            "dot-before-a",
            "--debug",
            "--debug-svg-path",
            "tests/fixtures/before/sample_same_1.svg",
            "--debug-output-group",
            "after",
        ]
    )

    assert captured["before_dir"] == Path("tests/fixtures/before")
    assert captured["after_dir"] == Path("tests/fixtures/after")
    assert captured["remove_ids"] == ["mycurrenttime", "dot-before-a"]
    assert captured["debug"] is True
    assert captured["debug_svg_path"] == Path("tests/fixtures/before/sample_same_1.svg")
    assert captured["debug_output_group"] == "after"


@pytest.mark.integration
def test_main_end_to_end_writes_expected_different_txt() -> None:
    main(
        before_dir=Path("tests/fixtures/before"),
        after_dir=Path("tests/fixtures/after"),
        remove_ids=["mycurrenttime"],
    )

    assert (Path("outputs") / "different.txt").read_text(encoding="utf-8") == (
        "sample_diff_1.svg\n"
        "sample_diff_2.svg\n"
    )
    assert (Path("outputs") / "unmatched_svgs.txt").read_text(encoding="utf-8") == (
        "after_only_unmatched.svg\n"
    )
