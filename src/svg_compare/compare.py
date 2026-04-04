from io import BytesIO
from pathlib import Path

from PIL import Image


def compare_png_bytes(left_png: bytes, right_png: bytes) -> bool:
    left_image = Image.open(BytesIO(left_png)).convert("RGBA")
    right_image = Image.open(BytesIO(right_png)).convert("RGBA")

    if left_image.size != right_image.size:
        return False

    return left_image.tobytes() == right_image.tobytes()


def write_diff_details(left_png: bytes, right_png: bytes, output_dir: Path) -> None:
    left_image = Image.open(BytesIO(left_png)).convert("RGBA")
    right_image = Image.open(BytesIO(right_png)).convert("RGBA")

    output_dir.mkdir(parents=True, exist_ok=True)
    _build_side_by_side_image(left_image, right_image).save(output_dir / "before_after.png")
    _build_diff_image(left_image, right_image).save(output_dir / "diff.png")


def _build_diff_image(left_image: Image.Image, right_image: Image.Image) -> Image.Image:
    diff_width = max(left_image.width, right_image.width)
    diff_height = max(left_image.height, right_image.height)
    diff_image = Image.new("RGBA", (diff_width, diff_height), (0, 0, 0, 0))
    left_pixels = left_image.load()
    right_pixels = right_image.load()
    diff_pixels = diff_image.load()

    for y in range(diff_image.height):
        for x in range(diff_image.width):
            left_pixel = _get_pixel_or_none(left_image, left_pixels, x, y)
            right_pixel = _get_pixel_or_none(right_image, right_pixels, x, y)
            if left_pixel == right_pixel:
                diff_pixels[x, y] = (0, 0, 0, 0)
            else:
                diff_pixels[x, y] = (255, 0, 0, 255)

    return diff_image


def _build_side_by_side_image(left_image: Image.Image, right_image: Image.Image) -> Image.Image:
    combined_width = left_image.width + right_image.width
    combined_height = max(left_image.height, right_image.height)
    combined_image = Image.new("RGBA", (combined_width, combined_height), (0, 0, 0, 0))
    combined_image.paste(left_image, (0, 0))
    combined_image.paste(right_image, (left_image.width, 0))
    return combined_image


def _get_pixel_or_none(
    image: Image.Image,
    pixels,
    x: int,
    y: int,
) -> tuple[int, int, int, int] | None:
    if x >= image.width or y >= image.height:
        return None
    return pixels[x, y]
