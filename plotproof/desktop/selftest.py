"""Packaged native UI acceptance checks, using real Qt widgets and signals."""

import sys
import time
import traceback

from PySide6.QtCore import Qt
from PySide6.QtTest import QTest

from .window import WorkbenchWindow


def run(app, root):
    result = {"frozen": bool(getattr(sys, "frozen", False)), "interface": "native-qt-widgets", "checks": []}
    window = None
    try:
        window = WorkbenchWindow(root, "zh")
        window.show()
        app.processEvents()
        QTest.mouseClick(window.sample_btn, Qt.MouseButton.LeftButton)
        deadline = time.monotonic() + 15
        while window.worker and time.monotonic() < deadline:
            QTest.qWait(30)
        assert window.worker is None, "Analysis did not finish"
        assert len(window.doc["report"]["findings"]) == 4
        assert window.findings.count() == 4
        assert window.fact_tree.topLevelItemCount() > 0
        result["checks"].append(
            "Native sample button → threaded analysis → four displayed findings + fact index"
        )
        ident = window.doc["id"]
        window.note_edit.setPlainText("Native smoke note · 审阅记录")
        QTest.qWait(900)
        assert window.store.read(ident)["report"]["findings"][0]["note"] == "Native smoke note · 审阅记录"
        QTest.mouseClick(window.decision_buttons[0], Qt.MouseButton.LeftButton)
        assert window.findings.count() == 3
        assert window.store.read(ident)["report"]["findings"][0]["status"] == "confirmed"
        result["checks"].append("Native note autosave and confirm button advance the review queue")
        selected = window.doc["report"]["findings"][1]
        window.jump_source(selected["before"]["paragraph_id"])
        assert window.tabs.currentIndex() == 1
        window.editor.setPlainText(window.doc["text"].replace("1997", "1994"))
        QTest.qWait(900)
        assert window.store.read(ident)["draft"]["text"] == window.editor.toPlainText()
        assert window.stale_label.isVisible()
        assert not window.export_btn.isEnabled()
        QTest.mouseClick(window.run_btn, Qt.MouseButton.LeftButton)
        deadline = time.monotonic() + 15
        while window.worker and time.monotonic() < deadline:
            QTest.qWait(30)
        assert window.doc["revision"] == 2
        assert len(window.doc["report"]["findings"]) == 3
        assert len(window.store.history(ident)) == 1
        result["checks"].append("Editor autosave, stale-report guard, recheck and version snapshot")
        for extension in ("html", "json", "pdf"):
            output = root / f"report.{extension}"
            window.export_to(output)
            assert output.stat().st_size > 100
            if extension == "pdf":
                assert output.read_bytes().startswith(b"%PDF")
        result["checks"].append("Native PDF, HTML and JSON export")
        window.switch_language()
        assert window.lang == "en"
        assert window.run_btn.text() == "Check story"
        result["checks"].append("Live Chinese/English interface switch")
        window.close()
        app.processEvents()
        window.deleteLater()
        window = WorkbenchWindow(root)
        assert window.lang == "en" and window.doc["revision"] == 2
        assert len(window.doc["report"]["findings"]) == 3
        result["checks"].append("Restart restores project, revision, report and language")
        result["passed"] = True
    except Exception:
        result["passed"] = False
        result["error"] = traceback.format_exc()
    finally:
        if window:
            if window.worker:
                window.worker.cancel.set()
                window.worker.wait(5000)
            window.close()
            app.processEvents()
    return result
