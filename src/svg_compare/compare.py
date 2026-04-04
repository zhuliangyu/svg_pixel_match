from io import BytesIO

from PIL import Image


def compare_png_bytes(left_png: bytes, right_png: bytes) -> bool:
    left_image = Image.open(BytesIO(left_png)).convert("RGBA")
    right_image = Image.open(BytesIO(right_png)).convert("RGBA")

    if left_image.size != right_image.size:
        return False

    return left_image.tobytes() == right_image.tobytes()
