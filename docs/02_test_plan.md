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

These tests were run on the real application window on macOS 26.6 (Python 3.14.7, PyQt6 6.12). To make the run repeatable I wrote `tools/gui_walkthrough.py`. It opens the real `MainWindow` and controller and does what a user would do: selecting rows, typing text, clicking buttons, choosing menu actions. Pop-up dialogs are answered automatically, and the script records what the app showed. It saves screenshots to `docs/evidence/`, and the full output is in `docs/evidence/gui_walkthrough_results.txt`. Two things needed a person at the computer, and both were checked by hand: hearing the chime (MT24) and pressing the keyboard shortcuts (MT26). The packaged app (MT27) was checked by launching the built `.app` on its own, outside the virtual environment.

| ID | Req | Feature | Type | Input / conditions | Expected result | Actual result | Pass/Fail |
|----|-----|---------|------|--------------------|-----------------|---------------|-----------|
| MT01 | FR1, FR2 | Add folder | Normal | File > Add Folder, choose `sample_images` | 30 images appear with thumbnails; status says "Scan complete. 30 image(s) added. 1 file(s) could not be read." | 30 images with thumbnails. Status 'Scan complete. 30 image(s) added. 1 file(s) could not be read.' | Pass |
| MT02 | FR2 | Bad file handling | Exceptional | Same scan (folder has `broken.jpg`) | Warning dialog lists `broken.jpg`; the other 30 are still added; the app does not crash | Warning 'Some files were skipped' listed broken.jpg; the other 30 were still added | Pass |
| MT03 | FR1 | Non-image files | Normal | Same scan (folder has `notes.txt`) | `notes.txt` is ignored silently | notes.txt is not in the table and not reported as a failure | Pass |
| MT04 | FR2 | Responsiveness | Normal | Scan a big folder (`make_sample_images.py big 300`), then drag the window, scroll the table and type in search while it runs | Window keeps responding; rows appear while scanning | 200-image scan took 2.0s; a 20 ms timer on the GUI thread fired 64 times, longest gap 89 ms (window never froze) | Pass |
| MT05 | FR3 | Progress | Normal | Watch status bar during MT04 | Progress bar counts up to e.g. "300 / 300", then hides | Progress went (0, 201) -> (201, 201) in 202 updates; bar hidden afterwards: True | Pass |
| MT06 | FR3 | Cancel | Normal | Start a 300-image scan, press Cancel (or Esc) halfway | Status says "Scan cancelled. N image(s) were added before stopping"; Add Folder works again | Pressed Cancel: 'Scan cancelled. 64 image(s) were added before stopping. 1 file(s) could not be read.'. Add Folder enabled again: True | Pass |
| MT07 | FR3 | Restart after cancel | Normal | After MT06, add the same folder again | Only the images not yet added are added (no duplicates) | Scanned the same folder again: 'Scan complete. 136 image(s) added. 1 file(s) could not be read.'; 200 images in total (was 64), 0 duplicates | Pass |
| MT08 | FR1 | Empty folder | Boundary | Add an empty folder | "Scan complete. 0 image(s) added."; no error | Status 'Scan complete. 0 image(s) added.', 0 images, no dialogs | Pass |
| MT09 | FR1 | Rescan same folder | Boundary | Add `sample_images` twice | Second scan adds 0 new images; count stays 30 | Second scan of the same folder: status 'Scan complete. 0 image(s) added. 1 file(s) could not be read.', still 30 images | Pass |
| MT10 | FR4 | Sorting | Normal | Click "Size (KB)" header twice | Rows sort smallest to largest, then largest to smallest (numerically, not as text) | Ascending 10.0 .. 94.9 KB, descending 94.9 .. 10.0 KB (numeric order) | Pass |
| MT11 | FR5 | Preview | Normal | Click a row | Large preview and details shown; resizing the window rescales the preview | Preview and details of photo_001.jpg shown; preview rescaled 286px -> 468px wide when the window was enlarged | Pass |
| MT12 | FR6 | Edit details | Normal | Title "Beach day", Tags "Sea, Holiday, sea", Rating 4, Save | Table updates; tags shown as "sea, holiday"; 4 stars | Saved: title 'Beach day', tags ['sea', 'holiday'], rating 4; form now shows tags 'sea, holiday' | Pass |
| MT13 | FR6 | Empty title | Invalid | Clear title, press Save | Error "Title cannot be empty."; nothing changes | Error 'Title cannot be empty.'; image unchanged | Pass |
| MT14 | FR6 | Bad tag | Invalid | Tags "hello world" | Error explaining allowed characters; nothing changes | Error ''hello world' is not a valid tag. Use letters, numbers or hyphens (max 20 characters).'; image unchanged | Pass |
| MT15 | FR6 | Title length | Boundary | Type more than 100 characters | Text box stops at 100 characters | Typed 120 characters, the box kept 100 | Pass |
| MT16 | FR6 | Rating limits | Boundary | Try to go below 0 or above 5 in the spin box | Spin box stays within 0-5 | Set 9 -> 5; set -3 -> 0; step down from 0 -> 0 | Pass |
| MT17 | FR7 | Search | Normal | Type "holiday" | Only images with that tag/title/name are shown | Typed 'holiday': 1 row shown (the image tagged in MT12) | Pass |
| MT18 | FR7 | Search, no match | Boundary | Type "zzzz" | Table is empty; clearing the search shows everything again | Typed 'zzzz': 0 rows; after clearing: 30 rows | Pass |
| MT19 | FR8 | Remove | Normal | Select a row, Edit > Remove, choose Yes | Row disappears, count goes down, file still on disk | Answered Yes: 29 images left; photo_002.png still on disk: True | Pass |
| MT20 | FR8 | Remove, cancel | Normal | Same but choose No | Nothing removed | Answered No: still 30 images | Pass |
| MT21 | FR9 | Save and open | Normal | Save as `test.json`, restart app, File > Open Catalogue | Same images with same titles/tags/ratings | Saved test.json, opened it in a new window: 29 images; edited image has tags ['sea', 'holiday'], rating 4 | Pass |
| MT22 | FR9 | Open broken file | Exceptional | Make a .json with random text and open it | Error dialog "not a valid catalogue"; current data unchanged | Error 'Could not open catalogue': This file is not a valid catalogue (bad JSON):; still 29 images | Pass |
| MT23 | FR9 | Unsaved changes | Normal | Edit something, close window | Save / Discard / Cancel dialog; Cancel keeps the app open | Save/Discard/Cancel asked: True; Cancel kept the window open: True; Discard closed it: True | Pass |
| MT24 | FR10 | Sound | Normal | Finish a scan with sound on, then turn off Tools > Play Sound When Done and scan again | Chime plays the first time only | done.wav loaded: True; sound played 1 time(s) with the option on, 0 time(s) with it off; the chime was heard on the Mac speakers when a scan of sample_images finished in the running app | Pass |
| MT25 | FR3 | Close during scan | Exceptional | Start a big scan and close the window | Asked to stop the scan; app closes cleanly with no error | Asked 'Scan in progress'; window closed: True; background thread stopped: True | Pass |
| MT26 | - | Keyboard shortcuts | Normal | Ctrl+O, Ctrl+S, Delete, Esc | Each does the same as its menu item | Checked by hand in the running app on macOS (Ctrl shows as Cmd): Cmd+O opened the folder chooser, Cmd+S opened the save window, fn+Delete on a selected row asked to remove the image, and Esc during a scan cancelled it | Pass |
| MT27 | - | Packaged app | Normal | Build with `pyinstaller image_catalogue.spec`, open `dist/ImageCatalogue.app` from Finder, then repeat MT01 and MT24 | App starts without Python/venv, scans and plays sound | Built dist/ImageCatalogue.app (110 MB) with done.wav inside Contents/Resources/assets. Launched it on its own (no venv): still running after 8 s with no errors | Pass |

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
