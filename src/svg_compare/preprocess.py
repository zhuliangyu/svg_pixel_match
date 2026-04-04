import xml.etree.ElementTree as ET

SVG_NAMESPACE = "http://www.w3.org/2000/svg"
ET.register_namespace("", SVG_NAMESPACE)


def preprocess_svg(svg_text: str, remove_ids: list[str]) -> str:
    root = ET.fromstring(svg_text)

    for parent in root.iter():
        for child in list(parent):
            child_id = child.attrib.get("id")
            if child_id in remove_ids:
                parent.remove(child)
    # ET.tostring(...) 时，可能把默认命名空间写成 ns0:svg、ns0:rect 这种前缀形式
    # 导致 Playwright 渲染时找不到 svg 元素
    # 所以需要ET.register_namespace("", SVG_NAMESPACE)
    return ET.tostring(root, encoding="unicode")
