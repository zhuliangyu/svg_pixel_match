from pathlib import Path

import pytest


pytest.importorskip("playwright.sync_api")

from svg_compare.render import render_svg_to_png


FIXTURES_DIR = Path(__file__).parent / "fixtures"
SAMPLE_SVG_PATH = FIXTURES_DIR / "before" / "sample_same_1.svg"


def test_render_svg_to_png_returns_png_bytes() -> None:
    svg_text = SAMPLE_SVG_PATH.read_text(encoding="utf-8")

    png_bytes = render_svg_to_png(svg_text)

    assert png_bytes.startswith(b"\x89PNG\r\n\x1a\n")
    assert len(png_bytes) > 8


def test_render_svg_to_png_preserves_svg_dimensions() -> None:
    svg_text = SAMPLE_SVG_PATH.read_text(encoding="utf-8")

    png_bytes = render_svg_to_png(svg_text)

    assert _read_png_size(png_bytes) == (120, 120)


def test_render_svg_to_png_writes_debug_png_into_outputs_before() -> None:
    svg_text = SAMPLE_SVG_PATH.read_text(encoding="utf-8")
    debug_path = Path("outputs") / "before" / "sample_same_1.png"

    if debug_path.exists():
        debug_path.unlink()

    render_svg_to_png(
        svg_text,
        debug=True,
        debug_output_path=debug_path,
    )

    assert debug_path.exists()
    assert debug_path.read_bytes().startswith(b"\x89PNG\r\n\x1a\n")


def test_render_svg_to_png_does_not_write_debug_png_when_flag_is_false() -> None:
    svg_text = SAMPLE_SVG_PATH.read_text(encoding="utf-8")
    debug_path = Path("outputs") / "after" / "sample_same_1.png"

    if debug_path.exists():
        debug_path.unlink()

    render_svg_to_png(
        svg_text,
        debug=False,
        debug_output_path=debug_path,
    )

    assert not debug_path.exists()


def _read_png_size(png_bytes: bytes) -> tuple[int, int]:
    width = int.from_bytes(png_bytes[16:20], byteorder="big")
    height = int.from_bytes(png_bytes[20:24], byteorder="big")
    return width, height
