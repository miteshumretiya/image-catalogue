# Task 8: Performance and Parallelism Investigation

## What I measured

The component is the slowest part of the app, **generating thumbnails** (`process_image()` in `catalogue/model/processing.py`). For each file it opens the image, decodes it, reads its size and format, shrinks it to 128 px and saves a PNG.

Setup: 40 random-noise JPEGs of 2000 x 1500 (noise doesn't compress, so decoding is real work), plus 5 `.txt` files to filter out. Machine: MacBook Pro, Intel Core i9-9980HK (8 cores / 16 threads, 2.4 GHz), 32 GB RAM, macOS 26.6, Python 3.14.7. Run with `python benchmark/benchmark.py 40` on 30 October 2026.

Timing: `time.perf_counter()`, a high-resolution clock meant for measuring short intervals. Each approach was run 3 times and I report the **median**, so one slow run (e.g. caused by antivirus or disk cache) doesn't skew the result.

## The parallel query (PLINQ in Python)

In the module we covered PLINQ, where adding `.AsParallel()` to a LINQ query makes .NET split the work across cores:

```csharp
var items = files.AsParallel().Where(IsImage).Select(Process).ToList();
```

Python doesn't have PLINQ, but `concurrent.futures` gives the same idea. `executor.map()` is a parallel `Select`, and the `Where` is a filter before it:

```python
images = [f for f in files if is_image_file(f)]              # Where
with ProcessPoolExecutor(max_workers=4) as pool:              # AsParallel().WithDegreeOfParallelism(4)
    items = list(pool.map(process_image, images, ...))        # Select(...).ToList()
```

Like PLINQ, `map` keeps the results in the same order as the input, and the code says *what* to compute rather than *how* to split it up. I checked that the parallel versions return the same number of results as the sequential one.

## Results

**Table 1: Approaches compared (4 workers)**

| Approach | Workers | Time (s) | Speed-up |
|----------|---------|----------|----------|
| Sequential (for-loop) | 1 | 2.09 | 1.00x |
| Threads (ThreadPoolExecutor) | 4 | 0.64 | 3.25x |
| Processes (ProcessPoolExecutor) | 4 | 0.78 | 2.69x |

**Table 2: Scalability**

| Workers | Threads (s) | Threads speed-up | Processes (s) | Processes speed-up |
|---------|-------------|------------------|---------------|--------------------|
| 1 | 2.12 | 0.99x | 2.39 | 0.87x |
| 2 | 1.22 | 1.71x | 1.35 | 1.55x |
| 4 | 0.68 | 3.05x | 0.80 | 2.60x |
| 8 | 0.46 | 4.50x | 0.66 | 3.17x |

**Table 3: CPU-bound vs I/O-bound (4 workers)**

| Kind of work | Sequential (s) | Threads (s) | Processes (s) |
|--------------|----------------|-------------|---------------|
| Pillow thumbnails (C code, GIL released) | 2.42 | 0.70 | 0.83 |
| Pure-Python pixel loop (holds the GIL) | 2.29 | 1.42 | 0.85 |
| Waiting on I/O (sleep 50 ms per file) | 2.10 | 0.53 | 0.74 |

## Discussion

**Why did it get faster?** Each image is independent of the others, so the job splits naturally across workers. With 4 workers, roughly 4 images are processed at once, giving about 3.25x with threads.

**Threads beat processes for this job on my Mac.** With 4 workers, threads took 0.64 s and processes 0.78 s. Both use the CPU in parallel here (see below), but processes also have to start new Python interpreters and pickle every result to send it back. That extra cost is pure overhead.

**Why do threads work here when Python has the GIL?** This surprised me at first. The GIL means only one thread runs *Python* code at a time. However, Pillow does decoding and resizing in C, and it releases the GIL while doing so. That means the threads really do run in parallel during the heavy part. Table 3 shows this. When I replaced the work with a loop written in pure Python, threads only managed 1.6x (2.29 s to 1.42 s) while processes managed 2.7x (0.85 s). Threads aren't stuck at 1.0x because part of that task (opening and decoding the file) is still C code.

**CPU-bound vs I/O-bound.**
- *I/O-bound* work (waiting on a disk or network) is mostly waiting, so threads are ideal. They are cheap and the GIL is released while waiting. Table 3 row 3 shows 4x with threads (2.10 s to 0.53 s), better than processes (0.74 s).
- *CPU-bound* work in pure Python needs **processes**, because each process has its own interpreter and its own GIL.
- *CPU-bound* work in a C library that releases the GIL (like Pillow) works fine with threads.

**Overhead.** Parallelism isn't free:
- With 1 worker, the pool versions were no faster: threads 0.99x, and processes were *slower* than the plain loop at 0.87x. That is the cost of starting the pool and, for processes, starting a new Python interpreter and **pickling** every argument and result to send between processes.
- The speed-up is never as big as the number of workers. 8 workers gave 4.50x with threads but only 3.17x with processes. All the workers write thumbnails to the same disk, the laptop lowers its clock speed when all cores are busy, and the 8 "extra" cores are hyper-threads sharing the same 8 physical cores.

**Why I used threads in the app (not processes).** For this workload threads were nearly as fast as processes. They are also much simpler with Qt: results can be passed to the GUI via signals without pickling, there is no start-up cost each scan, and PyInstaller packaging of multiprocessing needs extra care on Windows (`freeze_support`).

## Amdahl's Law

Amdahl's Law gives the maximum speed-up when only part of a program can run in parallel:

```
Speed-up(N) = 1 / ((1 - P) + P / N)
```

where **P** is the fraction that can be parallelised and **N** is the number of workers.

In my benchmark the sequential part is listing and filtering the files and starting a process pool. I measured it at **0.161 s of 2.09 s, so 1 - P = 0.077 and P = 0.923**.

- N = 4: 1 / (0.077 + 0.923/4) = 1 / 0.308 = **3.25x** predicted. I measured **3.25x with threads** and 2.60x with processes.
- N = 8: 1 / (0.077 + 0.923/8) = **5.20x** predicted. I measured 4.50x with threads.
- N = infinity: 1 / 0.077 = about **12.9x** is the absolute ceiling, however many cores I had.

The measured speed-up is a bit lower than predicted at 8 workers because Amdahl's Law assumes perfect parallel work with no overhead. In reality there is pool management, pickling and several workers writing to one disk.

**Worked example of the limit.** In the real app the sequential part is bigger. The GUI thread has to receive every result and insert a table row, which can't be done in parallel. Suppose that's 10% of the total time (P = 0.9). Then:
- 4 cores: 1 / (0.1 + 0.9/4) = **3.08x**
- 16 cores: 1 / (0.1 + 0.9/16) = **6.4x**
- infinite cores: 1 / 0.1 = **10x maximum**

So even with unlimited cores, 10% of sequential work caps the speed-up at 10x. To go faster, you have to shrink the sequential part (e.g. add rows to the table in batches) rather than add more cores.

## Scalability conclusion

The job scales well from 1 to 4 workers (3.05x with threads) and keeps improving at 8 (4.50x), but each extra worker adds less. That is what Amdahl's Law predicts: the 7.7% sequential part, plus the shared disk and pickling overhead, stops the speed-up from growing in step with the number of cores.
