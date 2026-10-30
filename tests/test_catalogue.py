"""Tests for ImageCatalogue: adding, removing, editing, searching, save/load."""
import json

import pytest

from catalogue.model.catalogue import ImageCatalogue, CatalogueError
from catalogue.model.image_item import ImageItem, ValidationError


def make_item(name, title="", tags=None):
    return ImageItem(path=f"/pics/{name}", file_name=name, title=title, tags=tags or [])


@pytest.fixture
def catalogue():
    cat = ImageCatalogue()
    cat.add(make_item("beach.jpg", "Beach day", ["holiday", "sea"]))
    cat.add(make_item("cat.png", "My cat", ["pets"]))
    cat.add(make_item("mountain.jpg", "Alps", ["holiday", "snow"]))
    return cat


def test_add_and_count(catalogue):
    assert len(catalogue) == 3
    assert catalogue.contains("/pics/cat.png")


def test_duplicate_path_is_not_added(catalogue):
    assert catalogue.add(make_item("cat.png")) is False
    assert len(catalogue) == 3


def test_remove(catalogue):
    removed = catalogue.remove(1)
    assert removed.file_name == "cat.png"
    assert len(catalogue) == 2
    assert not catalogue.contains("/pics/cat.png")
    # once removed it can be added again
    assert catalogue.add(make_item("cat.png")) is True


def test_update_details_valid(catalogue):
    catalogue.update_details(0, "  New title ", "Sun, Sea", 4)
    item = catalogue.get(0)
    assert item.title == "New title"
    assert item.tags == ["sun", "sea"]
    assert item.rating == 4
    assert catalogue.modified


def test_invalid_update_leaves_item_unchanged(catalogue):
    before = catalogue.get(0).to_dict()
    with pytest.raises(ValidationError):
        catalogue.update_details(0, "Good title", "good, bad tag!", 3)
    assert catalogue.get(0).to_dict() == before


@pytest.mark.parametrize("text, expected", [
    ("", 3),            # empty search shows everything
    ("holiday", 2),     # tag
    ("CAT", 1),         # file name, any case
    ("alps", 1),        # title
    ("zzz", 0),         # nothing
])
def test_search(catalogue, text, expected):
    assert len(catalogue.search(text)) == expected


def test_save_and_load_round_trip(catalogue, tmp_path):
    path = tmp_path / "cat.json"
    catalogue.save(path)
    assert catalogue.modified is False

    items = ImageCatalogue.read_file(path)
    assert [i.to_dict() for i in items] == [i.to_dict() for i in catalogue.items()]


def test_replace_all_clears_modified_flag(catalogue):
    new = ImageCatalogue()
    new.replace_all(catalogue.items())
    assert len(new) == 3
    assert new.modified is False


def test_load_missing_file(tmp_path):
    with pytest.raises(CatalogueError):
        ImageCatalogue.read_file(tmp_path / "nope.json")


def test_load_corrupt_json(tmp_path):
    path = tmp_path / "bad.json"
    path.write_text("{ this is not json")
    with pytest.raises(CatalogueError):
        ImageCatalogue.read_file(path)


@pytest.mark.parametrize("content", [
    [],                                  # a list, not a dict
    {"version": 1},                      # no images key
    {"images": "nope"},                  # images is not a list
    {"images": [{"title": "no path"}]},  # entry without a path
])
def test_load_wrong_structure(tmp_path, content):
    path = tmp_path / "wrong.json"
    path.write_text(json.dumps(content))
    with pytest.raises(CatalogueError):
        ImageCatalogue.read_file(path)


def test_save_to_bad_location_raises_catalogue_error(catalogue, tmp_path):
    with pytest.raises(CatalogueError):
        catalogue.save(tmp_path / "missing_folder" / "cat.json")
