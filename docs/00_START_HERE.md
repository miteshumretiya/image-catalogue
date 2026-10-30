# Start Here: Understanding the Project Step by Step

Read this first. It explains how the whole project works in the order you should learn it. Don't move on until each step makes sense. You'll need to explain all of this in your presentation.

---

## Step 1: Run it and play with it (15 min)

```bash
pip install -r requirements-dev.txt
```
```bash
python tools/make_sample_images.py sample_images 30
```
```bash
python main.py
```

Click **Add Folder**, choose `sample_images`, and watch the progress bar. Click an image, give it a title and tags, and save. Search for a tag. Save the catalogue, close the app, reopen it and open the catalogue again. Try typing a bad tag like `hello world`.

## Step 2: Follow one click through the code (the big idea, MVC)

Let's follow what happens when you press **Save Details**:

1. **View** (`views/main_window.py`): the button's `clicked` signal runs `_on_save_details_clicked()`. That just *emits* `details_submitted(title, tags, rating)`. The window doesn't decide anything.
2. **Controller** (`controller/main_controller.py`): `save_details()` is connected to that signal. It calls `self.catalogue.update_details(...)`.
3. **Model** (`model/catalogue.py`): `update_details()` calls the validation functions in `image_item.py`. If something is wrong it raises `ValidationError`, and nothing is changed.
4. Back in the **controller**: if there was an error, it calls `window.show_error(...)`. Otherwise it tells the table to refresh that row and the form to show the cleaned-up values.

**Why bother?** The validation rules can be tested without a GUI, and the window code stays simple. This is "separation of concerns".

## Step 3: The model (start here in the code)

Read in this order:
1. `model/image_item.py`: a dataclass for one image, plus `validate_title`, `parse_tags` and `validate_rating`.
2. `model/catalogue.py`: a list of items plus a set of paths (for quick duplicate checks), with search, save and load. Note `read_file()` *returns* items instead of replacing the current ones, so a broken file can't wipe your data.
3. `model/processing.py`: `find_images()` walks the folder; `process_image()` opens a picture with Pillow, reads its size, and saves a 128 px thumbnail.

Then run `python -m pytest tests/test_image_item.py -v` and read the tests next to the code.

## Step 4: The view

`views/main_window.py` builds the window:
- `_create_actions()` creates the menu and toolbar items (`QAction`). One action can appear in both the menu and the toolbar.
- `_create_central_area()` sets up a `QSplitter` with the search box and table on the left, and the preview and form on the right.
- `_create_status_bar()` adds the progress bar and Cancel button.
- At the top are the **custom signals**. The methods at the bottom (`show_details`, `set_busy`, `show_error`, ...) are what the controller calls.

`views/image_table_model.py` is how Qt's `QTableView` gets its data. `rowCount`, `columnCount` and `data` are called by Qt whenever it repaints. `beginInsertRows`/`endInsertRows` tell the view "a row was added". The proxy handles searching and sorting.

## Step 5: Threads (the most important part for marks)

**The problem.** Opening and shrinking 300 big photos takes several seconds. If that runs in the GUI thread, the window can't redraw or respond to clicks, so it freezes.

**The solution** (`workers/scan_worker.py` and `start_scan()` in the controller):

```
GUI thread                          QThread                      pool threads (x4)
----------                          -------                      -----------------
start_scan()
  worker.moveToThread(thread)
  thread.start()  ----------------> worker.run()
                                      find_images()
                                      pool.submit(...) ---------> process_image(a.jpg)
                                                                  process_image(b.jpg)
                                      as_completed loop  <------- results
  on_item_ready(item) <---signal----  item_ready.emit(item)
  update_progress()   <---signal----  progress.emit(done, total)
  on_scan_finished()  <---signal----  scan_finished.emit(...)
  play sound
```

Key points to be able to explain:
- **Signals across threads are queued.** Emitting `item_ready` in the worker thread doesn't run the slot there. Qt puts it in the GUI thread's event queue. That's why it's safe to update the table in `on_item_ready`.
- **ScanStats uses a Lock.** Four pool threads update the same counter. Run `python tools/race_demo.py` to see what happens without a lock (you'll get far fewer than 40,000).
- **Cancel uses `threading.Event`** and is called directly, not via a signal. The worker thread is busy inside `run()`, so it wouldn't process a queued signal until it had finished.
- **One bad file doesn't stop the scan.** `_process_one` catches the error, records it and carries on.

## Step 6: Multimedia

In the controller's `__init__`: `QSoundEffect` loads `assets/done.wav` and `_play_done_sound()` plays it when a scan finishes. Its purpose: you can switch to another window while a big folder scans, and the sound tells you it's done.

## Step 7: Performance investigation

```bash
python benchmark/benchmark.py 40
```

Read `docs/03_performance_investigation.md`. **Put your own numbers in.** The key ideas to explain:
- Threads vs processes, and why threads still helped despite the GIL (Pillow's C code releases it).
- CPU-bound vs I/O-bound (Table 3).
- Overhead: 1 worker is no faster, and 8 workers on 4 cores gets slower.
- Amdahl's Law: the sequential part limits the maximum speed-up.
- `pool.map` is Python's version of PLINQ's `AsParallel().Select()`.

## Step 8: Testing

```bash
python -m pytest -v
```

Then work through the manual tests in `docs/02_test_plan.md`, filling in the "Actual" and "Pass/Fail" columns and taking screenshots.

## Step 9: Git

Follow `docs/04_git_workflow_guide.md` **as you build**, not at the end. Your markers will look at the commit dates and history.

## Step 10: Packaging

```bash
pyinstaller image_catalogue.spec
```

Run `dist/ImageCatalogue/ImageCatalogue.exe`. Ideally copy the `dist/ImageCatalogue` folder to another computer (or a friend's) and screenshot it working there.

---

## Checklist against the brief

| Task | Where it's covered |
|------|--------------------|
| 1 Design | `docs/01_design_specification.md` |
| 2 PyQt GUI | `views/main_window.py` (QMainWindow, menus, toolbar, status bar, table, splitter, form, dialogs) |
| 3 Signals, validation, errors | custom signals in `MainWindow` and `ScanWorker`; `ValidationError`, `CatalogueError` |
| 4 MVC | `model/`, `views/`, `controller/`, explained in the design spec and report 15.2 |
| 5 Multimedia | `QSoundEffect` in `main_controller.py` |
| 6 Concurrency | `ScanWorker` + `QThread` + `ThreadPoolExecutor`, progress, cancel, completion message |
| 7 Synchronisation | `ScanStats` lock, `threading.Event`, queued signals; `tools/race_demo.py` |
| 8 Performance | `benchmark/benchmark.py`, `docs/03_performance_investigation.md` |
| 9-12 Testing and debugging | `docs/02_test_plan.md`, `tests/` |
| 13 Git | `docs/04_git_workflow_guide.md` (you do this) |
| 14 Distribution | `image_catalogue.spec`, README build section |
| 15 Documentation and presentation | `docs/05_technical_report.md`, `docs/06_presentation_outline.md` |
