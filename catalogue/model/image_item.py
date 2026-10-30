"""ImageItem holds everything we know about one image in the catalogue.

The validation functions live here too, so the rules for "what is a valid
title / tag / rating" are in one place and can be unit tested without a GUI.
"""
import os
import re
from dataclasses import dataclass, field, asdict, fields

MAX_TITLE_LENGTH = 100
MAX_TAGS = 10
MIN_RATING = 0
MAX_RATING = 5

# A tag is 1-20 letters, digits or hyphens, e.g. "holiday", "2024", "black-white"
TAG_PATTERN = re.compile(r"^[a-z0-9-]{1,20}$")


class ValidationError(ValueError):
    """Raised when the user enters something we can't accept."""


@dataclass
class ImageItem:
    path: str
    file_name: str
    width: int = 0
    height: int = 0
    image_format: str = ""
    file_size: int = 0          # in bytes
    thumbnail_path: str = ""
    title: str = ""
    tags: list = field(default_factory=list)
    rating: int = 0

    @property
    def dimensions(self):
        return f"{self.width} x {self.height}"

    @property
    def size_kb(self):
        return round(self.file_size / 1024, 1)

    def to_dict(self):
        return asdict(self)

    @classmethod
    def from_dict(cls, data):
        """Build an ImageItem from a dict loaded from a JSON catalogue file."""
        if not isinstance(data, dict) or not data.get("path"):
            raise ValueError("Every catalogue entry needs a 'path'.")

        # Ignore any keys we don't recognise so an edited file doesn't crash us
        known = {f.name for f in fields(cls)}
        clean = {key: value for key, value in data.items() if key in known}
        clean.setdefault("file_name", os.path.basename(data["path"]))
        return cls(**clean)


def validate_title(text):
    title = text.strip()
    if not title:
        raise ValidationError("Title cannot be empty.")
    if len(title) > MAX_TITLE_LENGTH:
        raise ValidationError(f"Title must be {MAX_TITLE_LENGTH} characters or fewer.")
    return title


def parse_tags(text):
    """Turn "Beach, sunset , beach" into ["beach", "sunset"]."""
    tags = []
    for part in text.split(","):
        tag = part.strip().lower()
        if not tag or tag in tags:
            continue
        if not TAG_PATTERN.match(tag):
            raise ValidationError(
                f"'{tag}' is not a valid tag. Use letters, numbers or hyphens (max 20 characters)."
            )
        tags.append(tag)

    if len(tags) > MAX_TAGS:
        raise ValidationError(f"An image can have at most {MAX_TAGS} tags.")
    return tags


def validate_rating(value):
    try:
        rating = int(value)
    except (TypeError, ValueError):
        raise ValidationError("Rating must be a whole number.")
    if not MIN_RATING <= rating <= MAX_RATING:
        raise ValidationError(f"Rating must be between {MIN_RATING} and {MAX_RATING}.")
    return rating
