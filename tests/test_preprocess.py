from pathlib import Path
import xml.etree.ElementTree as ET

from svg_compare.preprocess import preprocess_svg


FIXTURES_DIR = Path(__file__).parent / "fixtures"
SAMPLE_SVG_PATH = FIXTURES_DIR / "before" / "sample_same_1.svg"
SVG_NS = {"svg": "http://www.w3.org/2000/svg"}


def test_preprocess_svg_removes_element_with_id_mycurrenttime() -> None:
    svg_text = SAMPLE_SVG_PATH.read_text(encoding="utf-8")

    processed_svg = preprocess_svg(svg_text, remove_ids=["mycurrenttime"])
    root = ET.fromstring(processed_svg)

    assert root.find(".//*[@id='mycurrenttime']", SVG_NS) is None
    assert root.find(".//*[@id='bg-before-a']", SVG_NS) is not None
    assert root.find(".//*[@id='dot-before-a']", SVG_NS) is not None


def test_preprocess_svg_removes_any_user_provided_id() -> None:
    svg_text = SAMPLE_SVG_PATH.read_text(encoding="utf-8")

    processed_svg = preprocess_svg(svg_text, remove_ids=["dot-before-a"])
    root = ET.fromstring(processed_svg)

    assert root.find(".//*[@id='dot-before-a']", SVG_NS) is None
    assert root.find(".//*[@id='mycurrenttime']", SVG_NS) is not None
    assert root.find(".//*[@id='bg-before-a']", SVG_NS) is not None


def test_preprocess_svg_does_not_fail_when_id_does_not_exist() -> None:
    svg_text = SAMPLE_SVG_PATH.read_text(encoding="utf-8")

    processed_svg = preprocess_svg(svg_text, remove_ids=["missing-id"])
    root = ET.fromstring(processed_svg)

    assert root.find(".//*[@id='bg-before-a']", SVG_NS) is not None
    assert root.find(".//*[@id='dot-before-a']", SVG_NS) is not None
    assert root.find(".//*[@id='mycurrenttime']", SVG_NS) is not None
