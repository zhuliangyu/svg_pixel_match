import re
from pathlib import Path

from playwright.sync_api import sync_playwright


def render_svg_to_png(
    svg_text: str,
    debug: bool = False,
    debug_output_path: Path | None = None,
) -> bytes:
    width, height = _extract_dimensions(svg_text)
    page_content = _build_html(svg_text, width, height)

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        page = browser.new_page(viewport={"width": width, "height": height}, device_scale_factor=1)
        page.set_content(page_content)
        png_bytes = page.locator("svg").screenshot(type="png")
        browser.close()

    if debug and debug_output_path is not None:
        debug_output_path.parent.mkdir(parents=True, exist_ok=True)
        debug_output_path.write_bytes(png_bytes)

    return png_bytes


def _extract_dimensions(svg_text: str) -> tuple[int, int]:
    width_match = re.search(r'\bwidth="(\d+)"', svg_text)
    height_match = re.search(r'\bheight="(\d+)"', svg_text)

    if width_match is None or height_match is None:
        raise ValueError("SVG width and height are required")

    return int(width_match.group(1)), int(height_match.group(1))


def _build_html(svg_text: str, width: int, height: int) -> str:
    return (
        "<!doctype html>"
        "<html>"
        "<body style='margin:0; background:white;'>"
        f"<div style='width:{width}px; height:{height}px;'>"
        f"{svg_text}"
        "</div>"
        "</body>"
        "</html>"
    )
