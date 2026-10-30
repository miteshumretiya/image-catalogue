# PyInstaller build configuration for Image Catalogue.
# Build with:   pyinstaller image_catalogue.spec
# Output:       dist/ImageCatalogue/      (Windows: run ImageCatalogue.exe)
#               dist/ImageCatalogue.app   (macOS: double-click it)
import sys

a = Analysis(
    ["main.py"],
    pathex=[],
    datas=[("assets/done.wav", "assets")],   # the completion sound
    hiddenimports=[],
    excludes=["pytest", "tkinter"],          # not needed at runtime, keeps the build smaller
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="ImageCatalogue",
    console=False,          # no black console window behind the app
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    name="ImageCatalogue",
)

# On a Mac, also wrap it as a normal double-clickable .app
if sys.platform == "darwin":
    app = BUNDLE(
        coll,
        name="ImageCatalogue.app",
        bundle_identifier="uk.ac.student.imagecatalogue",
    )
