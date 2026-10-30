"""ImageCatalogue is the main data store: the list of images plus save/load.

It deliberately has no Qt code in it. The GUI talks to it through the
controller and the table model, which keeps this class easy to test.
"""
import json

from .image_item import ImageItem, validate_title, parse_tags, validate_rating

FILE_VERSION = 1


class CatalogueError(Exception):
    """Raised when a catalogue file can't be read or written."""


class ImageCatalogue:
    def __init__(self):
        self._items = []
        self._paths = set()     # quick duplicate check
        self.modified = False   # True when there are unsaved changes

    def __len__(self):
        return len(self._items)

    def get(self, index):
        return self._items[index]

    def items(self):
        return list(self._items)

    def contains(self, path):
        return path in self._paths

    def add(self, item):
        """Add an image. Returns False if that file is already in the catalogue."""
        if item.path in self._paths:
            return False
        self._items.append(item)
        self._paths.add(item.path)
        self.modified = True
        return True

    def remove(self, index):
        item = self._items.pop(index)
        self._paths.discard(item.path)
        self.modified = True
        return item

    def replace_all(self, items):
        self._items = []
        self._paths = set()
        for item in items:
            self.add(item)
        self.modified = False

    def update_details(self, index, title, tags_text, rating):
        """Validate everything first, then change the item.

        If any field is invalid a ValidationError is raised and the item is
        left exactly as it was (we never half-update it).
        """
        clean_title = validate_title(title)
        clean_tags = parse_tags(tags_text)
        clean_rating = validate_rating(rating)

        item = self._items[index]
        item.title = clean_title
        item.tags = clean_tags
        item.rating = clean_rating
        self.modified = True
        return item

    @staticmethod
    def matches(item, search_text):
        """True if the search text appears in the file name, title or any tag."""
        text = search_text.strip().lower()
        if not text:
            return True
        return (
            text in item.file_name.lower()
            or text in item.title.lower()
            or any(text in tag for tag in item.tags)
        )

    def search(self, search_text):
        return [item for item in self._items if self.matches(item, search_text)]

    # ---- saving and loading ----

    def save(self, file_path):
        data = {
            "version": FILE_VERSION,
            "images": [item.to_dict() for item in self._items],
        }
        try:
            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
        except OSError as e:
            raise CatalogueError(f"Could not save the catalogue:\n{e}")
        self.modified = False

    @staticmethod
    def read_file(file_path):
        """Read a catalogue file and return a list of ImageItems.

        This doesn't touch the current catalogue, so if the file is broken
        the user's existing data is still safe.
        """
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except FileNotFoundError:
            raise CatalogueError(f"File not found:\n{file_path}")
        except json.JSONDecodeError as e:
            raise CatalogueError(f"This file is not a valid catalogue (bad JSON):\n{e}")
        except OSError as e:
            raise CatalogueError(f"Could not open the file:\n{e}")

        if not isinstance(data, dict) or not isinstance(data.get("images"), list):
            raise CatalogueError("This file is not a valid catalogue (no 'images' list).")

        try:
            return [ImageItem.from_dict(entry) for entry in data["images"]]
        except (TypeError, ValueError) as e:
            raise CatalogueError(f"The catalogue contains a broken entry:\n{e}")
