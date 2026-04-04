from pathlib import Path

import pytest


pytest.importorskip("playwright.sync_api")

from svg_compare.render import PlaywrightSvgRenderer, render_svg_to_png


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
    debug_path = Path("outputs") / "debug" / "before" / "sample_same_1.png"

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
    debug_path = Path("outputs") / "debug" / "after" / "sample_same_1.png"

    if debug_path.exists():
        debug_path.unlink()

    render_svg_to_png(
        svg_text,
        debug=False,
        debug_output_path=debug_path,
    )

    assert not debug_path.exists()


def test_playwright_svg_renderer_reuses_single_page_for_multiple_renders(monkeypatch) -> None:
    created_pages: list[FakePage] = []

    class FakeLocator:
        @property
        def first(self) -> "FakeLocator":
            return self

        def wait_for(self, state: str) -> None:
            assert state == "attached"

        def screenshot(self, type: str) -> bytes:
            assert type == "png"
            return b"\x89PNG\r\n\x1a\nfake"

    class FakePage:
        def __init__(self) -> None:
            self.viewport_calls: list[dict[str, int]] = []
            self.content_calls: list[str] = []

        def set_viewport_size(self, viewport: dict[str, int]) -> None:
            self.viewport_calls.append(viewport)

        def set_content(self, svg_text: str) -> None:
            self.content_calls.append(svg_text)

        def locator(self, selector: str) -> FakeLocator:
            assert selector == "svg"
            return FakeLocator()

    class FakeBrowser:
        def new_page(self, viewport: dict[str, int], device_scale_factor: int) -> FakePage:
            assert device_scale_factor == 1
            page = FakePage()
            page.viewport_calls.append(viewport)
            created_pages.append(page)
            return page

        def close(self) -> None:
            return None

    class FakeChromium:
        def launch(self) -> FakeBrowser:
            return FakeBrowser()

    class FakePlaywright:
        chromium = FakeChromium()

    class FakeManager:
        def __enter__(self) -> FakePlaywright:
            return FakePlaywright()

        def __exit__(self, exc_type, exc, tb) -> None:
            return None

    monkeypatch.setattr("svg_compare.render.sync_playwright", lambda: FakeManager())

    renderer = PlaywrightSvgRenderer()
    renderer.start()

    first_png = renderer.render_svg_to_png('<svg width="120" height="120"></svg>')
    second_png = renderer.render_svg_to_png('<svg width="140" height="100"></svg>')

    renderer.close()

    assert first_png.startswith(b"\x89PNG")
    assert second_png.startswith(b"\x89PNG")
    assert len(created_pages) == 1
    assert created_pages[0].viewport_calls == [
        {"width": 120, "height": 120},
        {"width": 140, "height": 100},
    ]


def test_render_svg_to_png_uses_first_svg_locator_when_page_contains_multiple_svgs(monkeypatch) -> None:
    class FakeLocator:
        def __init__(self, name: str) -> None:
            self.name = name
            self.wait_called = False
            self.screenshot_called = False

        @property
        def first(self) -> "FakeLocator":
            return self

        def wait_for(self, state: str) -> None:
            assert state == "attached"
            self.wait_called = True

        def screenshot(self, type: str) -> bytes:
            assert type == "png"
            self.screenshot_called = True
            return b"\x89PNG\r\n\x1a\nfake"

    class FakePage:
        def __init__(self) -> None:
            self.svg_locator = FakeLocator("first-svg")

        def set_viewport_size(self, viewport: dict[str, int]) -> None:
            return None

        def set_content(self, svg_text: str) -> None:
            return None

        def locator(self, selector: str) -> FakeLocator:
            assert selector == "svg"
            return self.svg_locator

    class FakeBrowser:
        def __init__(self) -> None:
            self.page = FakePage()

        def new_page(self, viewport: dict[str, int], device_scale_factor: int) -> FakePage:
            return self.page

        def close(self) -> None:
            return None

    class FakeChromium:
        def __init__(self) -> None:
            self.browser = FakeBrowser()

        def launch(self) -> FakeBrowser:
            return self.browser

    class FakePlaywright:
        def __init__(self) -> None:
            self.chromium = FakeChromium()

    class FakeManager:
        def __init__(self) -> None:
            self.playwright = FakePlaywright()

        def __enter__(self) -> FakePlaywright:
            return self.playwright

        def __exit__(self, exc_type, exc, tb) -> None:
            return None

    fake_manager = FakeManager()
    monkeypatch.setattr("svg_compare.render.sync_playwright", lambda: fake_manager)

    renderer = PlaywrightSvgRenderer()
    renderer.start()

    png_bytes = renderer.render_svg_to_png(
        '<svg width="120" height="120" id="container_svg"><svg id="chart_svg"></svg></svg>'
    )

    renderer.close()

    assert png_bytes.startswith(b"\x89PNG")
    assert fake_manager.playwright.chromium.browser.page.svg_locator.wait_called is True
    assert fake_manager.playwright.chromium.browser.page.svg_locator.screenshot_called is True


def test_render_svg_to_png_restarts_renderer_and_retries_once_after_driver_disconnect(monkeypatch) -> None:
    created_pages: list[FakePage] = []

    class FakeLocator:
        @property
        def first(self) -> "FakeLocator":
            return self

        def wait_for(self, state: str) -> None:
            assert state == "attached"

        def screenshot(self, type: str) -> bytes:
            assert type == "png"
            return b"\x89PNG\r\n\x1a\nfake"

    class FakePage:
        def __init__(self, fail_once: bool) -> None:
            self.fail_once = fail_once

        def set_viewport_size(self, viewport: dict[str, int]) -> None:
            return None

        def set_content(self, svg_text: str) -> None:
            if self.fail_once:
                self.fail_once = False
                raise Exception("Connection closed while reading from the driver")

        def locator(self, selector: str) -> FakeLocator:
            assert selector == "svg"
            return FakeLocator()

    class FakeBrowser:
        def __init__(self, fail_once: bool) -> None:
            self.fail_once = fail_once

        def new_page(self, viewport: dict[str, int], device_scale_factor: int) -> FakePage:
            page = FakePage(self.fail_once)
            self.fail_once = False
            created_pages.append(page)
            return page

        def close(self) -> None:
            return None

    class FakeChromium:
        def __init__(self) -> None:
            self.launch_count = 0

        def launch(self) -> FakeBrowser:
            self.launch_count += 1
            return FakeBrowser(fail_once=self.launch_count == 1)

    class FakePlaywright:
        def __init__(self) -> None:
            self.chromium = FakeChromium()

    class FakeManager:
        def __init__(self) -> None:
            self.playwright = FakePlaywright()

        def __enter__(self) -> FakePlaywright:
            return self.playwright

        def __exit__(self, exc_type, exc, tb) -> None:
            return None

    fake_manager = FakeManager()
    monkeypatch.setattr("svg_compare.render.sync_playwright", lambda: fake_manager)

    renderer = PlaywrightSvgRenderer()
    renderer.start()

    png_bytes = renderer.render_svg_to_png('<svg width="120" height="120"></svg>')

    renderer.close()

    assert png_bytes.startswith(b"\x89PNG")
    assert fake_manager.playwright.chromium.launch_count == 2
    assert len(created_pages) == 2


def _read_png_size(png_bytes: bytes) -> tuple[int, int]:
    width = int.from_bytes(png_bytes[16:20], byteorder="big")
    height = int.from_bytes(png_bytes[20:24], byteorder="big")
    return width, height
