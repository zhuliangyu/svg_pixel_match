from __future__ import annotations

import argparse
from pathlib import Path


SVG_HEADER = '<svg xmlns="http://www.w3.org/2000/svg" width="1600" height="1200" viewBox="0 0 1600 1200">'
SVG_FOOTER = "</svg>\n"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-root", type=Path, required=True)
    parser.add_argument("--pairs", type=int, default=500)
    parser.add_argument("--target-bytes", type=int, default=1_500_000)
    args = parser.parse_args()

    before_dir = args.output_root / "before"
    after_dir = args.output_root / "after"
    before_dir.mkdir(parents=True, exist_ok=True)
    after_dir.mkdir(parents=True, exist_ok=True)

    for index in range(args.pairs):
        filename = f"bench_{index:04d}.svg"
        before_path = before_dir / filename
        after_path = after_dir / filename
        if before_path.exists() and after_path.exists():
            continue

        shared = index < args.pairs // 2
        before_svg = build_svg(index=index, target_bytes=args.target_bytes, variant="before")
        after_svg = build_svg(
            index=index,
            target_bytes=args.target_bytes,
            variant="before" if shared else "after",
        )
        before_path.write_text(before_svg, encoding="utf-8")
        after_path.write_text(after_svg, encoding="utf-8")


def build_svg(index: int, target_bytes: int, variant: str) -> str:
    parts = [SVG_HEADER]
    parts.append(
        f'<rect id="bg-{variant}-{index}" x="0" y="0" width="1600" height="1200" fill="#f5f7fa" />'
    )

    change_offset = 0 if variant == "before" else 7
    change_fill = "#0055aa" if variant == "before" else "#aa5500"

    row = 0
    while encoded_length(parts) + len(SVG_FOOTER.encode("utf-8")) < target_bytes:
        x = (row * 37) % 1500
        y = (row * 53) % 1100
        width = 40 + (row % 9) * 7
        height = 30 + (row % 11) * 5
        radius = 8 + (row % 13)
        fill = f"#{(row * 17) % 256:02x}{(row * 29) % 256:02x}{(row * 43) % 256:02x}"
        stroke = f"#{(row * 11) % 256:02x}{(row * 19) % 256:02x}{(row * 23) % 256:02x}"
        text_value = f"node-{index:04d}-{row:06d}-{variant}"
        path_x = (x + change_offset) % 1550

        parts.append(
            f'<g id="g-{variant}-{index}-{row}">'
            f'<rect id="r-{variant}-{index}-{row}" x="{x}" y="{y}" width="{width}" height="{height}" '
            f'rx="{radius}" fill="{fill}" stroke="{stroke}" stroke-width="2" />'
            f'<circle id="c-{variant}-{index}-{row}" cx="{(x + width // 2) % 1600}" cy="{(y + height // 2) % 1200}" '
            f'r="{radius}" fill="{stroke}" opacity="0.55" />'
            f'<path id="p-{variant}-{index}-{row}" d="M{path_x} {y} C{(path_x + 10) % 1600} {(y + 30) % 1200}, '
            f'{(path_x + 60) % 1600} {(y + 40) % 1200}, {(path_x + 90) % 1600} {(y + 12) % 1200}" '
            f'fill="none" stroke="{change_fill if row == 3 else stroke}" stroke-width="3" />'
            f'<text id="t-{variant}-{index}-{row}" x="{x}" y="{(y + height + 12) % 1200}" '
            f'font-size="12" fill="#222222">{text_value}</text>'
            "</g>"
        )
        row += 1

    parts.append(SVG_FOOTER)
    return "".join(parts)


def encoded_length(parts: list[str]) -> int:
    return sum(len(part.encode("utf-8")) for part in parts)


if __name__ == "__main__":
    main()
