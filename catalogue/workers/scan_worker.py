"""Background scanning: find images in a folder and make thumbnails.

How the threads fit together:

  GUI thread  --starts-->  QThread running ScanWorker.run()
                                |
                                +--> ThreadPoolExecutor (several threads)
                                       each one calls process_image()

The pool threads never touch the GUI or the catalogue. Finished ImageItems
are handed back to the GUI thread through Qt signals (queued connections),
which is the thread-safe way to pass data to widgets.
"""
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed

from PIL import Image
from PyQt6.QtCore import QObject, pyqtSignal, pyqtSlot

from catalogue.model.processing import find_images, process_image


class ScanStats:
    """Counters that all the pool threads update at the same time.

    This is shared state, so every read and write goes through a lock.
    Without the lock, "self.processed += 1" from two threads at once can
    lose an update, because += is really read, add, write.
    """

    def __init__(self):
        self._lock = threading.Lock()
        self._processed = 0
        self._failures = []     # list of (path, reason)

    def record_success(self):
        with self._lock:
            self._processed += 1

    def record_failure(self, path, reason):
        with self._lock:
            self._processed += 1
            self._failures.append((path, reason))

    def snapshot(self):
        """Return a consistent copy of (processed, failures)."""
        with self._lock:
            return self._processed, list(self._failures)


class ScanWorker(QObject):
    # Custom signals. These are how the worker talks to the GUI.
    progress = pyqtSignal(int, int)             # done, total
    item_ready = pyqtSignal(object)             # an ImageItem
    scan_finished = pyqtSignal(int, list, bool)  # added, failures, was_cancelled
    scan_failed = pyqtSignal(str)               # a problem that stopped the whole scan

    def __init__(self, folder, thumb_dir, max_threads=4):
        super().__init__()
        self.folder = folder
        self.thumb_dir = thumb_dir
        self.max_threads = max_threads
        # threading.Event is thread-safe, so the GUI can set it while we run
        self._cancel_event = threading.Event()

    def cancel(self):
        # Called directly from the GUI thread, not through a signal.
        # A queued signal would wait until run() finished, which is too late.
        self._cancel_event.set()

    def is_cancelled(self):
        return self._cancel_event.is_set()

    @pyqtSlot()
    def run(self):
        try:
            paths = find_images(self.folder)
        except OSError as e:
            self.scan_failed.emit(str(e))
            return

        total = len(paths)
        self.progress.emit(0, total)
        stats = ScanStats()
        added = 0

        with ThreadPoolExecutor(max_workers=self.max_threads) as pool:
            futures = [pool.submit(self._process_one, path, stats) for path in paths]

            for future in as_completed(futures):
                if self.is_cancelled():
                    # Stop anything that hasn't started yet
                    for f in futures:
                        f.cancel()
                    break

                item = future.result()
                if item is not None:
                    self.item_ready.emit(item)
                    added += 1

                done, _ = stats.snapshot()
                self.progress.emit(done, total)

        _, failures = stats.snapshot()
        self.scan_finished.emit(added, failures, self.is_cancelled())

    def _process_one(self, path, stats):
        """Runs inside a pool thread. One bad file must not stop the scan."""
        if self.is_cancelled():
            return None
        try:
            item = process_image(path, self.thumb_dir)
        except (OSError, ValueError, Image.DecompressionBombError) as e:
            stats.record_failure(path, str(e))
            return None
        stats.record_success()
        return item
