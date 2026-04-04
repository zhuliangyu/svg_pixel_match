from pathlib import Path


def find_matched_svg_pairs(
    before_dir: Path,
    after_dir: Path,
    report_path: Path | None = None,
) -> list[tuple[Path, Path]]:
    before_svg_files = _collect_svg_files(before_dir)
    after_svg_files = _collect_svg_files(after_dir)

    matched_names = sorted(before_svg_files.keys() & after_svg_files.keys())
    unmatched_entries = sorted(
        [f"before/{name}" for name in before_svg_files.keys() - after_svg_files.keys()]
        + [f"after/{name}" for name in after_svg_files.keys() - before_svg_files.keys()]
    )

    if report_path is not None:
        report_path.parent.mkdir(parents=True, exist_ok=True)
        report_path.write_text(
            "".join(f"{entry}\n" for entry in unmatched_entries),
            encoding="utf-8",
        )

    return [(before_svg_files[name], after_svg_files[name]) for name in matched_names]


def _collect_svg_files(directory: Path) -> dict[str, Path]:
    return {path.name: path for path in directory.iterdir() if path.suffix.lower() == ".svg"}
