import io

from PIL import Image


def image_to_jpeg_bytes(image: Image.Image) -> bytes:
    image_bytes = io.BytesIO()
    image.convert("RGB").save(image_bytes, format="JPEG")
    return image_bytes.getvalue()
