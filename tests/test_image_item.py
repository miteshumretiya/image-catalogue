"""Tests for the validation rules and the ImageItem data class.

Grouped as normal / boundary / invalid inputs to match the test plan.
"""
import pytest

from catalogue.model.image_item import (
    ImageItem, ValidationError, validate_title, parse_tags, validate_rating,
    MAX_TITLE_LENGTH, MAX_TAGS,
)


# ---- title ----

def test_title_normal_is_trimmed():
    assert validate_title("  Beach day  ") == "Beach day"


def test_title_at_max_length_is_accepted():
    assert len(validate_title("a" * MAX_TITLE_LENGTH)) == MAX_TITLE_LENGTH


def test_title_one_over_max_length_is_rejected():
    with pytest.raises(ValidationError):
        validate_title("a" * (MAX_TITLE_LENGTH + 1))


@pytest.mark.parametrize("bad", ["", "   ", "\t\n"])
def test_empty_title_is_rejected(bad):
    with pytest.raises(ValidationError):
        validate_title(bad)


# ---- tags ----

def test_tags_are_split_lowercased_and_deduplicated():
    assert parse_tags("Beach, sunset , BEACH") == ["beach", "sunset"]


def test_empty_tag_text_gives_empty_list():
    assert parse_tags("") == []
    assert parse_tags(" , , ") == []


def test_max_number_of_tags_is_accepted():
    text = ",".join(f"t{i}" for i in range(MAX_TAGS))
    assert len(parse_tags(text)) == MAX_TAGS


def test_too_many_tags_is_rejected():
    text = ",".join(f"t{i}" for i in range(MAX_TAGS + 1))
    with pytest.raises(ValidationError):
        parse_tags(text)


@pytest.mark.parametrize("bad", ["hello world", "tag!", "a" * 21, "café"])
def test_invalid_tag_characters_are_rejected(bad):
    with pytest.raises(ValidationError):
        parse_tags(bad)


def test_tag_with_hyphen_and_numbers_is_ok():
    assert parse_tags("black-white, 2024") == ["black-white", "2024"]


# ---- rating ----

@pytest.mark.parametrize("value, expected", [(0, 0), (5, 5), (3, 3), ("4", 4)])
def test_valid_ratings(value, expected):
    assert validate_rating(value) == expected


@pytest.mark.parametrize("bad", [-1, 6, 100])
def test_out_of_range_rating_is_rejected(bad):
    with pytest.raises(ValidationError):
        validate_rating(bad)


@pytest.mark.parametrize("bad", ["abc", None, ""])
def test_non_number_rating_is_rejected(bad):
    with pytest.raises(ValidationError):
        validate_rating(bad)


# ---- ImageItem ----

def test_item_dict_round_trip():
    item = ImageItem(path="/pics/a.jpg", file_name="a.jpg", width=10, height=20,
                     tags=["x"], rating=3)
    assert ImageItem.from_dict(item.to_dict()) == item


def test_from_dict_fills_in_file_name_and_ignores_unknown_keys():
    item = ImageItem.from_dict({"path": "/pics/b.png", "something_else": 1})
    assert item.file_name == "b.png"


def test_from_dict_without_path_is_rejected():
    with pytest.raises(ValueError):
        ImageItem.from_dict({"file_name": "x.jpg"})


def test_dimensions_and_size_properties():
    item = ImageItem(path="p", file_name="p", width=1920, height=1080, file_size=2048)
    assert item.dimensions == "1920 x 1080"
    assert item.size_kb == 2.0
