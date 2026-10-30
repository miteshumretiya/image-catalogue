"""Performance investigation: is thumbnail generation faster in parallel?

    python benchmark/benchmark.py            (default 40 images)
    python benchmark/benchmark.py 80

It runs the same job as the app (open image -> read details -> make
thumbnail) in three ways and times each one with time.perf_counter():

  1. Sequential      - a normal for-loop, one image at a time
  2. Threads         - ThreadPoolExecutor (what the app uses)
  3. Processes       - ProcessPoolExecutor (true parallelism, no GIL)

The job is written as a "parallel query", the Python version of PLINQ:

  C# PLINQ:  files.AsParallel().Where(IsImage).Select(Process).ToList()
  Python:    list(pool.map(process, filter(is_image_file, files)))

At the end it estimates the sequential fraction and applies Amdahl's Law.
"""
import os
import shutil
import statistics
import sys
import tempfile
import time
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from PIL import Image  # noqa: E402

from catalogue.model.processing import is_image_file, process_image  # noqa: E402

REPEATS = 3
IMAGE_SIZE = (2000, 1500)
THUMB_DIR = os.path.join(tempfile.gettempdir(), "imgcat_bench_thumbs")


def make_test_images(folder, count):
    """Random-noise JPEGs: they don't compress well, so decoding takes real work."""
    for i in range(count):
        img = Image.frombytes("RGB", IMAGE_SIZE, os.urandom(IMAGE_SIZE[0] * IMAGE_SIZE[1] * 3))
        img.save(os.path.join(folder, f"test_{i:03d}.jpg"), quality=90)
    # a few non-image files so the "Where" part of the query has something to filter
    for i in range(5):
        with open(os.path.join(folder, f"readme_{i}.txt"), "w") as f:
            f.write("not an image")


def process_image_task(path):
    # module-level function (not a lambda) so ProcessPoolExecutor can pickle it
    return process_image(path, THUMB_DIR)


def query_sequential(files, thumb_dir):
    # files.Where(IsImage).Select(Process).ToList()
    return [process_image(f, thumb_dir) for f in files if is_image_file(f)]


def query_parallel(files, thumb_dir, executor_class, workers):
    # files.AsParallel().WithDegreeOfParallelism(workers).Where(IsImage).Select(Process).ToList()
    images = [f for f in files if is_image_file(f)]
    with executor_class(max_workers=workers) as pool:
        return list(pool.map(process_image, images, [thumb_dir] * len(images)))


def brightness_pure_python(path, _thumb_dir=None):
    """CPU-bound work written in pure Python, so it holds the GIL the whole time."""
    with Image.open(path) as img:
        img.draft("L", (500, 375))    # decode at reduced size so the Python loop dominates
        pixels = img.convert("L").resize((500, 375)).tobytes()
    total = 0
    for _ in range(3):
        for value in pixels:
            total += value * value % 7
    return total


def wait_like_io(path, _thumb_dir=None):
    """I/O-bound work: mostly waiting (like a slow network drive), not computing."""
    time.sleep(0.05)
    return os.path.getsize(path)


def run_task(task, files, executor_class=None, workers=1):
    images = [f for f in files if is_image_file(f)]
    if executor_class is None:
        return [task(f) for f in images]
    with executor_class(max_workers=workers) as pool:
        return list(pool.map(task, images))


def time_it(func, *args):
    """Run func REPEATS times and return the median time in seconds."""
    times = []
    for _ in range(REPEATS):
        start = time.perf_counter()
        result = func(*args)
        times.append(time.perf_counter() - start)
    return statistics.median(times), result


def main():
    count = int(sys.argv[1]) if len(sys.argv) > 1 else 40
    cpu_count = os.cpu_count() or 1
    work_dir = tempfile.mkdtemp(prefix="imgcat_bench_")
    image_dir = os.path.join(work_dir, "images")
    thumb_dir = os.path.join(work_dir, "thumbs")
    os.makedirs(image_dir)

    try:
        print(f"Creating {count} test images of {IMAGE_SIZE[0]}x{IMAGE_SIZE[1]} ...")
        make_test_images(image_dir, count)
        files = sorted(os.path.join(image_dir, name) for name in os.listdir(image_dir))
        print(f"CPU cores reported: {cpu_count}.  Each result is the median of {REPEATS} runs.\n")

        # ---- 1. compare the three approaches with 4 workers ----
        rows = []
        seq_time, seq_result = time_it(query_sequential, files, thumb_dir)
        rows.append(("Sequential (for-loop)", 1, seq_time))

        for name, executor in [("Threads (ThreadPoolExecutor)", ThreadPoolExecutor),
                               ("Processes (ProcessPoolExecutor)", ProcessPoolExecutor)]:
            t, result = time_it(query_parallel, files, thumb_dir, executor, 4)
            assert len(result) == len(seq_result), "parallel version gave a different answer!"
            rows.append((name, 4, t))

        print("Table 1 - Approaches compared (4 workers)")
        print(f"| {'Approach':<32} | Workers | Time (s) | Speed-up |")
        print(f"|{'-' * 34}|---------|----------|----------|")
        for name, workers, t in rows:
            print(f"| {name:<32} | {workers:^7} | {t:8.2f} | {seq_time / t:7.2f}x |")

        # ---- 2. scalability: how does it change with more workers? ----
        print("\nTable 2 - Scalability (speed-up compared with sequential)")
        print("| Workers | Threads time (s) | Threads speed-up | Processes time (s) | Processes speed-up |")
        print("|---------|------------------|------------------|--------------------|--------------------|")
        best_process_speedup = 0
        for workers in [1, 2, 4, 8]:
            t_thr, _ = time_it(query_parallel, files, thumb_dir, ThreadPoolExecutor, workers)
            t_proc, _ = time_it(query_parallel, files, thumb_dir, ProcessPoolExecutor, workers)
            if workers <= cpu_count:
                best_process_speedup = max(best_process_speedup, seq_time / t_proc)
            print(f"| {workers:^7} | {t_thr:16.2f} | {seq_time / t_thr:15.2f}x "
                  f"| {t_proc:18.2f} | {seq_time / t_proc:17.2f}x |")

        # ---- 3. CPU-bound vs I/O-bound ----
        print("\nTable 3 - Type of work (4 workers)")
        print("| Kind of work                         | Sequential (s) | Threads (s) | Processes (s) |")
        print("|--------------------------------------|----------------|-------------|---------------|")
        kinds = [("Pillow thumbnails (C, GIL released)", process_image_task),
                 ("Pure-Python pixel loop (holds GIL)", brightness_pure_python),
                 ("Waiting on I/O (sleep 50 ms)", wait_like_io)]
        for label, task in kinds:
            t_seq, _ = time_it(run_task, task, files)
            t_thr, _ = time_it(run_task, task, files, ThreadPoolExecutor, 4)
            t_proc, _ = time_it(run_task, task, files, ProcessPoolExecutor, 4)
            print(f"| {label:<36} | {t_seq:14.2f} | {t_thr:11.2f} | {t_proc:13.2f} |")

        # ---- 4. Amdahl's Law ----
        # Measure the part that can't be parallelised: listing + filtering the files
        # and starting the pool. Here we time the listing/filter step directly.
        start = time.perf_counter()
        for _ in range(100):
            sorted(f for f in os.listdir(image_dir) if is_image_file(f))
        listing_time = (time.perf_counter() - start) / 100
        start = time.perf_counter()
        with ProcessPoolExecutor(max_workers=4) as pool:
            list(pool.map(abs, [1]))
        pool_startup = time.perf_counter() - start

        serial = listing_time + pool_startup
        serial_fraction = min(serial / seq_time, 1.0)
        p = 1 - serial_fraction

        print("\nAmdahl's Law:  speed-up(N) = 1 / ((1 - P) + P / N)")
        print(f"  Sequential part (file listing + pool start-up) = {serial:.3f}s "
              f"of {seq_time:.2f}s  ->  serial fraction = {serial_fraction:.3f}, P = {p:.3f}")
        for n in [2, 4, 8, 1000]:
            print(f"  N = {n:<5} predicted max speed-up = {1 / ((1 - p) + p / n):.2f}x")
        print(f"  Best measured process speed-up = {best_process_speedup:.2f}x")
    finally:
        shutil.rmtree(work_dir, ignore_errors=True)
        shutil.rmtree(THUMB_DIR, ignore_errors=True)


if __name__ == "__main__":
    main()
