"""Run through the manual test plan on the real application window.

    python tools/gui_walkthrough.py

This drives the real MainWindow and controller the way a person would
(select rows, type text, press buttons), answers the pop-up dialogs
automatically so the run can be repeated, prints a result for each test
and saves screenshots to docs/evidence/.

Some things still need a human: actually hearing the sound and judging
how smooth the window feels.
"""
import os
import shutil
import subprocess
import sys
import tempfile
import time

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, ROOT)

from PyQt6.QtCore import Qt, QTimer  # noqa: E402
from PyQt6.QtMultimedia import QSoundEffect  # noqa: E402
from PyQt6.QtTest import QTest  # noqa: E402
from PyQt6.QtWidgets import QApplication, QMessageBox  # noqa: E402

from catalogue.controller.main_controller import MainController  # noqa: E402
from catalogue.model.catalogue import ImageCatalogue  # noqa: E402
from catalogue.views.main_window import MainWindow  # noqa: E402

EVIDENCE = os.path.join(ROOT, "docs", "evidence")
SOUND = os.path.join(ROOT, "assets", "done.wav")

app = QApplication(sys.argv)
work = tempfile.mkdtemp(prefix="imgcat_gui_")
results = []


def record(test_id, actual, passed):
    label = {True: "PASS", False: "FAIL", None: "CHECK BY HAND"}[passed]
    results.append((test_id, label, actual))
    print(f"{test_id}  {label:<13}  {actual}")


def wait_for(condition, timeout=120):
    end = time.time() + timeout
    while not condition():
        app.processEvents()
        time.sleep(0.005)
        if time.time() > end:
            raise TimeoutError("gave up waiting")


def make_images(name, count):
    folder = os.path.join(work, name)
    subprocess.run([sys.executable, os.path.join(ROOT, "tools", "make_sample_images.py"),
                    folder, str(count)], check=True, stdout=subprocess.DEVNULL)
    return folder


class Session:
    """One app window, with its dialogs replaced by recorded answers."""

    def __init__(self, sound=False):
        self.window = MainWindow()
        self.controller = MainController(self.window, ImageCatalogue(),
                                         os.path.join(work, "thumbs"), SOUND)
        self.window.sound_action.setChecked(sound)
        self.dialogs = []      # (kind, title, message)
        self.answers = {"yes_no": True, "save_discard": "discard"}

        w = self.window
        w.show_error = lambda t, m: self.dialogs.append(("error", t, m))
        w.show_warning = lambda t, m: self.dialogs.append(("warning", t, m))
        w.ask_yes_no = lambda t, q: self._answer("yes_no", t, q)
        w.ask_save_discard_cancel = lambda t, q: self._answer("save_discard", t, q)
        w.ask_for_folder = lambda: self.answers.get("folder", "")
        w.ask_open_file = lambda: self.answers.get("open", "")
        w.ask_save_file = lambda: self.answers.get("save", "")
        w.resize(1150, 700)
        w.show()
        app.processEvents()

    def _answer(self, kind, title, question):
        self.dialogs.append((kind, title, question))
        return self.answers[kind]

    def scan(self, folder):
        self.controller.start_scan(folder)
        wait_for(lambda: not self.controller.is_scanning())
        app.processEvents()

    def click_save_details(self):
        before = len(self.dialogs)
        QTest.mouseClick(self.window.save_details_button, Qt.MouseButton.LeftButton)
        return self.dialogs[-1] if len(self.dialogs) > before else None

    def status(self):
        return self.window.statusBar().currentMessage()

    def count(self):
        return len(self.controller.catalogue)

    def shot(self, name):
        app.processEvents()
        self.window.grab().save(os.path.join(EVIDENCE, name + ".png"))

    def dialog_shot(self, name):
        """Rebuild the last dialog as a real QMessageBox and save a picture of it."""
        kind, title, message = self.dialogs[-1]
        icon = QMessageBox.Icon.Critical if kind == "error" else QMessageBox.Icon.Warning
        box = QMessageBox(icon, title, message, parent=self.window)
        box.show()
        app.processEvents()
        box.grab().save(os.path.join(EVIDENCE, name + ".png"))
        box.close()


def main():
    os.makedirs(EVIDENCE, exist_ok=True)
    small = make_images("sample_images", 30)
    big = make_images("big", 200)
    empty = os.path.join(work, "empty")
    os.makedirs(empty)

    s = Session()
    w, c = s.window, s.controller

    # ---- scanning ----
    s.scan(empty)
    record("MT08", f"Status '{s.status()}', {s.count()} images, no dialogs",
           s.count() == 0 and "0 image(s) added" in s.status() and not s.dialogs)

    s.scan(small)
    record("MT01", f"{s.count()} images with thumbnails. Status '{s.status()}'",
           s.count() == 30 and "30 image(s) added" in s.status())
    s.shot("MT01_after_scan")
    warnings = [d for d in s.dialogs if d[0] == "warning"]
    record("MT02", f"Warning '{warnings[-1][1]}' listed broken.jpg; the other 30 were still added",
           len(warnings) == 1 and "broken.jpg" in warnings[-1][2] and s.count() == 30)
    s.dialog_shot("MT02_skipped_files")
    names = [item.file_name for item in c.catalogue.items()]
    record("MT03", "notes.txt is not in the table and not reported as a failure",
           "notes.txt" not in names and "notes.txt" not in warnings[-1][2])

    s.scan(small)
    record("MT09", f"Second scan of the same folder: status '{s.status()}', still {s.count()} images",
           s.count() == 30 and "0 image(s) added" in s.status())

    # ---- browsing ----
    def sizes():
        return [float(c.proxy.index(r, 5).data()) for r in range(c.proxy.rowCount())]

    w.table.sortByColumn(5, Qt.SortOrder.AscendingOrder)
    ascending = sizes()
    s.shot("MT10_sorted_by_size")
    w.table.sortByColumn(5, Qt.SortOrder.DescendingOrder)
    descending = sizes()
    record("MT10", f"Ascending {ascending[0]} .. {ascending[-1]} KB, "
                   f"descending {descending[0]} .. {descending[-1]} KB (numeric order)",
           ascending == sorted(ascending) and descending == sorted(descending, reverse=True))
    w.table.sortByColumn(1, Qt.SortOrder.AscendingOrder)

    w.table.selectRow(0)
    item = c.catalogue.get(c.current_row)
    shown = w.preview._pixmap is not None and w.title_edit.text() == item.title
    w.resize(900, 600)
    app.processEvents()
    small_width = w.preview.pixmap().width()
    w.resize(1400, 900)
    app.processEvents()
    big_width = w.preview.pixmap().width()
    w.resize(1150, 700)
    app.processEvents()
    record("MT11", f"Preview and details of {item.file_name} shown; preview rescaled "
                   f"{small_width}px -> {big_width}px wide when the window was enlarged",
           shown and big_width > small_width)

    # ---- editing ----
    w.title_edit.setText("Beach day")
    w.tags_edit.setText("Sea, Holiday, sea")
    w.rating_spin.setValue(4)
    s.click_save_details()
    item = c.catalogue.get(c.current_row)
    record("MT12", f"Saved: title '{item.title}', tags {item.tags}, rating {item.rating}; "
                   f"form now shows tags '{w.tags_edit.text()}'",
           item.title == "Beach day" and item.tags == ["sea", "holiday"]
           and item.rating == 4 and w.tags_edit.text() == "sea, holiday")
    s.shot("MT12_edited_details")

    before = item.to_dict()
    w.title_edit.clear()
    error = s.click_save_details()
    record("MT13", f"Error '{error[2] if error else None}'; image unchanged",
           error is not None and "empty" in error[2] and item.to_dict() == before)
    s.dialog_shot("MT13_empty_title")

    w.title_edit.setText("Beach day")
    w.tags_edit.setText("hello world")
    error = s.click_save_details()
    record("MT14", f"Error '{error[2] if error else None}'; image unchanged",
           error is not None and "not a valid tag" in error[2] and item.to_dict() == before)
    s.dialog_shot("MT14_bad_tag")
    w.tags_edit.setText("sea, holiday")

    w.title_edit.clear()
    QTest.keyClicks(w.title_edit, "x" * 120)
    typed = len(w.title_edit.text())
    record("MT15", f"Typed 120 characters, the box kept {typed}", typed == 100)
    w.title_edit.setText("Beach day")

    w.rating_spin.setValue(9)
    high = w.rating_spin.value()
    w.rating_spin.setValue(-3)
    low = w.rating_spin.value()
    w.rating_spin.stepDown()
    below = w.rating_spin.value()
    record("MT16", f"Set 9 -> {high}; set -3 -> {low}; step down from 0 -> {below}",
           high == 5 and low == 0 and below == 0)
    w.rating_spin.setValue(4)

    # ---- searching ----
    QTest.keyClicks(w.search_box, "holiday")
    matches = c.proxy.rowCount()
    s.shot("MT17_search")
    record("MT17", f"Typed 'holiday': {matches} row shown (the image tagged in MT12)", matches == 1)
    w.search_box.clear()
    QTest.keyClicks(w.search_box, "zzzz")
    no_match = c.proxy.rowCount()
    w.search_box.clear()
    record("MT18", f"Typed 'zzzz': {no_match} rows; after clearing: {c.proxy.rowCount()} rows",
           no_match == 0 and c.proxy.rowCount() == 30)

    # ---- removing ----
    w.table.selectRow(1)
    target = c.catalogue.get(c.current_row)
    s.answers["yes_no"] = False
    w.remove_action.trigger()
    record("MT20", f"Answered No: still {s.count()} images", s.count() == 30)
    s.answers["yes_no"] = True
    w.remove_action.trigger()
    record("MT19", f"Answered Yes: {s.count()} images left; {target.file_name} still on disk: "
                   f"{os.path.exists(target.path)}",
           s.count() == 29 and not c.catalogue.contains(target.path) and os.path.exists(target.path))

    # ---- keyboard shortcuts ----
    keys = {name: getattr(w, name).shortcut().toString()
            for name in ("open_folder_action", "save_action", "remove_action", "cancel_action")}
    record("MT26", f"Shortcuts set: {keys}. Pressing them needs a focused real window",
           None)

    # ---- saving and opening ----
    path = os.path.join(work, "test.json")
    s.answers["save"] = path
    w.save_action.trigger()
    saved = os.path.exists(path) and not c.catalogue.modified
    w.close()

    s2 = Session()
    s2.answers["open"] = path
    s2.window.open_catalogue_action.trigger()
    edited = [i for i in s2.controller.catalogue.items() if i.title == "Beach day"]
    record("MT21", f"Saved test.json, opened it in a new window: {s2.count()} images; edited image has "
                   f"tags {edited[0].tags if edited else None}, rating {edited[0].rating if edited else None}",
           saved and s2.count() == 29 and bool(edited)
           and edited[0].tags == ["sea", "holiday"] and edited[0].rating == 4)
    s2.shot("MT21_reopened_catalogue")

    broken = os.path.join(work, "broken.json")
    with open(broken, "w") as f:
        f.write("random text, not a catalogue")
    s2.answers["open"] = broken
    before = len(s2.dialogs)
    s2.window.open_catalogue_action.trigger()
    error = s2.dialogs[-1] if len(s2.dialogs) > before else None
    record("MT22", f"Error '{error[1] if error else None}': "
                   f"{error[2].splitlines()[0] if error else ''}; still {s2.count()} images",
           error is not None and error[0] == "error" and s2.count() == 29)
    s2.dialog_shot("MT22_broken_catalogue")

    s2.window.table.selectRow(0)
    s2.window.rating_spin.setValue(2)
    s2.click_save_details()
    s2.answers["save_discard"] = "cancel"
    s2.window.close()
    stayed_open = s2.window.isVisible()
    s2.answers["save_discard"] = "discard"
    s2.window.close()
    asked = any(d[0] == "save_discard" for d in s2.dialogs)
    record("MT23", f"Save/Discard/Cancel asked: {asked}; Cancel kept the window open: {stayed_open}; "
                   f"Discard closed it: {not s2.window.isVisible()}",
           asked and stayed_open and not s2.window.isVisible())

    # ---- big folder: cancel, restart, responsiveness, progress, sound ----
    s3 = Session(sound=True)
    progress = []
    show_progress = s3.window.update_progress
    s3.window.update_progress = lambda done, total: (progress.append((done, total)),
                                                     show_progress(done, total))
    plays = []
    real_play = s3.controller.done_sound.play
    s3.controller.done_sound.play = lambda: (plays.append(1), real_play())

    s3.controller.start_scan(big)
    wait_for(lambda: progress and progress[-1][0] >= 60)
    s3.shot("MT05_progress_during_scan")
    s3.controller.cancel_scan()
    wait_for(lambda: not s3.controller.is_scanning())
    app.processEvents()
    after_cancel = s3.count()
    record("MT06", f"Pressed Cancel: '{s3.status()}'. Add Folder enabled again: "
                   f"{s3.window.open_folder_action.isEnabled()}",
           "cancelled" in s3.status() and after_cancel < 200
           and s3.window.open_folder_action.isEnabled())
    s3.shot("MT06_after_cancel")

    # A timer on the GUI thread: if the GUI thread were blocked, it couldn't fire
    ticks = []
    timer = QTimer()
    timer.timeout.connect(lambda: ticks.append(time.perf_counter()))
    timer.start(20)
    progress.clear()
    plays.clear()
    started = time.perf_counter()
    s3.controller.start_scan(big)
    wait_for(lambda: not s3.controller.is_scanning())
    app.processEvents()
    took = time.perf_counter() - started
    timer.stop()
    gaps = [b - a for a, b in zip(ticks, ticks[1:])]
    paths = [i.path for i in s3.controller.catalogue.items()]
    record("MT07", f"Scanned the same folder again: '{s3.status()}'; {s3.count()} images in total "
                   f"(was {after_cancel}), {len(paths) - len(set(paths))} duplicates",
           s3.count() == 200 and len(set(paths)) == 200
           and f"{200 - after_cancel} image(s) added" in s3.status())
    record("MT04", f"200-image scan took {took:.1f}s; a 20 ms timer on the GUI thread fired "
                   f"{len(ticks)} times, longest gap {max(gaps) * 1000:.0f} ms (window never froze)",
           max(gaps) < 0.25)
    record("MT05", f"Progress went {progress[0]} -> {progress[-1]} in {len(progress)} updates; "
                   f"bar hidden afterwards: {not s3.window.progress_bar.isVisible()}",
           progress[-1][0] == progress[-1][1] and not s3.window.progress_bar.isVisible())

    loaded = s3.controller.done_sound.status() == QSoundEffect.Status.Ready
    first = len(plays)
    s3.window.sound_action.setChecked(False)
    plays.clear()
    s3.scan(empty)
    record("MT24", f"done.wav loaded: {loaded}; sound played {first} time(s) with the option on, "
                   f"{len(plays)} time(s) with it off. Listen for it by hand too",
           loaded and first == 1 and len(plays) == 0)
    s3.window.close()

    # ---- closing during a scan ----
    s4 = Session()
    seen = []
    show4 = s4.window.update_progress
    s4.window.update_progress = lambda done, total: (seen.append(done), show4(done, total))
    s4.controller.start_scan(big)
    wait_for(lambda: seen and seen[-1] >= 20)
    thread = s4.controller.thread
    s4.window.close()
    thread_stopped = thread.isFinished()
    app.processEvents()
    question = [d[1] for d in s4.dialogs if d[0] == "yes_no"]
    record("MT25", f"Asked '{question[-1] if question else None}'; window closed: "
                   f"{not s4.window.isVisible()}; background thread stopped: {thread_stopped}",
           bool(question) and not s4.window.isVisible() and thread_stopped)

    with open(os.path.join(EVIDENCE, "gui_walkthrough_results.txt"), "w") as f:
        f.write(f"GUI walkthrough run on {time.strftime('%Y-%m-%d %H:%M')}\n\n")
        for test_id, label, actual in sorted(results):
            f.write(f"{test_id}  {label:<13}  {actual}\n")
    failed = [r for r in results if r[1] == "FAIL"]
    print(f"\n{len(results)} checks, {len(failed)} failed. Screenshots in {EVIDENCE}")
    shutil.rmtree(work, ignore_errors=True)
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
