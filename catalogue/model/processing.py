"""Image processing functions: finding image files and making thumbnails.

These are plain functions with no Qt in them, so they can be used by the
background worker, the benchmark script and the unit tests.
"""
import hashlib
import os

from PIL import Image

from .image_item import ImageItem

IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".gif", ".bmp", ".webp", ".tif", ".tiff"}
THUMBNAIL_SIZE = (128, 128)


def is_image_file(path):
    return os.path.splitext(path)[1].lower() in IMAGE_EXTENSIONS


def find_images(folder):
    """Return every image file inside a folder (including sub-folders)."""
    if not os.path.isdir(folder):
        raise FileNotFoundError(f"Folder not found: {folder}")

    found = []
    for root, _dirs, files in os.walk(folder):
        for name in files:
            if is_image_file(name):
                found.append(os.path.join(root, name))
    return sorted(found)


def thumbnail_name(image_path):
    """Make a unique file name for a thumbnail, based on the full image path.

    Two photos can both be called IMG_0001.jpg in different folders,
    so we hash the whole path instead of using the file name.
    """
    digest = hashlib.md5(os.path.abspath(image_path).encode("utf-8")).hexdigest()
    return digest + ".png"


def process_image(image_path, thumb_dir):
    """Read an image's details and save a small thumbnail.

    This is the slow part of the app (decoding and resizing a large photo),
    which is why the GUI runs it in the background.
    Raises OSError if the file is missing or isn't a real image.
    """
    with Image.open(image_path) as img:
        width, height = img.size
        image_format = img.format or "Unknown"

        thumb = img.copy()
        thumb.thumbnail(THUMBNAIL_SIZE)
        # PNG can't store some modes (e.g. CMYK), so convert them first
        if thumb.mode not in ("RGB", "RGBA"):
            thumb = thumb.convert("RGBA")

        os.makedirs(thumb_dir, exist_ok=True)
        thumb_path = os.path.join(thumb_dir, thumbnail_name(image_path))
        thumb.save(thumb_path, "PNG")

    return ImageItem(
        path=image_path,
        file_name=os.path.basename(image_path),
        width=width,
        height=height,
        image_format=image_format,
        file_size=os.path.getsize(image_path),
        thumbnail_path=thumb_path,
        title=os.path.splitext(os.path.basename(image_path))[0],
    )
