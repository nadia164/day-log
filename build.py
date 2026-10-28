"""Build Daylog.exe and the Windows installer.

    python build.py

Steps:
  1. Draw the app icon into assets/daylog.ico
  2. PyInstaller bundles Python + PySide6 + the app into dist/Daylog/Daylog.exe
  3. Inno Setup (if installed) wraps that folder into
     installer_output/Daylog-Setup-<version>.exe

Needs (inside the venv):  pip install -r requirements-dev.txt
Needs (once, for step 3): Inno Setup 6, https://jrsoftware.org/isdl.php
                          or: winget install JRSoftware.InnoSetup
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
ASSETS = ROOT / "assets"
ICON = ASSETS / "daylog.ico"
BUILD = ROOT / "build"
DIST = ROOT / "dist"
APP_DIR = DIST / "Daylog"
INSTALLER_SCRIPT = ROOT / "packaging" / "installer.iss"
INSTALLER_OUTPUT = ROOT / "installer_output"

sys.path.insert(0, str(ROOT))
from daylog import __version__  # noqa: E402


def step(text: str) -> None:
    print(f"\n==> {text}")


def make_icon() -> None:
    step("Drawing assets/daylog.ico")
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")  # no window needed
    from PySide6.QtWidgets import QApplication

    from daylog.icons import save_ico

    app = QApplication.instance() or QApplication([])  # Qt needs one to draw
    ASSETS.mkdir(exist_ok=True)
    save_ico(ICON)
    del app


def write_version_file() -> Path:
    """Windows file properties for Daylog.exe (Properties → Details, Task Manager)."""
    major, minor, patch = (int(x) for x in __version__.split("."))
    path = BUILD / "version_info.txt"
    path.write_text(
        f"""VSVersionInfo(
  ffi=FixedFileInfo(filevers=({major}, {minor}, {patch}, 0), prodvers=({major}, {minor}, {patch}, 0)),
  kids=[
    StringFileInfo([StringTable('040904B0', [
      StringStruct('FileDescription', 'Daylog'),
      StringStruct('ProductName', 'Daylog'),
      StringStruct('FileVersion', '{__version__}'),
      StringStruct('ProductVersion', '{__version__}'),
      StringStruct('OriginalFilename', 'Daylog.exe'),
      StringStruct('InternalName', 'Daylog')])]),
    VarFileInfo([VarStruct('Translation', [1033, 1200])])
  ]
)
""",
        encoding="utf-8",
    )
    return path


def build_exe() -> None:
    step(f"Building Daylog.exe {__version__} with PyInstaller")
    shutil.rmtree(DIST, ignore_errors=True)
    BUILD.mkdir(exist_ok=True)
    args = [
        str(ROOT / "main.py"),
        "--name", "Daylog",
        "--windowed",          # no console window
        "--onedir",            # a folder, not one big .exe: starts faster, fewer antivirus false alarms
        "--noconfirm",
        "--clean",
        "--icon", str(ICON),
        "--distpath", str(DIST),
        "--workpath", str(BUILD / "pyinstaller"),
        "--specpath", str(BUILD),
    ]
    if sys.platform == "win32":
        args += ["--version-file", str(write_version_file())]

    import PyInstaller.__main__

    PyInstaller.__main__.run(args)
    trim()
    print(f"\nApp folder: {APP_DIR}")


# Qt pieces Daylog never uses. They only get bundled because two optional plugins
# depend on them: the on-screen virtual keyboard (needs Qt Quick/QML) and the PDF
# image reader. Daylog uses neither, and Qt skips missing plugins silently.
TRIM_PATTERNS = [
    "*virtualkeyboard*", "*VirtualKeyboard*",
    "*Qt6Quick*", "*Qt6Qml*",
    "*qpdf*", "*Qt6Pdf*",
]


def trim() -> None:
    step("Removing unused Qt files")
    pyside = APP_DIR / "_internal" / "PySide6"
    before = _folder_size(APP_DIR)
    shutil.rmtree(pyside / "translations", ignore_errors=True)  # Windows layout
    shutil.rmtree(pyside / "Qt" / "translations", ignore_errors=True)  # macOS/Linux layout
    for pattern in TRIM_PATTERNS:
        for path in pyside.rglob(pattern):
            if path.is_file():
                path.unlink()
    print(f"Saved {(before - _folder_size(APP_DIR)) / 1e6:.0f} MB "
          f"(app folder is now {_folder_size(APP_DIR) / 1e6:.0f} MB)")


def _folder_size(folder: Path) -> int:
    return sum(f.stat().st_size for f in folder.rglob("*") if f.is_file() and not f.is_symlink())


def find_inno_compiler() -> Path | None:
    found = shutil.which("ISCC")
    if found:
        return Path(found)
    for base in (os.environ.get("ProgramFiles(x86)"), os.environ.get("ProgramFiles"),
                 os.path.join(os.environ.get("LOCALAPPDATA", ""), "Programs")):
        if base:
            candidate = Path(base) / "Inno Setup 6" / "ISCC.exe"
            if candidate.exists():
                return candidate
    return None


def build_installer() -> None:
    step("Building the installer with Inno Setup")
    if sys.platform != "win32":
        print("Skipped: the installer can only be built on Windows.")
        return
    compiler = find_inno_compiler()
    if compiler is None:
        print("Skipped: Inno Setup 6 isn't installed.\n"
              "Install it from https://jrsoftware.org/isdl.php (or: winget install JRSoftware.InnoSetup),\n"
              "then run `python build.py` again.\n"
              f"Meanwhile you can run the app directly: {APP_DIR / 'Daylog.exe'}")
        return
    INSTALLER_OUTPUT.mkdir(exist_ok=True)
    subprocess.run(
        [
            str(compiler),
            f"/DAppVersion={__version__}",
            f"/DSourceDir={APP_DIR}",
            f"/DIconFile={ICON}",
            f"/DOutputDir={INSTALLER_OUTPUT}",
            str(INSTALLER_SCRIPT),
        ],
        check=True,
    )
    print(f"\nInstaller: {INSTALLER_OUTPUT / f'Daylog-Setup-{__version__}.exe'}")


def main() -> None:
    make_icon()
    build_exe()
    build_installer()
    print("\nDone.")


if __name__ == "__main__":
    main()