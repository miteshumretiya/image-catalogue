# Image Catalogue

A small desktop app for organising a folder of photos. You point it at a folder, it scans the images in the background and makes thumbnails, and then you can search, preview, give each image a title, tags and a star rating, and save the catalogue to a file.

Built with Python 3, PyQt6 and Pillow for the Advanced Programming module (Assessment 2).

## Features

- Add a folder of images. Sub-folders are included, and the scan runs in the background with a progress bar and a Cancel button.
- Thumbnails and image details (size, format, file size) shown in a sortable table.
- Large preview of the selected image.
- Edit title, tags and rating, with input checking.
- Search by file name, title or tag.
- Save and open catalogues (`.json` files).
- A short sound plays when a scan finishes (QtMultimedia). It can be turned off in the Tools menu.

## Requirements

- Python 3.10 or newer
- Packages: `PyQt6` and `Pillow` (see `requirements.txt`)
- For development: `pytest` and `pyinstaller` (see `requirements-dev.txt`)

## Setup and run from source

```bash
python -m venv .venv
```
Activate it. On Windows:
```bash
.venv\Scripts\activate
```
On macOS / Linux:
```bash
source .venv/bin/activate
```
Then:
```bash
pip install -r requirements-dev.txt
```
```bash
python main.py
```

To get some test pictures (30 images plus one broken file):
```bash
python tools/make_sample_images.py sample_images 30
```

## Run the tests

```bash
python -m pytest -v
```

## Run the performance investigation

```bash
python benchmark/benchmark.py 40
```

## Build the standalone app (PyInstaller)

```bash
pyinstaller image_catalogue.spec
```

- **macOS:** the app is created as `dist/ImageCatalogue.app`. Double-click it in Finder (or run `open dist/ImageCatalogue.app`). You can copy it to the Applications folder.
- **Windows:** the app is created in `dist/ImageCatalogue/`. Copy that whole folder and run `ImageCatalogue.exe`.

Python does not need to be installed on the computer that runs the built app. Build on the same operating system you want to run it on, because PyInstaller does not cross-compile. Tested on macOS 26.6 (Intel) with Python 3.14.7.

## Run the manual test walkthrough

```bash
python tools/gui_walkthrough.py
```

This opens the real window, works through the manual test plan, and saves screenshots and results to `docs/evidence/`.

## Troubleshooting (macOS)

If `python main.py` stops with `Could not find the Qt platform plugin "cocoa"`, macOS has marked the files inside the `.venv` folder as hidden, and Qt skips hidden plugin files. Remove the flag and run it again:

```bash
chflags -R nohidden .venv
```

## Project structure

```
main.py                      starts the app
catalogue/
  model/                     data + processing (no GUI code)
    image_item.py            ImageItem class and validation rules
    catalogue.py             ImageCatalogue: list of images, search, save/load
    processing.py            find image files, make thumbnails (Pillow)
  views/                     what the user sees
    main_window.py           QMainWindow, menus, toolbar, preview, form
    image_table_model.py     Qt table model + search/sort proxy
  controller/
    main_controller.py       connects the window, the data and the worker
  workers/
    scan_worker.py           background scan (QThread + thread pool, lock)
tests/                       automated tests (pytest)
benchmark/benchmark.py       performance and parallelism investigation
tools/                       sample image maker, sound maker, race-condition demo
assets/done.wav              completion sound
docs/                        design, test plan, performance, git, report
image_catalogue.spec         PyInstaller build configuration
```

## Where data is stored

Thumbnails are cached in `~/.image_catalogue/thumbnails`. Catalogues are saved wherever you choose. The app never changes or deletes your original images.
