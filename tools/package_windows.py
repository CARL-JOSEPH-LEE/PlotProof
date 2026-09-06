"""Package the native desktop with replaceable Qt libraries and complete source."""

import argparse
import hashlib
import importlib.metadata
import json
import os
import shutil
import struct
import subprocess
import sys
import tempfile
import zipfile
import zlib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from plotproof import __version__


def make_icon(path):
    size = 64
    pixels = bytearray()
    for y in range(size):
        pixels.append(0)
        for x in range(size):
            color = (18, 35, 35, 255)
            if 11 <= x <= 28 and 10 <= y <= 49:
                color = (207, 225, 191, 255)
            if 36 <= x <= 53 and 20 <= y <= 55:
                color = (119, 165, 123, 255)
            if (16 <= x <= 23 and 19 <= y <= 22) or (41 <= x <= 48 and 29 <= y <= 32):
                color = (29, 54, 41, 255)
            if 25 <= x <= 39 and 39 <= y <= 41:
                color = (232, 225, 180, 255)
            pixels.extend(color)

    def chunk(kind, value):
        return (
            struct.pack(">I", len(value))
            + kind
            + value
            + struct.pack(">I", zlib.crc32(kind + value) & 0xFFFFFFFF)
        )

    png = (
        b"\x89PNG\r\n\x1a\n"
        + chunk(b"IHDR", struct.pack(">IIBBBBB", size, size, 8, 6, 0, 0, 0))
        + chunk(b"IDAT", zlib.compress(pixels))
        + chunk(b"IEND", b"")
    )
    path.write_bytes(
        struct.pack("<HHH", 0, 1, 1) + struct.pack("<BBBBHHII", size, size, 0, 0, 1, 32, len(png), 22) + png
    )


def archive_sources(target):
    roots = [p for p in ROOT.iterdir() if p.is_file() and p.suffix in {".md", ".toml", ".txt", ".bat"}]
    roots.extend(ROOT / name for name in ("LICENSE", ".gitignore", ".gitattributes", "installers/README.md"))
    files = roots[:]
    for name in ("plotproof", "tools", "tests", "docs", ".github"):
        files.extend((ROOT / name).rglob("*"))
    source = target / "PlotProof-source.zip"
    with zipfile.ZipFile(source, "w", zipfile.ZIP_DEFLATED) as archive:
        for file in sorted(set(files)):
            if file.is_file() and "__pycache__" not in file.parts and file.suffix not in {".pyc", ".pyo"}:
                archive.write(file, "PlotProof/" + file.relative_to(ROOT).as_posix())


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--refresh-assets",
        action="store_true",
        help="Refresh source, documentation and archive without rebuilding the unchanged binary",
    )
    args = parser.parse_args()
    if sys.platform != "win32":
        raise SystemExit("Build Windows packages on Windows.")
    name = f"PlotProof-{__version__}-windows-x64"
    output = ROOT / "installers"
    output.mkdir(exist_ok=True)
    stage = output / name
    if not args.refresh_assets:
        version = importlib.metadata.version("PySide6-Essentials")
        if version != "6.10.2":
            raise SystemExit(
                "Use the pinned build environment: python -m pip install -r requirements-build.txt"
            )
        build_files = tempfile.TemporaryDirectory(prefix="PlotProof-build-")
        work = Path(build_files.name).resolve()
        if not work.is_relative_to(Path(tempfile.gettempdir()).resolve()):
            raise RuntimeError("Unexpected temporary build directory")
        logo = work / "PlotProof.ico"
        make_icon(logo)
        version_file = work / "version.txt"
        numbers = tuple(int(p) for p in __version__.split(".")) + (0,)
        version_file.write_text(
            f"VSVersionInfo(ffi=FixedFileInfo(filevers={numbers!r}, prodvers={numbers!r}, mask=0x3f, flags=0, OS=0x40004, fileType=0x1, subtype=0x0, date=(0,0)), kids=[StringFileInfo([StringTable('040904B0', [StringStruct('CompanyName','PlotProof Contributors'), StringStruct('FileDescription','PlotProof Story Continuity Studio'), StringStruct('FileVersion','{__version__}'), StringStruct('ProductName','PlotProof'), StringStruct('ProductVersion','{__version__}'), StringStruct('LegalCopyright','MIT — CARL JOSEPH LEE and contributors')])]), VarFileInfo([VarStruct('Translation',[1033,1200])])])",
            encoding="utf-8",
        )
        command = [
            sys.executable,
            "-m",
            "PyInstaller",
            "--noconfirm",
            "--clean",
            "--onedir",
            "--windowed",
            "--name",
            "PlotProof",
            "--icon",
            str(logo),
            "--version-file",
            str(version_file),
            "--paths",
            str(ROOT),
            "--distpath",
            str(work / "bundles"),
            "--workpath",
            str(work / "build"),
            "--specpath",
            str(work),
            "--add-data",
            f"{ROOT / 'plotproof' / 'examples'}{os.pathsep}plotproof/examples",
            "--exclude-module",
            "PySide6.QtWebEngineCore",
            "--exclude-module",
            "PySide6.QtWebEngineWidgets",
            "--exclude-module",
            "PySide6.QtQml",
            "--exclude-module",
            "PySide6.QtQuick",
            "--exclude-module",
            "plotproof.server",
            str(ROOT / "tools" / "desktop_entry.py"),
        ]
        # DLL discovery searches PATH. Tools such as Poppler can ship a different
        # icuuc.dll from the Windows ICU that Qt imports, making a valid source
        # installation fail only after freezing. Use this Python and Windows.
        environment = os.environ.copy()
        windows = Path(environment.get("SystemRoot", r"C:\Windows"))
        environment["PATH"] = os.pathsep.join(
            str(path)
            for path in (
                Path(sys.executable).parent,
                Path(sys.base_prefix),
                Path(sys.base_prefix) / "DLLs",
                windows / "System32",
                windows,
            )
        )
        for key in ("PYTHONPATH", "PYTHONHOME", "QT_PLUGIN_PATH", "QML2_IMPORT_PATH"):
            environment.pop(key, None)
        subprocess.run(command, cwd=ROOT, env=environment, check=True)
        if stage.exists():
            resolved = stage.resolve()
            if not resolved.is_relative_to(output.resolve()) or resolved.name != name:
                raise RuntimeError("Unexpected package directory")
            shutil.rmtree(resolved)
        shutil.copytree(work / "bundles" / "PlotProof", stage)
        build_files.cleanup()
    if not (stage / "PlotProof.exe").exists():
        raise SystemExit("Build the executable first.")
    for file in ("LICENSE", "THIRD_PARTY_NOTICES.txt"):
        shutil.copy2(ROOT / file, stage / file)
    shutil.copy2(ROOT / "docs" / "WINDOWS_QUICKSTART.txt", stage / "START_HERE.txt")
    if (ROOT / "docs" / "licenses").exists():
        shutil.copytree(ROOT / "docs" / "licenses", stage / "licenses", dirs_exist_ok=True)
    python_license = Path(sys.base_prefix) / "LICENSE.txt"
    if python_license.exists():
        shutil.copy2(python_license, stage / "PYTHON_LICENSE.txt")
    archive_sources(stage)
    sums = []
    for file in sorted(stage.rglob("*")):
        if file.is_file() and file.name != "SHA256SUMS.txt":
            sums.append(
                hashlib.sha256(file.read_bytes()).hexdigest() + "  " + file.relative_to(stage).as_posix()
            )
    (stage / "SHA256SUMS.txt").write_text("\n".join(sums) + "\n", encoding="utf-8")
    archive = shutil.make_archive(str(stage), "zip", root_dir=stage.parent, base_dir=stage.name)
    checksum = hashlib.sha256(Path(archive).read_bytes()).hexdigest()
    Path(archive + ".sha256").write_text(checksum + "  " + Path(archive).name + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "exe": str(stage / "PlotProof.exe"),
                "zip": archive,
                "archive_MiB": round(Path(archive).stat().st_size / 1024**2, 2),
                "interface": "native Qt Widgets; no browser",
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
