"""Tests for the background worker and the shared counter (thread safety).

These call worker.run() directly in the test thread, so we can check the
signals it emits without starting a real QThread.
"""
import threading

import pytest
from PIL import Image
from PyQt6.QtCore import QCoreApplication

from catalogue.workers.scan_worker import ScanStats, ScanWorker


@pytest.fixture(scope="module", autouse=True)
def qt_app():
    app = QCoreApplication.instance() or QCoreApplication([])
    yield app


@pytest.fixture
def folder(tmp_path):
    for i in range(12):
        Image.new("RGB", (300, 200), (i * 20, 0, 0)).save(tmp_path / f"img{i}.png")
    (tmp_path / "broken.jpg").write_text("nope")
    return tmp_path


def run_worker(worker):
    """Run the worker and collect everything it emits."""
    results = {"items": [], "progress": [], "finished": None, "failed": None}
    worker.item_ready.connect(results["items"].append)
    worker.progress.connect(lambda done, total: results["progress"].append((done, total)))
    worker.scan_finished.connect(lambda *args: results.__setitem__("finished", args))
    worker.scan_failed.connect(lambda msg: results.__setitem__("failed", msg))
    worker.run()
    return results


def test_stats_counter_is_correct_with_many_threads():
    """8 threads each record 5000 results. With the lock nothing is lost."""
    stats = ScanStats()

    def work():
        for i in range(5000):
            if i % 10 == 0:
                stats.record_failure("x", "bad")
            else:
                stats.record_success()

    threads = [threading.Thread(target=work) for _ in range(8)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    processed, failures = stats.snapshot()
    assert processed == 8 * 5000
    assert len(failures) == 8 * 500


def test_worker_processes_all_images_and_reports_broken_one(folder, tmp_path):
    worker = ScanWorker(str(folder), str(tmp_path / "thumbs"), max_threads=4)
    results = run_worker(worker)

    added, failures, cancelled = results["finished"]
    assert added == 12
    assert len(results["items"]) == 12
    assert len(failures) == 1 and failures[0][0].endswith("broken.jpg")
    assert cancelled is False
    assert results["progress"][0] == (0, 13)
    assert results["progress"][-1] == (13, 13)


def test_worker_with_missing_folder_emits_scan_failed(tmp_path):
    worker = ScanWorker(str(tmp_path / "nope"), str(tmp_path / "thumbs"))
    results = run_worker(worker)
    assert results["failed"] is not None
    assert results["finished"] is None


def test_cancel_before_start_adds_nothing(folder, tmp_path):
    worker = ScanWorker(str(folder), str(tmp_path / "thumbs"))
    worker.cancel()
    results = run_worker(worker)
    added, _failures, cancelled = results["finished"]
    assert cancelled is True
    assert added == 0


def test_empty_folder_finishes_with_nothing(tmp_path):
    (tmp_path / "empty").mkdir()
    worker = ScanWorker(str(tmp_path / "empty"), str(tmp_path / "thumbs"))
    results = run_worker(worker)
    assert results["finished"] == (0, [], False)
