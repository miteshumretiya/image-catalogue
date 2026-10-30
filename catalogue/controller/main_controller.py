"""The controller: the "glue" between the window, the data and the worker.

- The window emits signals like open_folder_requested.
- The controller reacts: asks the model to do things, starts background
  work, and tells the window what to show.
"""
from PyQt6.QtCore import QThread, QUrl
from PyQt6.QtMultimedia import QSoundEffect

from catalogue.model.catalogue import CatalogueError
from catalogue.model.image_item import ValidationError
from catalogue.views.image_table_model import ImageTableModel, ImageFilterProxy
from catalogue.workers.scan_worker import ScanWorker


class MainController:
    def __init__(self, window, catalogue, thumb_dir, sound_path):
        self.window = window
        self.catalogue = catalogue
        self.thumb_dir = thumb_dir
        self.catalogue_path = None   # where we last saved/loaded
        self.current_row = -1
        self.added_count = 0         # images really added by the current scan

        self.thread = None
        self.worker = None

        self.table_model = ImageTableModel(catalogue)
        self.proxy = ImageFilterProxy(catalogue)
        self.proxy.setSourceModel(self.table_model)
        window.set_table_model(self.proxy)

        # QtMultimedia: a short chime when a long scan finishes, so the user
        # can do something else and still know when it's done
        self.sound_enabled = True
        self.done_sound = QSoundEffect()
        self.done_sound.setSource(QUrl.fromLocalFile(sound_path))
        self.done_sound.setVolume(0.6)

        self._connect_signals()
        self._update_count()
        window.show_status("Ready. Use File > Add Folder to add some images.")

    def _connect_signals(self):
        w = self.window
        w.open_folder_requested.connect(self.add_folder)
        w.open_catalogue_requested.connect(self.open_catalogue)
        w.save_catalogue_requested.connect(self.save_catalogue)
        w.remove_requested.connect(self.remove_selected)
        w.cancel_requested.connect(self.cancel_scan)
        w.search_changed.connect(self.proxy.set_search_text)
        w.selection_changed.connect(self.on_selection_changed)
        w.details_submitted.connect(self.save_details)
        w.sound_toggled.connect(self.set_sound_enabled)
        w.close_check = self.can_close

    # ---- scanning a folder (background work) ----

    def is_scanning(self):
        return self.thread is not None

    def add_folder(self):
        if self.is_scanning():
            return
        folder = self.window.ask_for_folder()
        if folder:
            self.start_scan(folder)

    def start_scan(self, folder):
        self.added_count = 0
        self.thread = QThread()
        self.worker = ScanWorker(folder, self.thumb_dir)
        self.worker.moveToThread(self.thread)

        # Because the worker lives in another thread, Qt automatically uses
        # queued connections here: each signal is delivered to our slots on
        # the GUI thread, so it's safe to update widgets in them.
        self.thread.started.connect(self.worker.run)
        self.worker.progress.connect(self.window.update_progress)
        self.worker.item_ready.connect(self.on_item_ready)
        self.worker.scan_finished.connect(self.on_scan_finished)
        self.worker.scan_failed.connect(self.on_scan_failed)

        self.worker.scan_finished.connect(self.thread.quit)
        self.worker.scan_failed.connect(self.thread.quit)
        self.thread.finished.connect(self._on_thread_finished)

        self.window.set_busy(True)
        self.window.show_status(f"Scanning {folder} ...")
        self.thread.start()

    def cancel_scan(self):
        if self.worker is not None:
            self.worker.cancel()
            self.window.set_cancelling()

    def on_item_ready(self, item):
        if self.table_model.add_item(item):
            self.added_count += 1
            self._update_count()

    def on_scan_finished(self, _images_read, failures, cancelled):
        # The worker counts every image it read, including ones already in
        # the catalogue, so use our own count of what was really added.
        added = self.added_count
        self.window.set_busy(False)
        if cancelled:
            message = f"Scan cancelled. {added} image(s) were added before stopping."
        else:
            message = f"Scan complete. {added} image(s) added."
        if failures:
            message += f" {len(failures)} file(s) could not be read."
        self.window.show_status(message)
        self._play_done_sound()

        if failures:
            lines = [f"- {path}\n    {reason}" for path, reason in failures[:10]]
            if len(failures) > 10:
                lines.append(f"...and {len(failures) - 10} more.")
            self.window.show_warning("Some files were skipped",
                                     "These files could not be opened as images:\n\n" + "\n".join(lines))

    def on_scan_failed(self, message):
        self.window.set_busy(False)
        self.window.show_status("Scan failed.")
        self.window.show_error("Scan failed", message)

    def _on_thread_finished(self):
        self.worker.deleteLater()
        self.thread.deleteLater()
        self.worker = None
        self.thread = None

    def set_sound_enabled(self, enabled):
        self.sound_enabled = enabled

    def _play_done_sound(self):
        if self.sound_enabled:
            self.done_sound.play()

    # ---- viewing and editing ----

    def on_selection_changed(self, row):
        self.current_row = row
        if row < 0:
            self.window.clear_details()
        else:
            self.window.show_details(self.catalogue.get(row))

    def save_details(self, title, tags_text, rating):
        row = self.current_row
        if row < 0:
            return
        try:
            item = self.catalogue.update_details(row, title, tags_text, rating)
        except ValidationError as e:
            self.window.show_error("Invalid details", str(e))
            return
        self.table_model.refresh_row(row)
        self.window.show_details(item)   # show the cleaned-up values, e.g. tags in lower case
        self.window.show_status("Details saved.", 3000)

    def remove_selected(self):
        row = self.current_row
        if row < 0:
            return
        item = self.catalogue.get(row)
        if not self.window.ask_yes_no("Remove image",
                                      f"Remove '{item.file_name}' from the catalogue?\n"
                                      "(The file on disk is not deleted.)"):
            return
        self.table_model.remove_row(row)
        self._update_count()
        self.window.show_status(f"Removed {item.file_name}.", 3000)

    # ---- saving and loading ----

    def save_catalogue(self):
        path = self.catalogue_path or self.window.ask_save_file()
        if not path:
            return False
        try:
            self.catalogue.save(path)
        except CatalogueError as e:
            self.window.show_error("Save failed", str(e))
            return False
        self.catalogue_path = path
        self.window.show_status(f"Saved {len(self.catalogue)} image(s) to {path}", 5000)
        return True

    def open_catalogue(self):
        if self.is_scanning() or not self._ok_to_discard_changes():
            return
        path = self.window.ask_open_file()
        if not path:
            return
        try:
            items = self.catalogue.read_file(path)
        except CatalogueError as e:
            self.window.show_error("Could not open catalogue", str(e))
            return
        self.table_model.set_items(items)
        self.catalogue_path = path
        self.window.clear_details()
        self._update_count()
        self.window.show_status(f"Opened {path}", 5000)

    def can_close(self):
        if self.is_scanning():
            if not self.window.ask_yes_no("Scan in progress", "A scan is still running. Stop it and quit?"):
                return False
            self.worker.cancel()
            self.thread.quit()
            self.thread.wait()
        return self._ok_to_discard_changes()

    def _ok_to_discard_changes(self):
        if not self.catalogue.modified or len(self.catalogue) == 0:
            return True
        answer = self.window.ask_save_discard_cancel(
            "Unsaved changes", "You have unsaved changes. Do you want to save them first?")
        if answer == "save":
            return self.save_catalogue()
        return answer == "discard"

    def _update_count(self):
        self.window.set_image_count(len(self.catalogue))
