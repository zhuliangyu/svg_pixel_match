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

    if left_image.size != right_image.size:
        raise ValueError("PNG sizes must match to write diff details")

    output_dir.mkdir(parents=True, exist_ok=True)
    left_image.save(output_dir / "before.png")
    right_image.save(output_dir / "after.png")
    _build_diff_image(left_image, right_image).save(output_dir / "diff.png")


def _build_diff_image(left_image: Image.Image, right_image: Image.Image) -> Image.Image:
    diff_image = Image.new("RGBA", left_image.size, (0, 0, 0, 0))
    left_pixels = left_image.load()
    right_pixels = right_image.load()
    diff_pixels = diff_image.load()

    for y in range(left_image.height):
        for x in range(left_image.width):
            if left_pixels[x, y] == right_pixels[x, y]:
                diff_pixels[x, y] = (0, 0, 0, 0)
            else:
                diff_pixels[x, y] = (255, 0, 0, 255)

    return diff_image
