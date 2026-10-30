"""The main window (the View).

This class only builds widgets and shows things. It does not decide
anything. When the user does something, the window emits a signal and the
controller decides what should happen.
"""
from PyQt6.QtCore import Qt, QSize, pyqtSignal
from PyQt6.QtGui import QAction, QKeySequence, QPixmap
from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QSplitter, QVBoxLayout, QHBoxLayout, QFormLayout,
    QTableView, QLineEdit, QLabel, QSpinBox, QPushButton, QGroupBox,
    QProgressBar, QFileDialog, QMessageBox, QAbstractItemView, QHeaderView,
)

from catalogue.model.image_item import MAX_RATING, MIN_RATING, MAX_TITLE_LENGTH


class PreviewLabel(QLabel):
    """A QLabel that keeps its picture scaled to fit when the window resizes."""

    def __init__(self):
        super().__init__("Select an image to preview it")
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setMinimumSize(250, 200)
        self.setStyleSheet("background: #2b2b2b; color: #bbbbbb; border-radius: 4px;")
        self._pixmap = None

    def set_image(self, path):
        pixmap = QPixmap(path)
        if pixmap.isNull():
            self._pixmap = None
            self.setText("Could not load this image")
        else:
            self._pixmap = pixmap
            self._rescale()

    def clear_image(self):
        self._pixmap = None
        self.setText("Select an image to preview it")

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._rescale()

    def _rescale(self):
        if self._pixmap:
            self.setPixmap(self._pixmap.scaled(
                self.size(),
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            ))


class MainWindow(QMainWindow):
    # Custom signals the controller listens to
    open_folder_requested = pyqtSignal()
    open_catalogue_requested = pyqtSignal()
    save_catalogue_requested = pyqtSignal()
    remove_requested = pyqtSignal()
    cancel_requested = pyqtSignal()
    search_changed = pyqtSignal(str)
    selection_changed = pyqtSignal(int)            # source row, or -1 for none
    details_submitted = pyqtSignal(str, str, int)  # title, tags text, rating
    sound_toggled = pyqtSignal(bool)

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Image Catalogue")
        self.resize(1150, 700)
        self.close_check = None   # the controller sets this to decide if we can close
        self._proxy = None

        self._create_actions()
        self._create_menus()
        self._create_toolbar()
        self._create_central_area()
        self._create_status_bar()
        self.set_busy(False)
        self.clear_details()

    # ---- building the window ----

    def _create_actions(self):
        self.open_folder_action = QAction("&Add Folder...", self)
        self.open_folder_action.setShortcut(QKeySequence("Ctrl+O"))
        self.open_folder_action.setStatusTip("Scan a folder and add its images")
        self.open_folder_action.triggered.connect(self.open_folder_requested)

        self.open_catalogue_action = QAction("Open &Catalogue...", self)
        self.open_catalogue_action.setShortcut(QKeySequence("Ctrl+L"))
        self.open_catalogue_action.triggered.connect(self.open_catalogue_requested)

        self.save_action = QAction("&Save Catalogue", self)
        self.save_action.setShortcut(QKeySequence.StandardKey.Save)
        self.save_action.triggered.connect(self.save_catalogue_requested)

        self.remove_action = QAction("&Remove Image", self)
        self.remove_action.setShortcut(QKeySequence.StandardKey.Delete)
        self.remove_action.triggered.connect(self.remove_requested)

        self.cancel_action = QAction("&Cancel Scan", self)
        self.cancel_action.setShortcut(QKeySequence("Esc"))
        self.cancel_action.triggered.connect(self.cancel_requested)

        self.sound_action = QAction("Play &Sound When Done", self)
        self.sound_action.setCheckable(True)
        self.sound_action.setChecked(True)
        self.sound_action.toggled.connect(self.sound_toggled)

        self.exit_action = QAction("E&xit", self)
        self.exit_action.triggered.connect(self.close)

        self.about_action = QAction("&About", self)
        self.about_action.triggered.connect(self._show_about)

    def _create_menus(self):
        file_menu = self.menuBar().addMenu("&File")
        file_menu.addAction(self.open_folder_action)
        file_menu.addAction(self.open_catalogue_action)
        file_menu.addAction(self.save_action)
        file_menu.addSeparator()
        file_menu.addAction(self.exit_action)

        edit_menu = self.menuBar().addMenu("&Edit")
        edit_menu.addAction(self.remove_action)

        tools_menu = self.menuBar().addMenu("&Tools")
        tools_menu.addAction(self.cancel_action)
        tools_menu.addAction(self.sound_action)

        help_menu = self.menuBar().addMenu("&Help")
        help_menu.addAction(self.about_action)

    def _create_toolbar(self):
        toolbar = self.addToolBar("Main")
        toolbar.setMovable(False)
        toolbar.addAction(self.open_folder_action)
        toolbar.addAction(self.save_action)
        toolbar.addAction(self.remove_action)
        toolbar.addSeparator()
        toolbar.addAction(self.cancel_action)

    def _create_central_area(self):
        # Left side: search box + table
        self.search_box = QLineEdit()
        self.search_box.setPlaceholderText("Search by name, title or tag...")
        self.search_box.setClearButtonEnabled(True)
        self.search_box.textChanged.connect(self.search_changed)

        self.table = QTableView()
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.setSortingEnabled(True)
        self.table.setAlternatingRowColors(True)
        self.table.setIconSize(QSize(64, 64))
        self.table.verticalHeader().setDefaultSectionSize(70)
        self.table.verticalHeader().hide()

        left = QWidget()
        left_layout = QVBoxLayout(left)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.addWidget(self.search_box)
        left_layout.addWidget(self.table)

        # Right side: preview + details form
        self.preview = PreviewLabel()
        preview_box = QGroupBox("Preview")
        preview_layout = QVBoxLayout(preview_box)
        preview_layout.addWidget(self.preview)

        self.path_label = QLabel()
        self.path_label.setWordWrap(True)
        self.path_label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        self.info_label = QLabel()
        self.title_edit = QLineEdit()
        self.title_edit.setMaxLength(MAX_TITLE_LENGTH)
        self.tags_edit = QLineEdit()
        self.tags_edit.setPlaceholderText("e.g. holiday, beach, 2024")
        self.rating_spin = QSpinBox()
        self.rating_spin.setRange(MIN_RATING, MAX_RATING)
        self.rating_spin.setSuffix(" / 5")
        self.save_details_button = QPushButton("Save Details")
        self.save_details_button.clicked.connect(self._on_save_details_clicked)
        self.title_edit.returnPressed.connect(self._on_save_details_clicked)

        details_box = QGroupBox("Details")
        form = QFormLayout(details_box)
        form.addRow("File:", self.path_label)
        form.addRow("Info:", self.info_label)
        form.addRow("Title:", self.title_edit)
        form.addRow("Tags:", self.tags_edit)
        form.addRow("Rating:", self.rating_spin)
        form.addRow("", self.save_details_button)

        right = QWidget()
        right_layout = QVBoxLayout(right)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.addWidget(preview_box, stretch=3)
        right_layout.addWidget(details_box, stretch=2)

        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.addWidget(left)
        splitter.addWidget(right)
        splitter.setSizes([700, 450])
        self.setCentralWidget(splitter)

    def _create_status_bar(self):
        self.progress_bar = QProgressBar()
        self.progress_bar.setMaximumWidth(250)
        self.cancel_button = QPushButton("Cancel")
        self.cancel_button.clicked.connect(self.cancel_requested)
        self.count_label = QLabel()

        bar = self.statusBar()
        bar.addPermanentWidget(self.count_label)
        bar.addPermanentWidget(self.progress_bar)
        bar.addPermanentWidget(self.cancel_button)

    # ---- methods the controller calls ----

    def set_table_model(self, proxy):
        self._proxy = proxy
        self.table.setModel(proxy)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        for column, width in enumerate([80, 150, 130, 100, 65, 75, 80]):
            self.table.setColumnWidth(column, width)
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.sortByColumn(1, Qt.SortOrder.AscendingOrder)   # sort by name
        self.table.selectionModel().selectionChanged.connect(self._on_selection_changed)

    def selected_row(self):
        """The selected row in the *catalogue* (not the sorted/filtered view)."""
        indexes = self.table.selectionModel().selectedRows()
        if not indexes:
            return -1
        return self._proxy.mapToSource(indexes[0]).row()

    def show_details(self, item):
        self.preview.set_image(item.path)
        self.path_label.setText(item.path)
        self.info_label.setText(f"{item.dimensions}  |  {item.image_format}  |  {item.size_kb} KB")
        self.title_edit.setText(item.title)
        self.tags_edit.setText(", ".join(item.tags))
        self.rating_spin.setValue(item.rating)
        self._set_details_enabled(True)

    def clear_details(self):
        self.preview.clear_image()
        self.path_label.setText("-")
        self.info_label.setText("-")
        self.title_edit.clear()
        self.tags_edit.clear()
        self.rating_spin.setValue(0)
        self._set_details_enabled(False)

    def set_busy(self, busy):
        """Switch the window between 'scanning' and 'idle'."""
        self.progress_bar.setVisible(busy)
        self.cancel_button.setVisible(busy)
        self.cancel_button.setEnabled(busy)
        self.cancel_action.setEnabled(busy)
        self.open_folder_action.setEnabled(not busy)
        self.open_catalogue_action.setEnabled(not busy)
        if busy:
            self.progress_bar.setValue(0)

    def update_progress(self, done, total):
        self.progress_bar.setMaximum(max(total, 1))
        self.progress_bar.setValue(done)
        self.progress_bar.setFormat(f"{done} / {total}")

    def set_cancelling(self):
        self.cancel_button.setEnabled(False)
        self.cancel_action.setEnabled(False)
        self.show_status("Cancelling, finishing the images already in progress...")

    def set_image_count(self, count):
        self.count_label.setText(f"{count} image(s)")

    def show_status(self, message, timeout=0):
        self.statusBar().showMessage(message, timeout)

    def show_error(self, title, message):
        QMessageBox.critical(self, title, message)

    def show_warning(self, title, message):
        QMessageBox.warning(self, title, message)

    def ask_yes_no(self, title, question):
        answer = QMessageBox.question(self, title, question)
        return answer == QMessageBox.StandardButton.Yes

    def ask_save_discard_cancel(self, title, question):
        """Returns "save", "discard" or "cancel"."""
        buttons = (QMessageBox.StandardButton.Save | QMessageBox.StandardButton.Discard
                   | QMessageBox.StandardButton.Cancel)
        answer = QMessageBox.question(self, title, question, buttons)
        if answer == QMessageBox.StandardButton.Save:
            return "save"
        if answer == QMessageBox.StandardButton.Discard:
            return "discard"
        return "cancel"

    def ask_for_folder(self):
        return QFileDialog.getExistingDirectory(self, "Choose a folder of images")

    def ask_open_file(self):
        path, _ = QFileDialog.getOpenFileName(self, "Open catalogue", "", "Catalogue files (*.json)")
        return path

    def ask_save_file(self):
        path, _ = QFileDialog.getSaveFileName(self, "Save catalogue", "my_catalogue.json",
                                              "Catalogue files (*.json)")
        return path

    # ---- private slots ----

    def _set_details_enabled(self, enabled):
        for widget in (self.title_edit, self.tags_edit, self.rating_spin, self.save_details_button):
            widget.setEnabled(enabled)
        self.remove_action.setEnabled(enabled)

    def _on_selection_changed(self, *_):
        self.selection_changed.emit(self.selected_row())

    def _on_save_details_clicked(self):
        self.details_submitted.emit(self.title_edit.text(), self.tags_edit.text(),
                                    self.rating_spin.value())

    def _show_about(self):
        QMessageBox.about(self, "About Image Catalogue",
                          "Image Catalogue\n\nBrowse, tag and rate your local photos.\n"
                          "Built with Python and PyQt6.")

    def closeEvent(self, event):
        if self.close_check is None or self.close_check():
            event.accept()
        else:
            event.ignore()
