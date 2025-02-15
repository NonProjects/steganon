from PIL import Image
from io import BytesIO
from typing import Optional

__all__ = ['pngify']


def pngify(image: Image, format: Optional[str] = None) -> Image:
    """
    This function will convert image with
    not suitable format to PNG. Well compressed
    JPEG converted with this func is a good choice.

    Arguments:
        image (``Image``):
            Target (non PNG) image.

        format (``str``, optional):
            Format to convert your ``image`` to. Default
            is 'PNG', but you can also use different
            lossless format like WEBP, TIFF, etc.
    """
    memfile = BytesIO()
    image.save(memfile, format or 'PNG')
    return Image.open(memfile)
