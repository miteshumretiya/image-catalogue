# Tasks 9-12: Test Plan, Manual Testing, Automated Testing and Debugging

## How I approached testing

I split testing into two parts:

- **Automated tests (pytest)** for everything that is pure logic: validation, the catalogue, file finding, thumbnail creation, the worker's results and the thread-safe counter. These run in under a second, so I could rerun them after every change.
- **Manual tests** for anything the user sees or clicks: menus, dialogs, the progress bar, cancel, the sound, and the packaged app. These are hard to automate reliably and need a person to judge "does this look and feel right".

Test types used (from the module):
- **Requirements/model-driven:** each test links to a requirement (FR1-FR10) from the design specification.
- **Criteria-driven:** for each input I tested **normal**, **boundary**, **invalid** and **exceptional** values.

Test data: `python tools/make_sample_images.py sample_images 30` creates 30 images (JPG and PNG, 4 sizes, some in a sub-folder), one fake `broken.jpg` and one `notes.txt`.

---

## Part A: Manual test plan and results (Task 10)

These tests were run on the real application window on macOS 26.6 (Python 3.14.7, PyQt6 6.12). To make the run repeatable I wrote `tools/gui_walkthrough.py`. It opens the real `MainWindow` and controller and does what a user would do: selecting rows, typing text, clicking buttons, choosing menu actions. Pop-up dialogs are answered automatically, and the script records what the app showed. It saves screenshots to `docs/evidence/`, and the full output is in `docs/evidence/gui_walkthrough_results.txt`. Hearing the sound (MT24), pressing keyboard shortcuts (MT26) and opening the packaged app (MT27) were checked by hand.

| ID | Req | Feature | Type | Input / conditions | Expected result | Actual result | Pass/Fail |
|----|-----|---------|------|--------------------|-----------------|---------------|-----------|
| MT01 | FR1, FR2 | Add folder | Normal | File > Add Folder, choose `sample_images` | 30 images appear with thumbnails; status says "Scan complete. 30 image(s) added. 1 file(s) could not be read." | | |
| MT02 | FR2 | Bad file handling | Exceptional | Same scan (folder has `broken.jpg`) | Warning dialog lists `broken.jpg`; the other 30 are still added; the app does not crash | | |
| MT03 | FR1 | Non-image files | Normal | Same scan (folder has `notes.txt`) | `notes.txt` is ignored silently | | |
| MT04 | FR2 | Responsiveness | Normal | Scan a big folder (`make_sample_images.py big 300`), then drag the window, scroll the table and type in search while it runs | Window keeps responding; rows appear while scanning | | |
| MT05 | FR3 | Progress | Normal | Watch status bar during MT04 | Progress bar counts up to e.g. "300 / 300", then hides | | |
| MT06 | FR3 | Cancel | Normal | Start a 300-image scan, press Cancel (or Esc) halfway | Status says "Scan cancelled. N image(s) were added before stopping"; Add Folder works again | | |
| MT07 | FR3 | Restart after cancel | Normal | After MT06, add the same folder again | Only the images not yet added are added (no duplicates) | | |
| MT08 | FR1 | Empty folder | Boundary | Add an empty folder | "Scan complete. 0 image(s) added."; no error | | |
| MT09 | FR1 | Rescan same folder | Boundary | Add `sample_images` twice | Second scan adds 0 new images; count stays 30 | | |
| MT10 | FR4 | Sorting | Normal | Click "Size (KB)" header twice | Rows sort smallest to largest, then largest to smallest (numerically, not as text) | | |
| MT11 | FR5 | Preview | Normal | Click a row | Large preview and details shown; resizing the window rescales the preview | | |
| MT12 | FR6 | Edit details | Normal | Title "Beach day", Tags "Sea, Holiday, sea", Rating 4, Save | Table updates; tags shown as "sea, holiday"; 4 stars | | |
| MT13 | FR6 | Empty title | Invalid | Clear title, press Save | Error "Title cannot be empty."; nothing changes | | |
| MT14 | FR6 | Bad tag | Invalid | Tags "hello world" | Error explaining allowed characters; nothing changes | | |
| MT15 | FR6 | Title length | Boundary | Type more than 100 characters | Text box stops at 100 characters | | |
| MT16 | FR6 | Rating limits | Boundary | Try to go below 0 or above 5 in the spin box | Spin box stays within 0-5 | | |
| MT17 | FR7 | Search | Normal | Type "holiday" | Only images with that tag/title/name are shown | | |
| MT18 | FR7 | Search, no match | Boundary | Type "zzzz" | Table is empty; clearing the search shows everything again | | |
| MT19 | FR8 | Remove | Normal | Select a row, Edit > Remove, choose Yes | Row disappears, count goes down, file still on disk | | |
| MT20 | FR8 | Remove, cancel | Normal | Same but choose No | Nothing removed | | |
| MT21 | FR9 | Save and open | Normal | Save as `test.json`, restart app, File > Open Catalogue | Same images with same titles/tags/ratings | | |
| MT22 | FR9 | Open broken file | Exceptional | Make a .json with random text and open it | Error dialog "not a valid catalogue"; current data unchanged | | |
| MT23 | FR9 | Unsaved changes | Normal | Edit something, close window | Save / Discard / Cancel dialog; Cancel keeps the app open | | |
| MT24 | FR10 | Sound | Normal | Finish a scan with sound on, then turn off Tools > Play Sound When Done and scan again | Chime plays the first time only | | |
| MT25 | FR3 | Close during scan | Exceptional | Start a big scan and close the window | Asked to stop the scan; app closes cleanly with no error | | |
| MT26 | - | Keyboard shortcuts | Normal | Ctrl+O, Ctrl+S, Delete, Esc | Each does the same as its menu item | | |
| MT27 | - | Packaged app | Normal | Build with `pyinstaller image_catalogue.spec`, open `dist/ImageCatalogue.app` from Finder, then repeat MT01 and MT24 | App starts without Python/venv, scans and plays sound | | |

---

## Part B: Automated tests (Task 11)

Run with `python -m pytest -v`. **Result: 68 passed** (macOS 26.6, Python 3.14.7, 30 October 2026).

| File | What is tested | Normal | Boundary | Invalid / exceptional |
|------|----------------|--------|----------|-----------------------|
| `test_image_item.py` (29 tests) | Title, tag and rating validation; ImageItem save/load as dict | trimmed title, valid tags, ratings 0-5, round trip | title exactly 100 chars vs 101; exactly 10 tags vs 11; rating 0 and 5 vs -1 and 6 | empty/space-only title, tags with spaces or symbols or accents, rating "abc"/None, dict without path |
| `test_catalogue.py` (19 tests) | Add, duplicate check, remove, edit, search, save/load | add/remove/edit, search by tag, title and name | empty search returns all, search with no matches | invalid edit leaves item unchanged; missing file, corrupt JSON, wrong structure, saving to a missing folder |
| `test_processing.py` (15 tests) | Finding images, reading details, thumbnails | finds images in sub-folders, correct width/height/format | empty folder; very wide image keeps aspect ratio within 128 px | missing folder, fake .jpg, missing file; same file name in two folders |
| `test_scan_worker.py` (5 tests) | Background worker and thread safety | 12 images + 1 broken: 12 added, 1 failure, progress 0/13 to 13/13 | empty folder | missing folder emits `scan_failed`; cancel before start adds nothing; **8 threads x 5000 updates gives exactly 40,000 on the locked counter** |

**Why these were automated.** These are the parts with clear right or wrong answers and lots of edge cases, which makes them good for automation. If I change a validation rule, the tests tell me straight away if I broke something.

**What stays manual, and why.** Things like whether the window stays responsive, whether the dialog wording makes sense, whether the sound plays, and whether the packaged .exe runs on another PC. These depend on a real screen, speakers and another computer, and they need human judgement. GUI automation (e.g. pytest-qt) was possible but would have added a lot of complexity for little benefit in a project this size.

---

## Part C: Debugging and corrective development (Task 12)

These are real problems I found while testing the app during development.

| # | Problem (what I saw) | Found by | Probable cause | Fix | Retest result |
|---|----------------------|----------|----------------|-----|---------------|
| D1 | After a scan, rows were in a random-looking order and changed between runs | Manual test MT01 | The thread pool finishes images in whatever order they complete (`as_completed`), and the table had no default sort | `sortByColumn(1, Ascending)` after setting the model, so the table always sorts by name | MT01 and MT10 pass; order is now stable |
| D2 | After saving "Beach, beach", the table showed "beach" but the form still showed "Beach, beach" | Manual test MT12 | The controller refreshed the table row but not the form | `save_details` now calls `window.show_details(item)` with the cleaned values | MT12 passes |
| D3 | Closing with unsaved changes only offered Yes/No, so there was no way to change your mind and stay in the app | Manual test MT23 | I used `ask_yes_no` for a question that needs three answers | New `ask_save_discard_cancel` dialog (Save / Discard / Cancel) | MT23 passes |
| D4 | The "pure Python" benchmark showed threads giving a 2.5x speed-up, which contradicted what I expected from the GIL | Performance investigation | Most of each task was JPEG decoding, which runs in C and releases the GIL, so I wasn't measuring pure-Python work | Decode at a reduced size with `img.draft()` so the Python loop dominates | On the Mac: threads 1.6x vs processes 2.7x, as expected |
| D5 | Scanning the same folder a second time said "Scan complete. 30 image(s) added." even though nothing new was added (the table still had 30 rows) | Manual test MT09, while writing the walkthrough script | `ScanWorker` counts every image it *reads*. The duplicate check happens later, on the GUI thread, in `ImageTableModel.add_item`, so the worker can't know which images were really new | The controller now counts the rows actually added (`added_count`, reset in `start_scan`, increased in `on_item_ready`) and uses that in the status message. Commit `Fix: rescanning a folder reported images already in the catalogue as added` | MT09 and MT07 rerun; all 68 automated tests still pass |
