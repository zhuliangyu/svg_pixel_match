from pathlib import Path

import pytest


pytest.importorskip("playwright.sync_api")
pytest.importorskip("PIL")

from svg_compare.compare import compare_png_bytes
from svg_compare.preprocess import preprocess_svg
from svg_compare.render import render_svg_to_png


FIXTURES_DIR = Path(__file__).parent / "fixtures"
BEFORE_DIR = FIXTURES_DIR / "before"
AFTER_DIR = FIXTURES_DIR / "after"


def test_compare_png_bytes_returns_true_for_identical_rendered_images() -> None:
    before_svg = (BEFORE_DIR / "sample_same_1.svg").read_text(encoding="utf-8")
    after_svg = (AFTER_DIR / "sample_same_1.svg").read_text(encoding="utf-8")

    before_png = render_svg_to_png(preprocess_svg(before_svg, remove_ids=["mycurrenttime"]))
    after_png = render_svg_to_png(preprocess_svg(after_svg, remove_ids=["mycurrenttime"]))

    assert compare_png_bytes(before_png, after_png) is True


def test_compare_png_bytes_returns_false_for_different_rendered_images() -> None:
    before_svg = (BEFORE_DIR / "sample_diff_1.svg").read_text(encoding="utf-8")
    after_svg = (AFTER_DIR / "sample_diff_1.svg").read_text(encoding="utf-8")

    before_png = render_svg_to_png(preprocess_svg(before_svg, remove_ids=["mycurrenttime"]))
    after_png = render_svg_to_png(preprocess_svg(after_svg, remove_ids=["mycurrenttime"]))

    assert compare_png_bytes(before_png, after_png) is False
