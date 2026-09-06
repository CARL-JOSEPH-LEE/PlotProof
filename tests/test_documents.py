import zipfile

import pytest

from plotproof.importers import read_manuscript
from plotproof.preferences import Preferences
from plotproof.providers import Settings
from plotproof.storage import Conflict, Store


@pytest.mark.parametrize("encoding", ["utf-8-sig", "utf-16", "gb18030"])
def test_unicode_plain_manuscripts(encoding, tmp_path):
    text = "第一章\n\n林舟的眼睛是灰色。"
    path = tmp_path / "中文稿件.txt"
    path.write_bytes(text.encode(encoding))
    imported, _ = read_manuscript(path)
    assert imported == text


def test_docx_heading_body_table_and_tabs_are_imported(tmp_path):
    path = tmp_path / "story.docx"
    xml = """<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"><w:body>
      <w:p><w:pPr><w:pStyle w:val="Heading1"/></w:pPr><w:r><w:t>The beginning</w:t></w:r></w:p>
      <w:p><w:r><w:t>Mara has gray eyes.</w:t></w:r></w:p>
      <w:tbl><w:tr><w:tc><w:p><w:r><w:t>Mara has brown eyes.</w:t></w:r></w:p></w:tc></w:tr></w:tbl>
      </w:body></w:document>"""
    with zipfile.ZipFile(path, "w") as archive:
        archive.writestr("word/document.xml", xml)
    text, encoding = read_manuscript(path)
    assert text.startswith("# The beginning") and "brown eyes" in text and encoding == "DOCX"


def test_docx_tracked_changes_are_not_silently_accepted(tmp_path):
    path = tmp_path / "revisions.docx"
    xml = '<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"><w:body><w:p><w:ins><w:r><w:t>Unaccepted revision.</w:t></w:r></w:ins></w:p></w:body></w:document>'
    with zipfile.ZipFile(path, "w") as archive:
        archive.writestr("word/document.xml", xml)
    with pytest.raises(ValueError, match="tracked changes"):
        read_manuscript(path)


def test_draft_recovery_version_restore_and_archive(tmp_path):
    store = Store(tmp_path)
    original = "Mara has gray eyes."
    doc = store.create("Novel", original)
    store.save_draft(doc["id"], "An unfinished rewrite.", 1)
    assert Store(tmp_path).read(doc["id"])["draft"]["text"] == "An unfinished rewrite."
    updated = store.update(doc["id"], "Mara has brown eyes.", 1)
    assert "draft" not in updated
    assert store.history(doc["id"])[0]["revision"] == 1
    restored = store.restore(doc["id"], 1, 2)
    assert restored["text"] == original and restored["revision"] == 3
    assert len(store.history(doc["id"])) == 2
    with pytest.raises(Conflict):
        store.save_draft(doc["id"], "A stale edit", 2)
    store.archive(doc["id"])
    assert store.list() == [] and len(store.list(archived=True)) == 1
    store.archive(doc["id"], False)
    assert store.list()[0]["id"] == doc["id"]


def test_corrupt_project_does_not_hide_healthy_projects(tmp_path):
    store = Store(tmp_path)
    doc = store.create("Healthy", "A quiet morning.")
    (store.projects / ("a" * 32 + ".json")).write_text("broken", encoding="utf-8")
    assert store.list()[0]["id"] == doc["id"]
    assert len(store.warnings) == 1


def test_model_settings_persist_but_credentials_do_not(tmp_path):
    prefs = Preferences(tmp_path)
    prefs.save_model(Settings("compatible", "https://example.test/v1", "fixture-model", "fixture-secret"))
    assert "fixture-secret" not in prefs.path.read_text()
    restored = Preferences(tmp_path).model("en")
    assert restored.model == "fixture-model" and restored.api_key == ""
