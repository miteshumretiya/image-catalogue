# Task 13: Git Workflow, Step by Step

The brief says Git must be used **throughout** the project, not added at the end. So build the project up in stages and commit as you go. Each stage below adds a few files. Copy them into your repo (or type them in, which is better for learning), run them, and commit.

Commit messages: short, present tense, saying what changed, e.g. `Add catalogue save and load`. Avoid messages like `update` or `stuff`.

---

## Stage 0: One-time setup

```bash
git config --global user.name "Your Name"
```
```bash
git config --global user.email "you@example.com"
```

Create an **empty** repository on GitHub called `image-catalogue` (no README). Then, in your project folder:

```bash
git init
```
```bash
git branch -M main
```
```bash
git remote add origin https://github.com/YOUR-USERNAME/image-catalogue.git
```

## Stage 1: Project skeleton (main branch)

Add: `.gitignore`, `requirements.txt`, `requirements-dev.txt`, `README.md`, `docs/01_design_specification.md`

```bash
git add .gitignore requirements.txt requirements-dev.txt README.md docs/01_design_specification.md
```
```bash
git commit -m "Initial project setup with design specification"
```
```bash
git push -u origin main
```

## Stage 2: The model

Add: `catalogue/__init__.py`, `catalogue/model/` (all files), `pytest.ini`, `tests/test_image_item.py`, `tests/test_catalogue.py`

```bash
python -m pytest
```
```bash
git add catalogue pytest.ini tests
```
```bash
git commit -m "Add ImageItem, validation rules and ImageCatalogue with tests"
```

Then add `tests/test_processing.py` (processing.py is already in), and commit:
```bash
git add tests/test_processing.py
```
```bash
git commit -m "Add tests for image finding and thumbnail creation"
```

## Stage 3: The GUI (still single-threaded for now)

Add: `main.py`, `catalogue/views/`, `catalogue/controller/`, `assets/done.wav`, `tools/make_sound.py`, `tools/make_sample_images.py`

To begin with, make `start_scan` in the controller a simple loop with no thread:

```python
    def start_scan(self, folder):
        # First version: no thread. The window freezes until this loop ends!
        for path in find_images(folder):
            try:
                self.table_model.add_item(process_image(path, self.thumb_dir))
            except OSError:
                pass
        self._update_count()
```
(It needs `from catalogue.model.processing import find_images, process_image` at the top.)

Try it on a 300-image folder and you'll **see the window freeze** ("Not responding"). Take a screenshot, because it shows in your report why threading is needed. In Stage 4 you replace it with the threaded version.

```bash
git add main.py catalogue assets tools
```
```bash
git commit -m "Add main window, table model and controller"
```

## Stage 4: Feature branch for threading

```bash
git checkout -b feature/threaded-processing
```

Add `catalogue/workers/scan_worker.py` and the threaded version of the controller, plus `tests/test_scan_worker.py` and `tools/race_demo.py`.

```bash
git add catalogue/workers tests/test_scan_worker.py tools/race_demo.py
```
```bash
git commit -m "Add ScanWorker that scans folders in a background thread pool"
```
```bash
git add catalogue/controller/main_controller.py
```
```bash
git commit -m "Run scan in QThread with progress bar and cancel"
```
```bash
git push -u origin feature/threaded-processing
```

## Stage 5: Pull request and merge

On GitHub: **Pull requests > New pull request**, base `main`, compare `feature/threaded-processing`. Write a short description of what it adds and how you tested it. Review the "Files changed" tab, then **Merge pull request**. Take screenshots of the PR page for your report.

Then update your local main:

```bash
git checkout main
```
```bash
git pull origin main
```

## Stage 6: A controlled merge conflict (for demonstration)

The brief allows a deliberately created conflict if no natural one happens.

1. Make a branch and change the window title there:
```bash
git checkout -b feature/window-title
```
In `catalogue/views/main_window.py` change `self.setWindowTitle("Image Catalogue")` to `self.setWindowTitle("Image Catalogue - Photo Organiser")`.
```bash
git commit -am "Change window title to include subtitle"
```

2. Go back to main and change **the same line** differently:
```bash
git checkout main
```
Change it to `self.setWindowTitle("My Image Catalogue")`.
```bash
git commit -am "Rename window title"
```

3. Merge, and Git will report a conflict:
```bash
git merge feature/window-title
```
The file now contains:
```
<<<<<<< HEAD
        self.setWindowTitle("My Image Catalogue")
=======
        self.setWindowTitle("Image Catalogue - Photo Organiser")
>>>>>>> feature/window-title
```
**Screenshot this.** `HEAD` is the version on main. The part after `=======` is the version from the branch. Git can't choose because both changed the same line.

4. Resolve it: edit the file so only the line you want remains (e.g. `self.setWindowTitle("Image Catalogue - Photo Organiser")`), and delete the marker lines. Then:
```bash
python -m pytest
```
```bash
git add catalogue/views/main_window.py
```
```bash
git commit -m "Merge feature/window-title and resolve title conflict"
```
```bash
git push origin main
```

## Stage 7: Testing, benchmark, packaging, fixes

Use a second branch for testing work:
```bash
git checkout -b feature/testing
```
Add `benchmark/`, `docs/02_test_plan.md`, `docs/03_performance_investigation.md`, then commit, push, PR and merge as in Stage 5.

When you find a bug while testing, fix it in **its own commit**, e.g.:
```bash
git commit -am "Fix: refresh details form after saving so tags show cleaned values"
```
That way the Git history shows the debugging process (Task 12).

Finally, packaging:
```bash
git add image_catalogue.spec
```
```bash
git commit -m "Add PyInstaller build configuration"
```

## Useful commands for evidence screenshots

```bash
git log --oneline --graph --all
```
```bash
git branch -a
```
```bash
git status
```

The `--graph` view shows your branches splitting off and merging back in. Put that in the report.
