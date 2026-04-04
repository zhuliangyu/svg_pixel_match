from pathlib import Path

import pytest

from svg_compare.cli import _close_thread_renderer, _format_progress_line, _get_thread_renderer, main, parse_args, run_cli


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
    assert captured["debug_output_path"] == Path("outputs") / "debug" / "before" / "sample_same_1.png"
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

    class FakeRenderer:
        def render_svg_to_png(self, svg_text: str) -> bytes:
            return b"png"

    monkeypatch.setattr("svg_compare.cli.preprocess_svg", fake_preprocess_svg)
    monkeypatch.setattr("svg_compare.cli._get_thread_renderer", lambda: FakeRenderer())
    monkeypatch.setattr("svg_compare.cli.compare_png_bytes", lambda before_png, after_png: True)

    main(
        before_dir=Path("tests/fixtures/before"),
        after_dir=Path("tests/fixtures/after"),
        remove_ids=["mycurrenttime", "dot-before-a"],
    )

    assert len(preprocess_calls) == 2
    assert preprocess_calls[0][1] == ["mycurrenttime", "dot-before-a"]
    assert preprocess_calls[1][1] == ["mycurrenttime", "dot-before-a"]
    assert 'id="bg-before-a"' in preprocess_calls[0][0]
    assert 'id="mycurrenttime"' in preprocess_calls[0][0]
    assert 'id="bg-after-a"' in preprocess_calls[1][0]
    assert 'id="mycurrenttime"' in preprocess_calls[1][0]


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

    class FakeRenderer:
        def render_svg_to_png(self, svg_text: str) -> bytes:
            render_calls.append(svg_text)
            return f"png::{len(render_calls)}".encode()

    def fake_compare_png_bytes(before_png: bytes, after_png: bytes) -> bool:
        compare_calls.append((before_png, after_png))
        return True

    monkeypatch.setattr("svg_compare.cli._get_thread_renderer", lambda: FakeRenderer())
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
    printed_diffs: list[str] = []
    diff_detail_calls: list[tuple[bytes, bytes, Path]] = []

    monkeypatch.setattr(
        "svg_compare.cli.find_matched_svg_pairs",
        lambda before_dir, after_dir, report_path=None: [(before_path, after_path)],
    )
    class FakeRenderer:
        def render_svg_to_png(self, svg_text: str) -> bytes:
            return b"png"

    monkeypatch.setattr("svg_compare.cli.preprocess_svg", lambda svg_text, remove_ids: svg_text)
    monkeypatch.setattr("svg_compare.cli._get_thread_renderer", lambda: FakeRenderer())
    monkeypatch.setattr("svg_compare.cli.compare_png_bytes", lambda before_png, after_png: False)
    monkeypatch.setattr(
        "svg_compare.cli.write_diff_details",
        lambda before_png, after_png, output_dir: diff_detail_calls.append(
            (before_png, after_png, output_dir)
        ),
    )
    monkeypatch.setattr("svg_compare.cli._print_different_filename", lambda filename: printed_diffs.append(filename))

    main(
        before_dir=Path("tests/fixtures/before"),
        after_dir=Path("tests/fixtures/after"),
        remove_ids=["mycurrenttime"],
    )

    assert printed_diffs == ["sample_diff_1.svg"]
    assert diff_detail_calls == [
        (
            b"png",
            b"png",
            Path("outputs") / "diff_details" / "sample_diff_1",
        )
    ]
    assert (Path("outputs") / "different.txt").read_text(encoding="utf-8") == "sample_diff_1.svg\n"


def test_main_processes_pairs_with_configured_concurrency(monkeypatch) -> None:
    pairs = [
        (Path("tests/fixtures/before/sample_same_1.svg"), Path("tests/fixtures/after/sample_same_1.svg")),
        (Path("tests/fixtures/before/sample_diff_1.svg"), Path("tests/fixtures/after/sample_diff_1.svg")),
    ]
    submitted_worker_count = 0
    requested_workers: int | None = None

    class FakeFuture:
        def result(self) -> None:
            return None

    class FakeExecutor:
        def __init__(self, max_workers: int) -> None:
            nonlocal requested_workers
            requested_workers = max_workers

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb) -> None:
            return None

        def submit(self, fn, pair_queue, result_queue, remove_ids: list[str]):
            nonlocal submitted_worker_count
            submitted_worker_count += 1
            fn(pair_queue, result_queue, remove_ids)
            return FakeFuture()

    monkeypatch.setattr(
        "svg_compare.cli.find_matched_svg_pairs",
        lambda before_dir, after_dir, report_path=None: pairs,
    )
    monkeypatch.setattr("svg_compare.cli.ThreadPoolExecutor", FakeExecutor)
    class FakeRenderer:
        def render_svg_to_png(self, svg_text: str) -> bytes:
            return b"png"

    compare_results = iter([True, False])

    monkeypatch.setattr("svg_compare.cli._get_thread_renderer", lambda: FakeRenderer())
    monkeypatch.setattr("svg_compare.cli._close_thread_renderer", lambda: None)
    monkeypatch.setattr("svg_compare.cli.preprocess_svg", lambda svg_text, remove_ids: svg_text)
    monkeypatch.setattr(
        "svg_compare.cli.compare_png_bytes",
        lambda before_png, after_png: next(compare_results),
    )
    monkeypatch.setattr("svg_compare.cli.write_diff_details", lambda before_png, after_png, output_dir: None)

    main(
        before_dir=Path("tests/fixtures/before"),
        after_dir=Path("tests/fixtures/after"),
        remove_ids=["mycurrenttime"],
        concurrency=3,
    )

    assert requested_workers == 2
    assert submitted_worker_count == 2
    assert (Path("outputs") / "different.txt").read_text(encoding="utf-8") == "sample_diff_1.svg\n"


def test_main_updates_progress_for_completed_pairs(monkeypatch) -> None:
    pairs = [
        (Path("tests/fixtures/before/sample_same_1.svg"), Path("tests/fixtures/after/sample_same_1.svg")),
        (Path("tests/fixtures/before/sample_diff_1.svg"), Path("tests/fixtures/after/sample_diff_1.svg")),
    ]
    progress_updates: list[tuple[int, int]] = []

    class FakeFuture:
        def __init__(self, result: bool) -> None:
            self._result = result

        def result(self) -> bool:
            return self._result

    class FakeExecutor:
        def __init__(self, max_workers: int) -> None:
            self._futures: list[FakeFuture] = []

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb) -> None:
            return None

        def submit(self, fn, pair_queue, result_queue, remove_ids: list[str]):
            fn(pair_queue, result_queue, remove_ids)
            future = FakeFuture(False)
            self._futures.append(future)
            return future

    monkeypatch.setattr(
        "svg_compare.cli.find_matched_svg_pairs",
        lambda before_dir, after_dir, report_path=None: pairs,
    )
    monkeypatch.setattr("svg_compare.cli.ThreadPoolExecutor", FakeExecutor)
    class FakeRenderer:
        def render_svg_to_png(self, svg_text: str) -> bytes:
            return b"png"

    monkeypatch.setattr("svg_compare.cli._get_thread_renderer", lambda: FakeRenderer())
    monkeypatch.setattr("svg_compare.cli._close_thread_renderer", lambda: None)
    monkeypatch.setattr("svg_compare.cli.preprocess_svg", lambda svg_text, remove_ids: svg_text)
    monkeypatch.setattr("svg_compare.cli.compare_png_bytes", lambda before_png, after_png: True)
    monkeypatch.setattr("svg_compare.cli.write_diff_details", lambda before_png, after_png, output_dir: None)
    monkeypatch.setattr(
        "svg_compare.cli._print_progress",
        lambda completed, total, started_at, different_count: progress_updates.append(
            (completed, total, different_count)
        ),
    )

    main(
        before_dir=Path("tests/fixtures/before"),
        after_dir=Path("tests/fixtures/after"),
        remove_ids=["mycurrenttime"],
    )

    assert progress_updates == [(1, 2, 0), (2, 2, 0)]


def test_get_thread_renderer_reuses_renderer_in_same_thread(monkeypatch) -> None:
    created_renderers: list[object] = []

    class FakeRenderer:
        def start(self) -> None:
            return None

    import threading

    monkeypatch.setattr("svg_compare.cli._THREAD_RENDERER", threading.local())
    monkeypatch.setattr(
        "svg_compare.cli.PlaywrightSvgRenderer",
        lambda: created_renderers.append(FakeRenderer()) or created_renderers[-1],
    )

    first = _get_thread_renderer()
    second = _get_thread_renderer()

    assert first is second
    assert len(created_renderers) == 1


def test_close_thread_renderer_closes_current_thread_renderer(monkeypatch) -> None:
    closed: list[str] = []

    class FakeRenderer:
        def close(self) -> None:
            closed.append("closed")

    import threading

    thread_local = threading.local()
    thread_local.renderer = FakeRenderer()
    monkeypatch.setattr("svg_compare.cli._THREAD_RENDERER", thread_local)

    _close_thread_renderer()

    assert closed == ["closed"]
    assert getattr(thread_local, "renderer") is None


def test_parse_args_accepts_before_after_paths_and_multiple_remove_ids() -> None:
    args = parse_args(
        [
            "--before-dir",
            "tests/fixtures/before",
            "--after-dir",
            "tests/fixtures/after",
            "--concurrency",
            "8",
            "--remove-id",
            "mycurrenttime",
            "--remove-id",
            "dot-before-a",
        ]
    )

    assert args.before_dir == Path("tests/fixtures/before")
    assert args.after_dir == Path("tests/fixtures/after")
    assert args.concurrency == 8
    assert args.remove_ids == ["mycurrenttime", "dot-before-a"]


def test_run_cli_passes_parsed_values_to_main(monkeypatch) -> None:
    captured: dict[str, object] = {}

    def fake_main(
        before_dir: Path | None = None,
        after_dir: Path | None = None,
        remove_ids: list[str] | None = None,
        concurrency: int = 4,
        debug: bool = False,
        debug_svg_path: Path | None = None,
        debug_output_group: str = "before",
    ) -> None:
        captured["before_dir"] = before_dir
        captured["after_dir"] = after_dir
        captured["remove_ids"] = remove_ids
        captured["concurrency"] = concurrency
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
            "--concurrency",
            "6",
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
    assert captured["concurrency"] == 6
    assert captured["debug"] is True
    assert captured["debug_svg_path"] == Path("tests/fixtures/before/sample_same_1.svg")
    assert captured["debug_output_group"] == "after"


def test_format_progress_line_contains_percentage_and_eta() -> None:
    line = _format_progress_line(
        completed=25,
        total=100,
        elapsed_seconds=50.0,
        different_count=7,
    )

    assert "[" in line
    assert "]" in line
    assert "25%" in line
    assert "25/100" in line
    assert "ETA" in line
    assert "diff=7" in line
    assert "elapsed" in line


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


@pytest.mark.integration
def test_main_end_to_end_without_removing_mycurrenttime_writes_expected_different_txt() -> None:
    main(
        before_dir=Path("tests/fixtures/before"),
        after_dir=Path("tests/fixtures/after"),
        remove_ids=[],
    )

    assert (Path("outputs") / "different.txt").read_text(encoding="utf-8") == (
        "sample_diff_1.svg\n"
        "sample_diff_2.svg\n"
        "sample_same_1.svg\n"
        "sample_same_2.svg\n"
    )
    assert (Path("outputs") / "unmatched_svgs.txt").read_text(encoding="utf-8") == (
        "after_only_unmatched.svg\n"
    )
