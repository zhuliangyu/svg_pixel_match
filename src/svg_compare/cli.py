import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
import os
from pathlib import Path
import shutil
import sys
import time

from svg_compare.compare import compare_png_bytes
from svg_compare.pairing import find_matched_svg_pairs
from svg_compare.preprocess import preprocess_svg
from svg_compare.render import render_svg_to_png


def main(
    before_dir: Path | None = None,
    after_dir: Path | None = None,
    remove_ids: list[str] | None = None,
    concurrency: int = 4,
    debug: bool = False,
    debug_svg_path: Path | None = None,
    debug_output_group: str = "before",
) -> None:
    outputs_dir = Path("outputs")
    _clear_output_files(outputs_dir)
    different_filenames: list[str] = []

    print("Start svg pixel matching")

    if before_dir is not None and after_dir is not None:
        matched_pairs = find_matched_svg_pairs(
            before_dir,
            after_dir,
            report_path=outputs_dir / "unmatched_svgs.txt",
        )
        started_at = time.perf_counter()

        with ThreadPoolExecutor(max_workers=max(1, concurrency)) as executor:
            futures = {
                executor.submit(
                    _process_pair,
                    matched_before_path,
                    matched_after_path,
                    remove_ids or [],
                ): matched_before_path.name
                for matched_before_path, matched_after_path in matched_pairs
            }

            completed = 0
            total = len(futures)
            for future in as_completed(futures):
                filename = futures[future]
                if future.result():
                    different_filenames.append(filename)
                    _print_different_filename(filename)
                completed += 1
                _print_progress(completed, total, started_at, len(different_filenames))

        (outputs_dir / "different.txt").write_text(
            "".join(f"{filename}\n" for filename in sorted(different_filenames)),
            encoding="utf-8",
        )

    if debug and debug_svg_path is not None:
        svg_text = debug_svg_path.read_text(encoding="utf-8")
        debug_output_path = outputs_dir / debug_output_group / f"{debug_svg_path.stem}.png"
        render_svg_to_png(
            svg_text,
            debug=True,
            debug_output_path=debug_output_path,
        )

    _open_outputs_directory(outputs_dir)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--before-dir", type=Path, required=True)
    parser.add_argument("--after-dir", type=Path, required=True)
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


def _open_outputs_directory(outputs_dir: Path) -> None:
    try:
        os.startfile(outputs_dir)
    except OSError:
        pass


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


def _process_pair(
    matched_before_path: Path,
    matched_after_path: Path,
    remove_ids: list[str],
) -> bool:
    matched_before_svg = matched_before_path.read_text(encoding="utf-8")
    matched_after_svg = matched_after_path.read_text(encoding="utf-8")
    processed_before_svg = preprocess_svg(matched_before_svg, remove_ids)
    processed_after_svg = preprocess_svg(matched_after_svg, remove_ids)
    before_png = render_svg_to_png(processed_before_svg)
    after_png = render_svg_to_png(processed_after_svg)
    return not compare_png_bytes(before_png, after_png)


if __name__ == "__main__":
    run_cli()
