"""Shows why ScanStats needs a lock.

    python tools/race_demo.py

Four threads each add 1 to a shared counter 10,000 times, so the answer
should be 40,000. The unsafe version reads the value, pauses for a moment
(time.sleep(0) lets another thread run, like a real thread switch would),
then writes it back. Other threads' updates in between get overwritten.
"""
import threading
import time

THREADS = 4
ADDS_PER_THREAD = 10_000


class UnsafeCounter:
    def __init__(self):
        self.value = 0

    def add(self):
        current = self.value      # 1. read
        time.sleep(0)             #    another thread may run here
        self.value = current + 1  # 2. write (may overwrite someone else's update)


class SafeCounter(UnsafeCounter):
    def __init__(self):
        super().__init__()
        self._lock = threading.Lock()

    def add(self):
        with self._lock:          # only one thread at a time can do read + write
            super().add()


def run(counter):
    def work():
        for _ in range(ADDS_PER_THREAD):
            counter.add()

    threads = [threading.Thread(target=work) for _ in range(THREADS)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    return counter.value


if __name__ == "__main__":
    expected = THREADS * ADDS_PER_THREAD
    print(f"Expected:              {expected}")
    print(f"Without a lock got:    {run(UnsafeCounter())}")
    print(f"With a lock got:       {run(SafeCounter())}")
