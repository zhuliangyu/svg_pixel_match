import xml.etree.ElementTree as ET


def preprocess_svg(svg_text: str, remove_ids: list[str]) -> str:
    root = ET.fromstring(svg_text)

    for parent in root.iter():
        for child in list(parent):
            child_id = child.attrib.get("id")
            if child_id in remove_ids:
                parent.remove(child)

    return ET.tostring(root, encoding="unicode")
