"""Image Catalogue - start the application from here.

    python main.py
"""
import os
import sys
from pathlib import Path

from PyQt6.QtWidgets import QApplication

from catalogue.controller.main_controller import MainController
from catalogue.model.catalogue import ImageCatalogue
from catalogue.views.main_window import MainWindow


def resource_path(relative):
    """Find bundled files both when running from source and from PyInstaller.

    PyInstaller unpacks data files into a temp folder stored in sys._MEIPASS.
    """
    base = getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base, relative)


def main():
    app = QApplication(sys.argv)
    app.setApplicationName("Image Catalogue")

    thumb_dir = Path.home() / ".image_catalogue" / "thumbnails"
    thumb_dir.mkdir(parents=True, exist_ok=True)

    window = MainWindow()
    controller = MainController(window, ImageCatalogue(), str(thumb_dir),
                                resource_path(os.path.join("assets", "done.wav")))
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
