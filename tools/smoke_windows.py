"""Validate the packaged native GUI in a Unicode path with no development PATH."""

import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("exe", type=Path)
    parser.add_argument("--report", type=Path, help="Optionally save the diagnostic JSON outside the package")
    args = parser.parse_args()
    if sys.platform != "win32":
        raise SystemExit("Run this test on Windows.")
    source = args.exe.resolve(strict=True)
    work = Path(tempfile.gettempdir()).resolve()
    scratch = Path(tempfile.mkdtemp(prefix="PlotProof 原生 EXE ", dir=work)).resolve()
    if not scratch.is_relative_to(work):
        raise RuntimeError("Unexpected scratch directory")
    destination = scratch / "PlotProof"
    shutil.copytree(source.parent, destination)
    assert not any(
        "webengine" in p.name.lower() or p.name.lower() == "node.exe" for p in destination.rglob("*")
    ), "Unexpected browser runtime"
    environment = os.environ.copy()
    environment["PATH"] = str(Path(environment.get("SystemRoot", r"C:\Windows")) / "System32")
    for key in ("PYTHONHOME", "PYTHONPATH", "NODE_PATH", "QT_PLUGIN_PATH", "QML2_IMPORT_PATH"):
        environment.pop(key, None)
    diagnostic = scratch / "native-check.json"
    result = subprocess.run(
        [str(destination / source.name), "--self-test", str(diagnostic), "--data-dir", str(scratch / "稿件")],
        cwd=scratch,
        env=environment,
        timeout=90,
        creationflags=subprocess.CREATE_NO_WINDOW,
    )
    if not diagnostic.exists():
        raise RuntimeError(f"No native diagnostic result. Exit={result.returncode}; files kept at {scratch}")
    report = json.loads(diagnostic.read_text(encoding="utf-8"))
    report.update(exe=str(source), isolated_runtime=True, unicode_path=True)
    if args.report:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    assert result.returncode == 0 and report["passed"] and report["frozen"], report
    print(json.dumps(report, ensure_ascii=True, indent=2))
    if scratch.resolve().is_relative_to(work.resolve()):
        shutil.rmtree(scratch)


if __name__ == "__main__":
    main()
