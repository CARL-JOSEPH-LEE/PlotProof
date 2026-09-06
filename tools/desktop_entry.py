"""Frozen native desktop entry point. Never launches a web browser."""

import json
import os
import sys
import traceback
from pathlib import Path


def launch():
    try:
        from plotproof.desktop.app import main

        return main()
    except Exception:
        details = traceback.format_exc()
        if "--self-test" in sys.argv:
            destination = Path(sys.argv[sys.argv.index("--self-test") + 1])
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_text(
                json.dumps(
                    {"passed": False, "frozen": bool(getattr(sys, "frozen", False)), "error": details}
                ),
                encoding="utf-8",
            )
            return 1
        destination = Path(os.environ.get("LOCALAPPDATA", str(Path.cwd()))) / "PlotProof"
        destination.mkdir(parents=True, exist_ok=True)
        log = destination / "startup-error.log"
        log.write_text(details, encoding="utf-8")
        if sys.platform == "win32":
            import ctypes

            ctypes.windll.user32.MessageBoxW(
                None,
                "PlotProof 无法启动。请将压缩包完整解压后重试。\n"
                "Please extract the complete package and try again.\n\n"
                f"诊断日志 / Diagnostic log: {log}",
                "PlotProof",
                0x10,
            )
        return 1


if __name__ == "__main__":
    raise SystemExit(launch())
