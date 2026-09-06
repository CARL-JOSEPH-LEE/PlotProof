import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import threading
import time

import pytest

pytest.importorskip("PySide6")
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication

from plotproof.desktop.selftest import run
from plotproof.desktop.window import WorkbenchWindow
from plotproof.engine import Cancelled, analyze
from plotproof.providers import Settings


@pytest.fixture(scope="module")
def app():
    return QApplication.instance() or QApplication(["PlotProof-tests"])


def settle(window, seconds=5):
    deadline = time.monotonic() + seconds
    while window.worker and time.monotonic() < deadline:
        QTest.qWait(20)
    assert window.worker is None


def test_actual_native_widget_workflow(app, tmp_path):
    result = run(app, tmp_path)
    assert result["passed"], result.get("error")
    assert len(result["checks"]) == 6


def test_source_jump_uses_utf16_positions_and_selects_exact_quote(app, tmp_path):
    window = WorkbenchWindow(tmp_path, "en")
    text = "# Start\n\n🙂 A quiet morning. Mara has gray eyes.\n\n# Later\n\nMara has brown eyes."
    doc = window.store.create("Unicode", text)
    doc = window.store.save_report(doc["id"], analyze(text), 1)
    window.load_document(doc)
    finding = doc["report"]["findings"][0]
    window.jump_source(finding["before"]["paragraph_id"])
    assert window.editor.textCursor().selectedText() == finding["before"]["quote"]
    window.close()


def test_sample_never_uses_configured_paid_or_unavailable_model(app, tmp_path):
    window = WorkbenchWindow(tmp_path, "en")
    window.model = Settings("compatible", "https://example.invalid/v1", "unavailable", "fixture-key")
    window.sample()
    settle(window)
    assert window.doc["report"]["provider"]["provider"] == "rules"
    assert window.doc["report"]["stats"]["requests"] == 0
    assert window.model.provider == "compatible"
    window.close()


def test_close_during_review_cancels_without_losing_previous_report(app, tmp_path, monkeypatch):
    window = WorkbenchWindow(tmp_path, "en")
    window.show()
    window.sample()
    settle(window)
    previous = window.doc["report"]
    started = threading.Event()

    def delayed(text, settings, *, progress, cancel, cache_dir):
        started.set()
        if cancel.wait(5):
            raise Cancelled()
        return analyze(text, settings)

    monkeypatch.setattr("plotproof.desktop.window.analyze", delayed)
    window.start_analysis()
    deadline = time.monotonic() + 2
    while not started.is_set() and time.monotonic() < deadline:
        QTest.qWait(20)
    window.close()
    settle(window)
    QTest.qWait(30)
    assert not window.isVisible()
    assert window.store.read(window.doc["id"])["report"] == previous


def test_switching_projects_flushes_draft_and_keeps_notes_separate(app, tmp_path):
    window = WorkbenchWindow(tmp_path, "en")
    text = "Mara has gray eyes.\n\nMara has brown eyes."
    first = window.store.create("One", text)
    second = window.store.create("Two", text)
    for doc in (first, second):
        window.store.save_report(doc["id"], analyze(text), 1)
    window.open_project(first["id"])
    window.note_edit.setPlainText("This belongs only to One.")
    window.open_project(second["id"])
    assert window.note_edit.toPlainText() == ""
    window.editor.setPlainText(text + "\n\nAn unfinished ending.")
    window.open_project(first["id"])
    assert window.note_edit.toPlainText() == "This belongs only to One."
    window.open_project(second["id"])
    assert window.editor.toPlainText().endswith("An unfinished ending.")
    window.close()
