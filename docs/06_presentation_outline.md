# Presentation Outline (about 10 minutes)

Keep slides light (a picture or diagram and a few words) and do most of the talking around a live demo.

| # | Slide | What to show / say |
|---|-------|--------------------|
| 1 | Title | Image Catalogue: your name, module, one-line purpose |
| 2 | The problem | Folders full of `IMG_4821.jpg`; no titles, tags or ratings; slow to find things |
| 3 | Requirements | The 10 functional requirements (short versions) |
| 4 | Architecture | The MVC diagram; follow the "Save Details" click through view, controller and model |
| 5 | **Live demo 1** | Add `sample_images`, show progress, broken-file warning, sound; preview; edit title/tags; bad tag error; search; save and reopen |
| 6 | Concurrency | The thread diagram from START_HERE step 5; why queued signals are safe |
| 7 | **Live demo 2** | Scan a 300-image folder: drag the window and search while it runs, then Cancel |
| 8 | Thread safety | The shared resources table; run `python tools/race_demo.py` live (10,006 vs 40,000) |
| 9 | Performance | Tables 1 and 3 with your numbers; GIL explanation; Amdahl calculation |
| 10 | Testing | 68 automated tests passing (run `pytest` live, under 1 second); a few manual tests; one bug you fixed |
| 11 | Git | `git log --oneline --graph --all` screenshot, the PR, the conflict before and after |
| 12 | Packaging | Run the .exe from `dist/` |
| 13 | Evaluation | 2 strengths, 2 limitations, 2 improvements |
| 14 | Questions | |

**Questions you might be asked (practise these):**
- Why didn't you just use a for-loop in the button's click handler?
- What would happen if the worker updated the table directly?
- Why is `cancel()` a direct method call and not a signal?
- Why threads and not processes in the app?
- What does the lock actually protect? What happens without it?
- What is the sequential part of your program in Amdahl's terms?
- Where is the model/view separation in your code? Show me a file with no Qt imports.
- Why does the proxy model exist?
