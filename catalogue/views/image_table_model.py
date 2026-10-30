"""Qt table model + filter proxy that let a QTableView show the catalogue.

ImageTableModel doesn't own any data. It is an adapter that reads from
ImageCatalogue and tells the QTableView whenever rows are added, removed
or changed. All its methods must be called from the GUI thread.
"""
from PyQt6.QtCore import Qt, QAbstractTableModel, QModelIndex, QSortFilterProxyModel
from PyQt6.QtGui import QIcon

from catalogue.model.catalogue import ImageCatalogue

COLUMNS = ["Preview", "Name", "Title", "Dimensions", "Format", "Size (KB)", "Rating", "Tags"]
SORT_ROLE = Qt.ItemDataRole.UserRole


class ImageTableModel(QAbstractTableModel):
    def __init__(self, catalogue, parent=None):
        super().__init__(parent)
        self._catalogue = catalogue
        self._icons = {}    # cache so we don't reload thumbnails on every repaint

    def rowCount(self, parent=QModelIndex()):
        return 0 if parent.isValid() else len(self._catalogue)

    def columnCount(self, parent=QModelIndex()):
        return 0 if parent.isValid() else len(COLUMNS)

    def headerData(self, section, orientation, role=Qt.ItemDataRole.DisplayRole):
        if orientation == Qt.Orientation.Horizontal and role == Qt.ItemDataRole.DisplayRole:
            return COLUMNS[section]
        return None

    def data(self, index, role=Qt.ItemDataRole.DisplayRole):
        if not index.isValid():
            return None
        item = self._catalogue.get(index.row())
        column = index.column()

        if role == Qt.ItemDataRole.DisplayRole:
            values = [
                "",
                item.file_name,
                item.title,
                item.dimensions,
                item.image_format,
                f"{item.size_kb:.1f}",
                "★" * item.rating,
                ", ".join(item.tags),
            ]
            return values[column]

        if role == SORT_ROLE:
            # Raw values so numbers sort as numbers, not as text
            values = [
                item.file_name.lower(),
                item.file_name.lower(),
                item.title.lower(),
                item.width * item.height,
                item.image_format,
                item.file_size,
                item.rating,
                ", ".join(item.tags),
            ]
            return values[column]

        if role == Qt.ItemDataRole.DecorationRole and column == 0:
            return self._icon_for(item)

        if role == Qt.ItemDataRole.ToolTipRole:
            return item.path

        if role == Qt.ItemDataRole.TextAlignmentRole and column in (5, 6):
            return Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter

        return None

    def _icon_for(self, item):
        if item.thumbnail_path not in self._icons:
            self._icons[item.thumbnail_path] = QIcon(item.thumbnail_path)
        return self._icons[item.thumbnail_path]

    # ---- changes (called by the controller) ----

    def add_item(self, item):
        if self._catalogue.contains(item.path):
            return False
        row = len(self._catalogue)
        self.beginInsertRows(QModelIndex(), row, row)
        self._catalogue.add(item)
        self.endInsertRows()
        return True

    def remove_row(self, row):
        self.beginRemoveRows(QModelIndex(), row, row)
        item = self._catalogue.remove(row)
        self.endRemoveRows()
        return item

    def refresh_row(self, row):
        left = self.index(row, 0)
        right = self.index(row, len(COLUMNS) - 1)
        self.dataChanged.emit(left, right)

    def set_items(self, items):
        self.beginResetModel()
        self._catalogue.replace_all(items)
        self._icons.clear()
        self.endResetModel()


class ImageFilterProxy(QSortFilterProxyModel):
    """Sits between the table model and the view to do searching and sorting.

    The actual "does this image match?" rule lives in ImageCatalogue.matches
    so it can be unit tested without Qt.
    """

    def __init__(self, catalogue, parent=None):
        super().__init__(parent)
        self._catalogue = catalogue
        self._search_text = ""
        self.setSortRole(SORT_ROLE)

    def set_search_text(self, text):
        self.beginFilterChange()
        self._search_text = text
        self.endFilterChange()

    def filterAcceptsRow(self, source_row, source_parent):
        item = self._catalogue.get(source_row)
        return ImageCatalogue.matches(item, self._search_text)
