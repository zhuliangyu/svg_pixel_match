import argparse
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from queue import Empty, Queue
import shutil
import sys
import threading
import time

from svg_compare.compare import compare_png_bytes, write_diff_details
from svg_compare.pairing import find_matched_svg_pairs
from svg_compare.preprocess import preprocess_svg
from svg_compare.render import PlaywrightSvgRenderer, render_svg_to_png, write_render_debug_details


_THREAD_RENDERER = threading.local()
_ERROR_LOG_LOCK = threading.Lock()
_ERROR_LOG_PATH: Path | None = None
_ERROR_SVGS_DIR: Path | None = None


def main(
    before_dir: Path | None = None,
    after_dir: Path | None = None,
    output_dir: Path | None = None,
    remove_ids: list[str] | None = None,
    concurrency: int = 4,
    debug: bool = False,
    debug_svg_path: Path | None = None,
    debug_output_group: str = "before",
) -> None:
    global _ERROR_LOG_PATH, _ERROR_SVGS_DIR
    outputs_dir = output_dir or Path("outputs")
    _log_info(f"Clearing output directory: {outputs_dir}")
    _clear_output_files(outputs_dir)
    previous_error_log_path = _ERROR_LOG_PATH
    previous_error_svgs_dir = _ERROR_SVGS_DIR
    _ERROR_LOG_PATH = outputs_dir / "errors.txt"
    _ERROR_SVGS_DIR = outputs_dir / "errors_svgs"
    different_filenames: list[str] = []
    try:
        _log_info("Output directory is ready")
        _log_info("Start svg pixel matching")

        if before_dir is not None and after_dir is not None:
            _log_info(f"Scanning before directory: {before_dir}")
            _log_info(f"Scanning after directory: {after_dir}")
            matched_pairs = find_matched_svg_pairs(
                before_dir,
                after_dir,
                report_path=outputs_dir / "unmatched_svgs.txt",
            )
            started_at = time.perf_counter()
            total = len(matched_pairs)
            _log_info(f"Found {total} matched SVG pairs")
            if total > 0:
                worker_count = min(max(1, concurrency), total)
                _log_info(f"Starting {worker_count} worker threads")
                pair_queue: Queue[tuple[Path, Path] | None] = Queue()
                result_queue: Queue[tuple[Path, Path, bool, bytes, bytes, str, str]] = Queue()
                stop_event = threading.Event()

                for matched_pair in matched_pairs:
                    pair_queue.put(matched_pair)
                for _ in range(worker_count):
                    pair_queue.put(None)

                executor = ThreadPoolExecutor(max_workers=worker_count)
                try:
                    futures = [
                        executor.submit(
                            _worker_loop,
                            pair_queue,
                            result_queue,
                            remove_ids or [],
                            stop_event,
                        )
                        for _ in range(worker_count)
                    ]

                    completed = 0
                    while completed < total:
                        result = _wait_for_next_result(result_queue)
                        if result is None:
                            _raise_completed_worker_exception(futures)
                            continue

                        (
                            matched_before_path,
                            matched_after_path,
                            is_different,
                            before_png,
                            after_png,
                            processed_before_svg,
                            processed_after_svg,
                        ) = result
                        filename = matched_before_path.name
                        if is_different:
                            different_filenames.append(filename)
                            diff_detail_dir = outputs_dir / "diff_details" / Path(filename).stem
                            diff_detail_dir.mkdir(parents=True, exist_ok=True)
                            write_diff_details(
                                before_png,
                                after_png,
                                diff_detail_dir,
                            )
                            write_render_debug_details(
                                processed_before_svg,
                                processed_after_svg,
                                diff_detail_dir,
                            )
                            shutil.copyfile(matched_before_path, diff_detail_dir / "before.svg")
                            shutil.copyfile(matched_after_path, diff_detail_dir / "after.svg")
                            _print_different_filename(filename)
                        completed += 1
                        _print_progress(completed, total, started_at, len(different_filenames))

                    for future in futures:
                        future.result()
                except KeyboardInterrupt:
                    _log_info("KeyboardInterrupt received, stopping workers")
                    _request_worker_stop(pair_queue, worker_count, stop_event)
                    executor.shutdown(wait=False, cancel_futures=True)
                    raise
                finally:
                    if not stop_event.is_set():
                        executor.shutdown(wait=True, cancel_futures=False)

            (outputs_dir / "different.txt").write_text(
                "".join(f"{filename}\n" for filename in sorted(different_filenames)),
                encoding="utf-8",
            )
            _log_info(f"Wrote different file list: {outputs_dir / 'different.txt'}")

        if debug and debug_svg_path is not None:
            _log_info(f"Rendering debug SVG: {debug_svg_path}")
            svg_text = debug_svg_path.read_text(encoding="utf-8")
            debug_output_path = outputs_dir / "debug" / debug_output_group / f"{debug_svg_path.stem}.png"
            render_svg_to_png(
                svg_text,
                debug=True,
                debug_output_path=debug_output_path,
            )
            _log_info(f"Wrote debug PNG: {debug_output_path}")
    finally:
        _ERROR_LOG_PATH = previous_error_log_path
        _ERROR_SVGS_DIR = previous_error_svgs_dir

def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--before-dir", type=Path, required=True)
    parser.add_argument("--after-dir", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, default=Path("outputs"))
    parser.add_argument("--concurrency", type=int, default=4)
    parser.add_argument("--remove-id", dest="remove_ids", action="append", default=[])
    parser.add_argument("--debug", action="store_true")
    parser.add_argument("--debug-svg-path", type=Path)
    parser.add_argument(
        "--debug-output-group",
        choices=["before", "after"],
        default="before",
    )
    return parser.parse_args(argv)


def run_cli(argv: list[str] | None = None) -> None:
    args = parse_args(argv)
    main(
        before_dir=args.before_dir,
        after_dir=args.after_dir,
        output_dir=args.output_dir,
        remove_ids=args.remove_ids,
        concurrency=args.concurrency,
        debug=args.debug,
        debug_svg_path=args.debug_svg_path,
        debug_output_group=args.debug_output_group,
    )


def _clear_output_files(outputs_dir: Path) -> None:
    outputs_dir.mkdir(exist_ok=True)

    for path in outputs_dir.iterdir():
        if path.is_file():
            path.unlink()
        elif path.is_dir():
            shutil.rmtree(path)


def _print_different_filename(filename: str) -> None:
    print(f"DIFF {filename}", file=sys.stdout, flush=True)


def _print_progress(
    completed: int,
    total: int,
    started_at: float,
    different_count: int,
) -> None:
    elapsed_seconds = time.perf_counter() - started_at
    line = _format_progress_line(
        completed=completed,
        total=total,
        elapsed_seconds=elapsed_seconds,
        different_count=different_count,
    )
    end = "\n" if completed == total else "\r"
    print(line, end=end, file=sys.stdout, flush=True)


def _format_progress_line(
    completed: int,
    total: int,
    elapsed_seconds: float,
    different_count: int,
) -> str:
    if total <= 0:
        return "[....................] 0% 0/0 diff=0 elapsed 00:00:00 ETA 00:00:00"

    percent = int((completed / total) * 100)
    bar_width = 20
    filled = int((completed / total) * bar_width)
    bar = "#" * filled + "." * (bar_width - filled)
    remaining_seconds = 0.0
    if completed > 0:
        average_seconds = elapsed_seconds / completed
        remaining_seconds = average_seconds * (total - completed)

    return (
        f"[{bar}] {percent}% {completed}/{total} "
        f"diff={different_count} "
        f"elapsed {_format_seconds(elapsed_seconds)} "
        f"ETA {_format_seconds(remaining_seconds)}"
    )


def _format_seconds(seconds: float) -> str:
    total_seconds = max(0, int(round(seconds)))
    hours, remainder = divmod(total_seconds, 3600)
    minutes, secs = divmod(remainder, 60)
    return f"{hours:02d}:{minutes:02d}:{secs:02d}"


def _worker_loop(
    pair_queue: Queue[tuple[Path, Path] | None],
    result_queue: Queue[tuple[Path, Path, bool, bytes, bytes, str, str]],
    remove_ids: list[str],
    stop_event: threading.Event,
) -> None:
    current_filename: str | None = None
    current_before_path: Path | None = None
    current_after_path: Path | None = None
    try:
        renderer = _get_thread_renderer()
        while True:
            if stop_event.is_set():
                _log_info(f"[{threading.current_thread().name}] Stop requested, worker exits")
                return
            matched_pair = pair_queue.get()
            if matched_pair is None:
                _log_info(f"[{threading.current_thread().name}] No more work, worker exits")
                return

            matched_before_path, matched_after_path = matched_pair
            current_before_path = matched_before_path
            current_after_path = matched_after_path
            current_filename = matched_before_path.name
            _log_info(f"[{threading.current_thread().name}] Processing pair: {matched_before_path.name}")
            is_different, before_png, after_png, processed_before_svg, processed_after_svg = _process_pair(
                matched_before_path,
                matched_after_path,
                remove_ids,
                renderer,
            )
            result_queue.put(
                (
                    matched_before_path,
                    matched_after_path,
                    is_different,
                    before_png,
                    after_png,
                    processed_before_svg,
                    processed_after_svg,
                )
            )
            _log_info(f"[{threading.current_thread().name}] Finished pair: {matched_before_path.name}")
            current_before_path = None
            current_after_path = None
            current_filename = None
    except Exception as exc:
        if current_filename is None:
            _log_error(f"[{threading.current_thread().name}] Worker failed: {exc!r}")
        else:
            _log_error(
                f"[{threading.current_thread().name}] Worker failed for {current_filename}: {exc!r}"
            )
            if current_before_path is not None and current_after_path is not None:
                _copy_error_svgs(current_before_path, current_after_path)
        raise
    finally:
        _close_thread_renderer()


def _process_pair(
    matched_before_path: Path,
    matched_after_path: Path,
    remove_ids: list[str],
    renderer: PlaywrightSvgRenderer | None = None,
) -> tuple[bool, bytes, bytes, str, str]:
    if renderer is None:
        renderer = _get_thread_renderer()
    matched_before_svg = matched_before_path.read_text(encoding="utf-8")
    matched_after_svg = matched_after_path.read_text(encoding="utf-8")
    processed_before_svg = preprocess_svg(matched_before_svg, remove_ids)
    processed_after_svg = preprocess_svg(matched_after_svg, remove_ids)
    before_png = renderer.render_svg_to_png(processed_before_svg)
    after_png = renderer.render_svg_to_png(processed_after_svg)
    return (
        not compare_png_bytes(before_png, after_png),
        before_png,
        after_png,
        processed_before_svg,
        processed_after_svg,
    )


def _get_thread_renderer() -> PlaywrightSvgRenderer:
    renderer = getattr(_THREAD_RENDERER, "renderer", None)
    if renderer is None:
        _log_info(f"[{threading.current_thread().name}] Starting Playwright Chromium renderer")
        renderer = PlaywrightSvgRenderer()
        renderer.start()
        _THREAD_RENDERER.renderer = renderer
        _log_info(f"[{threading.current_thread().name}] Playwright Chromium renderer is ready")
    return renderer


def _close_thread_renderer() -> None:
    renderer = getattr(_THREAD_RENDERER, "renderer", None)
    if renderer is None:
        return

    try:
        _log_info(f"[{threading.current_thread().name}] Closing Playwright Chromium renderer")
        renderer.close()
    finally:
        _THREAD_RENDERER.renderer = None


def _wait_for_next_result(
    result_queue: Queue[tuple[Path, Path, bool, bytes, bytes, str, str]],
    timeout_seconds: float = 0.2,
) -> tuple[Path, Path, bool, bytes, bytes, str, str] | None:
    try:
        return result_queue.get(timeout=timeout_seconds)
    except Empty:
        return None


def _request_worker_stop(
    pair_queue: Queue[tuple[Path, Path] | None],
    worker_count: int,
    stop_event: threading.Event,
) -> None:
    stop_event.set()
    for _ in range(worker_count):
        pair_queue.put(None)


def _raise_completed_worker_exception(futures: list[object]) -> None:
    for future in futures:
        done = getattr(future, "done", None)
        if callable(done) and not future.done():
            continue

        exception = getattr(future, "exception", None)
        if callable(exception):
            error = future.exception()
            if error is not None:
                _log_error(f"Worker future failed: {error!r}")
                raise error


def _log_info(message: str) -> None:
    print(f"[INFO] {message}", file=sys.stdout, flush=True)


def _log_error(message: str) -> None:
    print(f"[ERROR] {message}", file=sys.stderr, flush=True)
    if _ERROR_LOG_PATH is None:
        return

    with _ERROR_LOG_LOCK:
        _ERROR_LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
        with _ERROR_LOG_PATH.open("a", encoding="utf-8") as error_file:
            error_file.write(f"{message}\n")


def _copy_error_svgs(before_path: Path, after_path: Path) -> None:
    if _ERROR_SVGS_DIR is None:
        return

    target_dir = _ERROR_SVGS_DIR / before_path.stem
    target_dir.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(before_path, target_dir / "before.svg")
    shutil.copyfile(after_path, target_dir / "after.svg")


if __name__ == "__main__":
    run_cli()
