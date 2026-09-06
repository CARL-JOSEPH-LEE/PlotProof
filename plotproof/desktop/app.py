"""Application lifecycle: native window, local single instance, clean shutdown."""

import argparse
import hashlib
import json
import os
import sys
import traceback
from pathlib import Path


def main(argv=None):
    parser = argparse.ArgumentParser(prog="PlotProof")
    parser.add_argument("--data-dir", type=Path)
    parser.add_argument("--language", choices=("zh", "en"))
    parser.add_argument("--open", type=Path)
    parser.add_argument(
        "--self-test", type=Path, help="Run native-widget smoke checks and write diagnostic JSON"
    )
    args = parser.parse_args(argv)
    if args.self_test:
        os.environ["QT_QPA_PLATFORM"] = "offscreen"
    from PySide6.QtCore import QLockFile, QTimer
    from PySide6.QtGui import QFont
    from PySide6.QtNetwork import QLocalServer, QLocalSocket
    from PySide6.QtWidgets import QApplication, QMessageBox

    from .window import WorkbenchWindow

    app = QApplication.instance() or QApplication(["PlotProof"])
    app.setApplicationName("PlotProof")
    app.setOrganizationName("PlotProof")
    app.setStyle("Fusion")
    app.setFont(QFont("Segoe UI", 10))
    data = args.data_dir or (Path(os.environ.get("LOCALAPPDATA", str(Path.cwd()))) / "PlotProof")
    data.mkdir(parents=True, exist_ok=True)
    if args.self_test:
        from .selftest import run

        result = run(app, data)
        args.self_test.parent.mkdir(parents=True, exist_ok=True)
        args.self_test.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
        return 0 if result.get("passed") else 1

    name = "PlotProof-" + hashlib.sha256(str(data.resolve()).casefold().encode()).hexdigest()[:20]
    lock = QLockFile(str(data / "desktop.lock"))
    lock.setStaleLockTime(0)
    if not lock.tryLock(0):
        socket = QLocalSocket()
        socket.connectToServer(name)
        if socket.waitForConnected(1500):
            socket.write(b"focus")
            socket.flush()
            socket.waitForBytesWritten(1000)
            socket.disconnectFromServer()
            return 0
        QMessageBox.information(
            None, "PlotProof", "PlotProof 已在运行或正在启动。 / PlotProof is already running or starting."
        )
        return 1
    local = QLocalServer()
    QLocalServer.removeServer(name)
    if not local.listen(name):
        lock.unlock()
        QMessageBox.warning(None, "PlotProof", "无法建立桌面实例。 / Could not create the desktop instance.")
        return 1
    window = WorkbenchWindow(data, args.language)

    def focus():
        connection = local.nextPendingConnection()
        if connection:
            connection.disconnectFromServer()
            connection.deleteLater()
        if window.isMinimized():
            window.showNormal()
        window.show()
        window.raise_()
        window.activateWindow()

    local.newConnection.connect(focus)

    def report_exception(kind, value, trace):
        (data / "desktop-error.log").write_text(
            "".join(traceback.format_exception(kind, value, trace)), encoding="utf-8"
        )
        window.notify(
            "操作未完成，请重试。日志已保存在本机。 / The action failed. Try again; a local diagnostic log was saved.",
            True,
        )

    sys.excepthook = report_exception
    window.show()
    if sys.platform == "win32":
        # Use the operating system's title bar, resizing, snap and accessibility.
        import ctypes

        dark = ctypes.c_int(1)
        ctypes.windll.dwmapi.DwmSetWindowAttribute(
            int(window.winId()), 20, ctypes.byref(dark), ctypes.sizeof(dark)
        )
    if args.open:
        QTimer.singleShot(0, lambda: window.import_path(args.open))
    try:
        return app.exec()
    finally:
        local.close()
        lock.unlock()


if __name__ == "__main__":
    raise SystemExit(main())
