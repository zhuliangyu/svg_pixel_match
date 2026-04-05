from pathlib import Path

import pytest


pytest.importorskip("playwright.sync_api")

from svg_compare.render import PlaywrightSvgRenderer, render_svg_to_png, write_render_debug_details


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
            self.goto_calls: list[tuple[str, str, int | None]] = []
            self.evaluate_calls: list[str] = []
            self.timeout_calls: list[int] = []

        def set_viewport_size(self, viewport: dict[str, int]) -> None:
            self.viewport_calls.append(viewport)

        def goto(self, url: str, wait_until: str = "load", timeout: int | None = None) -> None:
            self.goto_calls.append((url, wait_until, timeout))

        def evaluate(self, script: str) -> None:
            self.evaluate_calls.append(script)

        def wait_for_timeout(self, timeout_ms: int) -> None:
            self.timeout_calls.append(timeout_ms)

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
    assert len(created_pages[0].goto_calls) == 2
    assert all(call[0].startswith("file:///") for call in created_pages[0].goto_calls)
    assert created_pages[0].goto_calls == [
        (created_pages[0].goto_calls[0][0], "load", 120000),
        (created_pages[0].goto_calls[1][0], "load", 120000),
    ]
    assert len(created_pages[0].evaluate_calls) == 4
    assert created_pages[0].timeout_calls == [200, 200]


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
            self.goto_calls: list[tuple[str, str, int | None]] = []
            self.evaluate_calls: list[str] = []
            self.timeout_calls: list[int] = []

        def set_viewport_size(self, viewport: dict[str, int]) -> None:
            return None

        def goto(self, url: str, wait_until: str = "load", timeout: int | None = None) -> None:
            self.goto_calls.append((url, wait_until, timeout))

        def evaluate(self, script: str) -> None:
            self.evaluate_calls.append(script)

        def wait_for_timeout(self, timeout_ms: int) -> None:
            self.timeout_calls.append(timeout_ms)

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
    assert len(fake_manager.playwright.chromium.browser.page.goto_calls) == 1
    assert fake_manager.playwright.chromium.browser.page.goto_calls[0][0].startswith("file:///")
    assert fake_manager.playwright.chromium.browser.page.goto_calls[0][1:] == ("load", 120000)
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
            self.goto_calls: list[tuple[str, str, int | None]] = []
            self.evaluate_calls: list[str] = []
            self.timeout_calls: list[int] = []

        def set_viewport_size(self, viewport: dict[str, int]) -> None:
            return None

        def goto(self, url: str, wait_until: str = "load", timeout: int | None = None) -> None:
            self.goto_calls.append((url, wait_until, timeout))
            if self.fail_once:
                self.fail_once = False
                raise Exception("Connection closed while reading from the driver")

        def evaluate(self, script: str) -> None:
            self.evaluate_calls.append(script)

        def wait_for_timeout(self, timeout_ms: int) -> None:
            self.timeout_calls.append(timeout_ms)

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


def test_write_render_debug_details_writes_page_screenshots_and_metadata(monkeypatch) -> None:
    output_dir = Path("outputs") / "test_render_debug_details"
    if output_dir.exists():
        for path in output_dir.iterdir():
            path.unlink()
        output_dir.rmdir()
    created_pages: list[FakePage] = []

    class FakeSvgLocator:
        @property
        def first(self) -> "FakeSvgLocator":
            return self

        def wait_for(self, state: str) -> None:
            assert state == "attached"

        def screenshot(self, type: str) -> bytes:
            assert type == "png"
            return b"\x89PNG\r\n\x1a\nsvg"

        def bounding_box(self) -> dict[str, float]:
            return {"x": 1.0, "y": 2.0, "width": 120.0, "height": 80.0}

        def get_attribute(self, name: str) -> str | None:
            attributes = {
                "width": "120",
                "height": "80",
                "viewBox": "0 0 120 80",
            }
            return attributes.get(name)

        def count(self) -> int:
            return 2

    class FakeCountLocator:
        def __init__(self, count: int) -> None:
            self._count = count

        def count(self) -> int:
            return self._count

    class FakePage:
        def __init__(self) -> None:
            self.goto_calls: list[tuple[str, str, int | None]] = []
            self.screenshot_calls: list[dict[str, object]] = []

        def set_viewport_size(self, viewport: dict[str, int]) -> None:
            return None

        def goto(self, url: str, wait_until: str = "load", timeout: int | None = None) -> None:
            self.goto_calls.append((url, wait_until, timeout))

        def evaluate(self, script: str):
            if "document.querySelectorAll('svg')" in script:
                return {"x": 4.0, "y": 5.0, "width": 300.0, "height": 200.0}
            if "document.documentElement.scrollWidth" in script:
                return {"scrollWidth": 320, "scrollHeight": 240}
            return None

        def wait_for_timeout(self, timeout_ms: int) -> None:
            return None

        def locator(self, selector: str):
            if selector == "svg":
                return FakeSvgLocator()
            counts = {
                "image": 1,
                "foreignObject": 0,
                "use": 3,
                "clipPath": 1,
                "mask": 0,
                "filter": 2,
            }
            return FakeCountLocator(counts[selector])

        def screenshot(self, type: str, clip: dict[str, float] | None = None, full_page: bool = False) -> bytes:
            assert type == "png"
            self.screenshot_calls.append({"clip": clip, "full_page": full_page})
            return b"\x89PNG\r\n\x1a\npage"

        @property
        def url(self) -> str:
            return "about:blank"

    class FakeBrowser:
        def new_page(self, viewport: dict[str, int], device_scale_factor: int) -> FakePage:
            page = FakePage()
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

    write_render_debug_details(
        '<svg width="120" height="80"></svg>',
        '<svg width="120" height="80"></svg>',
        output_dir,
    )

    assert (output_dir / "page_before.png").read_bytes().startswith(b"\x89PNG")
    assert (output_dir / "page_after.png").read_bytes().startswith(b"\x89PNG")
    debug_json = (output_dir / "render_debug.json").read_text(encoding="utf-8")
    assert '"svg_count": 2' in debug_json
    assert '"image_count": 1' in debug_json
    assert '"viewBox": "0 0 120 80"' in debug_json
    assert '"page_url": "about:blank"' in debug_json
    assert '"scrollWidth": 320' in debug_json
    assert '"scrollHeight": 240' in debug_json
    assert created_pages[0].screenshot_calls == [
        {"clip": {"x": 4.0, "y": 5.0, "width": 300.0, "height": 200.0}, "full_page": False},
        {"clip": {"x": 4.0, "y": 5.0, "width": 300.0, "height": 200.0}, "full_page": False},
    ]

    for path in output_dir.iterdir():
        path.unlink()
    output_dir.rmdir()


def _read_png_size(png_bytes: bytes) -> tuple[int, int]:
    width = int.from_bytes(png_bytes[16:20], byteorder="big")
    height = int.from_bytes(png_bytes[20:24], byteorder="big")
    return width, height
