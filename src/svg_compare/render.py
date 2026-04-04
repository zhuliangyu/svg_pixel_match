import re
from pathlib import Path

from playwright.sync_api import Page, Playwright, Browser, sync_playwright


class PlaywrightSvgRenderer:
    def __init__(self) -> None:
        self._playwright_manager = None
        self._playwright: Playwright | None = None
        self._browser: Browser | None = None
        self._page: Page | None = None

    def start(self) -> None:
        if self._browser is not None:
            return

        self._playwright_manager = sync_playwright()
        self._playwright = self._playwright_manager.__enter__()
        self._browser = self._playwright.chromium.launch()

    def close(self) -> None:
        if self._browser is not None:
            self._browser.close()
        if self._playwright_manager is not None and self._playwright is not None:
            self._playwright_manager.__exit__(None, None, None)

        self._playwright_manager = None
        self._playwright = None
        self._browser = None
        self._page = None

    def render_svg_to_png(
        self,
        svg_text: str,
        debug: bool = False,
        debug_output_path: Path | None = None,
    ) -> bytes:
        if self._browser is None:
            self.start()

        try:
            return self._render_svg_to_png_once(
                svg_text,
                debug=debug,
                debug_output_path=debug_output_path,
            )
        except Exception as exc:
            if not _is_driver_connection_closed_error(exc):
                raise

            self.close()
            self.start()
            return self._render_svg_to_png_once(
                svg_text,
                debug=debug,
                debug_output_path=debug_output_path,
            )

    def _render_svg_to_png_once(
        self,
        svg_text: str,
        debug: bool = False,
        debug_output_path: Path | None = None,
    ) -> bytes:
        if self._browser is None:
            self.start()

        width, height = _extract_dimensions(svg_text)
        if self._page is None:
            self._page = self._browser.new_page(
                viewport={"width": width, "height": height},
                device_scale_factor=1,
            )
        else:
            self._page.set_viewport_size({"width": width, "height": height})
        self._page.set_content(svg_text, timeout=120000)
        self._wait_for_render_stability()
        locator = self._page.locator("svg").first
        locator.wait_for(state="attached")
        png_bytes = locator.screenshot(type="png")

        if debug and debug_output_path is not None:
            debug_output_path.parent.mkdir(parents=True, exist_ok=True)
            debug_output_path.write_bytes(png_bytes)

        return png_bytes

    def _wait_for_render_stability(self) -> None:
        if self._page is None:
            return

        self._page.evaluate(
            "() => document.fonts ? document.fonts.ready.catch(() => undefined) : Promise.resolve()"
        )
        self._page.evaluate(
            "() => new Promise((resolve) => requestAnimationFrame(() => requestAnimationFrame(resolve)))"
        )
        self._page.wait_for_timeout(200)


def render_svg_to_png(
    svg_text: str,
    debug: bool = False,
    debug_output_path: Path | None = None,
) -> bytes:
    renderer = PlaywrightSvgRenderer()
    try:
        renderer.start()
        return renderer.render_svg_to_png(
            svg_text,
            debug=debug,
            debug_output_path=debug_output_path,
        )
    finally:
        renderer.close()


def _extract_dimensions(svg_text: str) -> tuple[int, int]:
    width_match = re.search(r'\bwidth="(\d+)"', svg_text)
    height_match = re.search(r'\bheight="(\d+)"', svg_text)

    if width_match is None or height_match is None:
        raise ValueError("SVG width and height are required")

    return int(width_match.group(1)), int(height_match.group(1))


def _is_driver_connection_closed_error(exc: Exception) -> bool:
    message = str(exc).lower()
    return "connection closed" in message and "driver" in message
