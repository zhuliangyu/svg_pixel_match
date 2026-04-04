import argparse
from pathlib import Path
import shutil

from svg_compare.compare import compare_png_bytes
from svg_compare.pairing import find_matched_svg_pairs
from svg_compare.preprocess import preprocess_svg
from svg_compare.render import render_svg_to_png


def main(
    before_dir: Path | None = None,
    after_dir: Path | None = None,
    remove_ids: list[str] | None = None,
    debug: bool = False,
    debug_svg_path: Path | None = None,
    debug_output_group: str = "before",
) -> None:
    outputs_dir = Path("outputs")
    _clear_output_files(outputs_dir)
    different_filenames: list[str] = []

    if before_dir is not None and after_dir is not None:
        matched_pairs = find_matched_svg_pairs(
            before_dir,
            after_dir,
            report_path=outputs_dir / "unmatched_svgs.txt",
        )

        for matched_before_path, matched_after_path in matched_pairs:
            matched_before_svg = matched_before_path.read_text(encoding="utf-8")
            matched_after_svg = matched_after_path.read_text(encoding="utf-8")
            processed_before_svg = preprocess_svg(matched_before_svg, remove_ids or [])
            processed_after_svg = preprocess_svg(matched_after_svg, remove_ids or [])
            before_png = render_svg_to_png(processed_before_svg)
            after_png = render_svg_to_png(processed_after_svg)

            if not compare_png_bytes(before_png, after_png):
                different_filenames.append(matched_before_path.name)

        (outputs_dir / "different.txt").write_text(
            "".join(f"{filename}\n" for filename in different_filenames),
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

    print("Start svg pixel matching")


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--before-dir", type=Path, required=True)
    parser.add_argument("--after-dir", type=Path, required=True)
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


if __name__ == "__main__":
    run_cli()
