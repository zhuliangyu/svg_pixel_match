from pathlib import Path

from svg_compare.pairing import find_matched_svg_pairs


FIXTURES_DIR = Path(__file__).parent / "fixtures"
BEFORE_DIR = FIXTURES_DIR / "before"
AFTER_DIR = FIXTURES_DIR / "after"


def test_find_matched_svg_pairs_returns_only_same_named_svg_files() -> None:
    pairs = find_matched_svg_pairs(BEFORE_DIR, AFTER_DIR)

    pair_names = [(before.name, after.name) for before, after in pairs]

    assert pair_names == [
        ("sample_diff_1.svg", "sample_diff_1.svg"),
        ("sample_diff_2.svg", "sample_diff_2.svg"),
        ("sample_same_1.svg", "sample_same_1.svg"),
        ("sample_same_2.svg", "sample_same_2.svg"),
    ]


def test_find_matched_svg_pairs_ignores_non_svg_and_unmatched_files() -> None:
    pairs = find_matched_svg_pairs(BEFORE_DIR, AFTER_DIR)

    matched_names = {before.name for before, _ in pairs}

    assert "ignore_me.pdf" not in matched_names
    assert "after_only_unmatched.svg" not in matched_names


def test_find_matched_svg_pairs_writes_unmatched_svg_names_to_reports_file() -> None:
    report_path = Path("outputs") / "unmatched_svgs.txt"

    find_matched_svg_pairs(BEFORE_DIR, AFTER_DIR, report_path=report_path)

    assert report_path.exists()
    assert report_path.read_text(encoding="utf-8") == "after_only_unmatched.svg\n"
