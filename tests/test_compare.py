from pathlib import Path

import pytest


pytest.importorskip("playwright.sync_api")
pytest.importorskip("PIL")

from PIL import Image

from svg_compare.compare import compare_png_bytes, write_diff_details
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


def test_write_diff_details_writes_side_by_side_and_red_diff_images() -> None:
    before_image = Image.new("RGBA", (2, 1))
    before_image.putdata(
        [
            (0, 255, 0, 255),
            (10, 20, 30, 255),
        ]
    )
    after_image = Image.new("RGBA", (2, 1))
    after_image.putdata(
        [
            (0, 255, 0, 255),
            (200, 210, 220, 255),
        ]
    )

    before_png = _to_png_bytes(before_image)
    after_png = _to_png_bytes(after_image)

    output_dir = Path("outputs") / "test_diff_details"
    if output_dir.exists():
        for path in output_dir.iterdir():
            path.unlink()
        output_dir.rmdir()

    write_diff_details(before_png, after_png, output_dir)

    combined_path = output_dir / "before_after.png"
    diff_path = output_dir / "diff.png"

    assert combined_path.exists()
    assert diff_path.exists()

    written_combined = Image.open(combined_path).convert("RGBA")
    written_diff = Image.open(diff_path).convert("RGBA")

    assert written_combined.size == (4, 1)
    assert _read_pixels(written_combined) == [
        (0, 255, 0, 255),
        (10, 20, 30, 255),
        (0, 255, 0, 255),
        (200, 210, 220, 255),
    ]
    assert _read_pixels(written_diff) == [
        (0, 0, 0, 0),
        (255, 0, 0, 255),
    ]

    for path in output_dir.iterdir():
        path.unlink()
    output_dir.rmdir()


def test_write_diff_details_handles_different_png_sizes() -> None:
    before_image = Image.new("RGBA", (2, 1), (0, 255, 0, 255))
    after_image = Image.new("RGBA", (3, 1), (0, 255, 0, 255))

    before_png = _to_png_bytes(before_image)
    after_png = _to_png_bytes(after_image)

    output_dir = Path("outputs") / "test_diff_details_different_sizes"
    if output_dir.exists():
        for path in output_dir.iterdir():
            path.unlink()
        output_dir.rmdir()

    write_diff_details(before_png, after_png, output_dir)

    written_combined = Image.open(output_dir / "before_after.png").convert("RGBA")
    written_diff = Image.open(output_dir / "diff.png").convert("RGBA")

    assert written_combined.size == (5, 1)
    assert _read_pixels(written_combined) == [
        (0, 255, 0, 255),
        (0, 255, 0, 255),
        (0, 255, 0, 255),
        (0, 255, 0, 255),
        (0, 255, 0, 255),
    ]
    assert written_diff.size == (3, 1)
    assert _read_pixels(written_diff) == [
        (0, 0, 0, 0),
        (0, 0, 0, 0),
        (255, 0, 0, 255),
    ]

    for path in output_dir.iterdir():
        path.unlink()
    output_dir.rmdir()


def _to_png_bytes(image: Image.Image) -> bytes:
    from io import BytesIO

    buffer = BytesIO()
    image.save(buffer, format="PNG")
    return buffer.getvalue()


def _read_pixels(image: Image.Image) -> list[tuple[int, int, int, int]]:
    pixels: list[tuple[int, int, int, int]] = []
    for y in range(image.height):
        for x in range(image.width):
            pixels.append(image.getpixel((x, y)))
    return pixels
