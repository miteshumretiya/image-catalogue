"""Tests for finding image files and making thumbnails."""
import os

import pytest
from PIL import Image

from catalogue.model.processing import (
    is_image_file, find_images, process_image, thumbnail_name, THUMBNAIL_SIZE,
)


@pytest.fixture
def image_folder(tmp_path):
    """A small folder with real images, a sub-folder, a text file and a fake jpg."""
    Image.new("RGB", (400, 300), "red").save(tmp_path / "a.jpg")
    Image.new("RGBA", (50, 80), "blue").save(tmp_path / "b.png")
    (tmp_path / "sub").mkdir()
    Image.new("L", (1000, 10), 128).save(tmp_path / "sub" / "c.bmp")
    (tmp_path / "notes.txt").write_text("hello")
    (tmp_path / "fake.jpg").write_text("not an image")
    return tmp_path


@pytest.mark.parametrize("name, expected", [
    ("photo.jpg", True), ("PHOTO.JPEG", True), ("x.png", True), ("x.webp", True),
    ("notes.txt", False), ("jpg", False), ("archive.jpg.zip", False),
])
def test_is_image_file(name, expected):
    assert is_image_file(name) == expected


def test_find_images_includes_subfolders_and_skips_other_files(image_folder):
    names = [os.path.basename(p) for p in find_images(str(image_folder))]
    assert sorted(names) == ["a.jpg", "b.png", "c.bmp", "fake.jpg"]


def test_find_images_empty_folder(tmp_path):
    assert find_images(str(tmp_path)) == []


def test_find_images_missing_folder():
    with pytest.raises(FileNotFoundError):
        find_images("/this/folder/does/not/exist")


def test_process_image_reads_details(image_folder, tmp_path):
    thumbs = tmp_path / "thumbs"
    item = process_image(str(image_folder / "a.jpg"), str(thumbs))
    assert (item.width, item.height) == (400, 300)
    assert item.image_format == "JPEG"
    assert item.file_size > 0
    assert item.title == "a"
    assert os.path.exists(item.thumbnail_path)


def test_thumbnail_fits_inside_max_size_and_keeps_aspect_ratio(image_folder, tmp_path):
    item = process_image(str(image_folder / "sub" / "c.bmp"), str(tmp_path / "thumbs"))
    with Image.open(item.thumbnail_path) as thumb:
        assert thumb.width <= THUMBNAIL_SIZE[0]
        assert thumb.height <= THUMBNAIL_SIZE[1]
        assert thumb.width == 128    # 1000x10 is very wide, so width hits the limit


def test_process_fake_image_raises(image_folder, tmp_path):
    with pytest.raises(OSError):
        process_image(str(image_folder / "fake.jpg"), str(tmp_path / "thumbs"))


def test_process_missing_file_raises(tmp_path):
    with pytest.raises(OSError):
        process_image(str(tmp_path / "gone.jpg"), str(tmp_path / "thumbs"))


def test_same_file_name_in_different_folders_gets_different_thumbnails():
    assert thumbnail_name("/one/IMG_0001.jpg") != thumbnail_name("/two/IMG_0001.jpg")
