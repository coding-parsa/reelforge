# PyInstaller spec — produces a single Reelforge.exe (no console, no installer).
#   .venv\Scripts\pyinstaller.exe --clean --noconfirm packaging\reelforge.spec
from pathlib import Path

from PyInstaller.utils.hooks import collect_submodules

ROOT = Path(SPECPATH).parent             # noqa: F821 — SPECPATH is the folder holding this spec

datas = [
    (str(ROOT / "reelforge" / "web"), "web"),
    (str(ROOT / "assets" / "fonts"), "assets/fonts"),
    (str(ROOT / "assets" / "sfx"), "assets/sfx"),
    (str(ROOT / "assets" / "broll"), "assets/broll"),
    (str(ROOT / "assets" / "music"), "assets/music"),
    (str(ROOT / "themes"), "themes"),
    (str(ROOT / "docs"), "docs"),
]
if (ROOT / "assets" / "logo.png").exists():
    datas.append((str(ROOT / "assets" / "logo.png"), "assets"))
if (ROOT / "hooks" / "examples").exists():
    datas.append((str(ROOT / "hooks" / "examples"), "hooks/examples"))

hiddenimports = (
    collect_submodules("uvicorn")
    + collect_submodules("fastapi")
    + ["h11", "websockets", "httptools", "anyio", "sniffio"]
)

a = Analysis(                                     # noqa: F821
    [str(ROOT / "run.py")],
    pathex=[str(ROOT)],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    runtime_hooks=[],
    excludes=["tkinter", "matplotlib", "numpy", "pandas", "PIL.ImageQt", "PyQt5", "PySide6"],
    noarchive=False,
)
pyz = PYZ(a.pure)                                  # noqa: F821

exe = EXE(                                         # noqa: F821
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name="Reelforge",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    icon=str(ROOT / "packaging" / "reelforge.ico"),
)
