from PIL import Image
from io import BytesIO


def pngify(image: Image) -> Image:
    """
    This function will convert image with
    not suitable format to PNG. Well compressed
    JPEG converted with this func is a good choice.

    Arguments:
        image (``Image``):
            Target (non PNG) image.
    """
    memfile = BytesIO()
    image.save(memfile, 'PNG')
    return Image.open(memfile)
