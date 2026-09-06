import threading
from pathlib import Path

import pytest

from plotproof.document import MAX_CHARS, batches, evidence, normalize_text, parse
from plotproof.engine import Cancelled, analyze
from plotproof.export import html_report
from plotproof.providers import ProviderError, Settings
from plotproof.storage import Conflict, Store

EXAMPLES = Path(__file__).resolve().parents[1] / "plotproof" / "examples"


@pytest.mark.parametrize("language", ["zh", "en"])
def test_examples_detect_conflicts_but_not_explained_changes(language):
    text = (EXAMPLES / f"{language}.txt").read_text(encoding="utf-8")
    report = analyze(text)
    assert len(report["findings"]) == 4
    assert report["stats"]["chapters"] == 8
    assert report["stats"]["requests"] == 0
    assert report["stats"]["facts"] == 11
    for issue in report["findings"]:
        assert issue["subject"] not in {"silver key", "银钥匙"}
        for side in ("before", "after"):
            v = issue[side]
            assert text[v["start"] : v["end"]] == v["quote"]
            assert text.count("\n", 0, v["start"]) + 1 == v["line"]


@pytest.mark.parametrize(
    "text",
    ["", "  ", "# Title\n\n", "Chapter 1\n", "binary\x00data", "a" * (MAX_CHARS + 1)],
    ids=["empty", "spaces", "markdown-heading", "chapter-heading", "binary", "oversized"],
)
def test_rejects_empty_binary_or_oversized_manuscripts(text):
    with pytest.raises(ValueError):
        parse(text)


def test_unicode_offsets_crlf_long_paragraph_and_stable_ids():
    original = "\ufeff# 起点\r\n\r\n🙂林舟的眼睛是灰色。\r\n下一行。\r\n\r\n第二章\r\n" + "很长的段落。" * 400
    text = normalize_text(original)
    paragraphs = parse(text)
    assert len(paragraphs) > 2
    for p in paragraphs:
        assert text[p.start : p.end] == p.text
        assert len(p.text) <= 1800
    first = paragraphs[0]
    quote = evidence(first, "林舟的眼睛是灰色")
    assert text[quote["start"] : quote["end"]] == quote["quote"]
    assert parse("# New opening\n\nUnrelated text.\n\n" + text)[1].id == first.id
    assert sum(len(group) for group in batches(paragraphs, 2000)) == len(paragraphs)


def test_evidence_rejects_invented_or_ambiguous_quote():
    p = parse("Mara has gray eyes. Mara has gray eyes.")[0]
    with pytest.raises(ValueError):
        evidence(p, "Mara has gray eyes")
    with pytest.raises(ValueError):
        evidence(p, "Mara has green eyes")


@pytest.mark.parametrize(
    "text",
    [
        "Mara has gray eyes.\n\nIn a dream, Mara has blue eyes.",
        'Mara has gray eyes.\n\nShe lied: "Mara has blue eyes."',
        "The brass key was destroyed.\n\nThe brass key was reforged.\n\nShe used the brass key to unlock a door.",
        "She used the brass key to unlock a door.\n\nThe brass key was destroyed.",
        "Mara was confirmed dead.\n\nMara was resurrected.\n\nMara is still alive.",
        "Mara is still alive.\n\nMara was confirmed dead.",
        "林舟的眼睛是灰色。\n\n回忆中，林舟的眼睛是蓝色。",
        "铜钥匙被彻底熔毁。\n\n铜钥匙被成功重铸。\n\n他取出铜钥匙开门。",
    ],
)
def test_negative_cases(text):
    assert analyze(text)["findings"] == []


def test_fixing_a_conflict_removes_it_and_new_text_is_actually_scanned():
    text = "# One\nMara has gray eyes.\n\n# Two\nMara has brown eyes."
    assert len(analyze(text)["findings"]) == 1
    assert not analyze(text.replace("brown", "gray"))["findings"]
    assert len(analyze(text.replace("Mara", "Nora"))["findings"]) == 1


def test_review_survives_unrelated_edits_but_not_changed_context(tmp_path):
    store = Store(tmp_path)
    text = "Mara has gray eyes.\n\nA quiet day.\n\nMara has brown eyes."
    doc = store.create("Test", text)
    doc = store.save_report(doc["id"], analyze(text), 1)
    ident = doc["report"]["findings"][0]["id"]
    store.review(doc["id"], ident, "dismissed", "Author's explanation.", 1)
    next_text = "An unrelated introduction.\n\n" + text
    doc = store.update(doc["id"], next_text, 1)
    doc = store.save_report(doc["id"], analyze(next_text), 2)
    assert doc["report"]["findings"][0]["status"] == "dismissed"
    final_text = next_text.replace("A quiet day.", "Mara changes her appearance.")
    doc = store.update(doc["id"], final_text, 2)
    doc = store.save_report(doc["id"], analyze(final_text), 3)
    assert doc["report"]["findings"][0]["status"] == "pending"
    assert Store(tmp_path).read(doc["id"])["revision"] == 3


def test_late_results_and_stale_review_cannot_overwrite_edits(tmp_path):
    store = Store(tmp_path)
    doc = store.create("Test", "Mara has gray eyes.\n\nMara has brown eyes.")
    report = analyze(doc["text"])
    store.save_report(doc["id"], report, 1)
    store.update(doc["id"], doc["text"] + "\n\nA new ending.", 1)
    with pytest.raises(Conflict):
        store.save_report(doc["id"], report, 1)
    with pytest.raises(Conflict):
        store.review(doc["id"], report["findings"][0]["id"], "confirmed", "", 1)
    with pytest.raises(Conflict):
        store.update(doc["id"], "Overwrite it.", 1)


def test_export_escapes_text_and_contains_source_status_and_notes():
    report = analyze("Mara has gray eyes.\n\nMara has brown eyes.")
    report["findings"][0].update(note="<script>alert(1)</script>", status="confirmed")
    html = html_report({"title": "<img src=x>", "revision": 1, "report": report})
    assert "<script>" not in html and "<img src=x>" not in html
    assert "&lt;script&gt;" in html and "confirmed" in html
    assert "Mara has gray eyes" in html and "<mark>" in html


class FakeClient:
    def __init__(self, bad_quote=False, verdict="suspected"):
        self.requests = 0
        self.extractions = 0
        self.bad_quote = bad_quote
        self.verdict = verdict

    def complete(self, system, payload, schema):
        self.requests += 1
        if "paragraphs" in payload:
            self.extractions += 1
            # The fixture copies the actual parser IDs, never guesses positions.
            result = []
            for p in payload["paragraphs"]:
                for color in ("gray", "brown"):
                    if color in p["text"]:
                        result.append(
                            {
                                "subject": "Mara",
                                "attribute": "eye_color",
                                "value": color,
                                "category": "character",
                                "paragraph_id": p["id"],
                                "quote": "invented quote" if self.bad_quote else f"Mara has {color} eyes",
                                "transition": False,
                            }
                        )
            return {"facts": result}
        return {
            "reviews": [
                {
                    "id": c["id"],
                    "verdict": self.verdict,
                    "title": "Eye color changes",
                    "reason": "The two passages give different eye colors.",
                }
                for c in payload["candidates"]
            ]
        }


def test_model_pipeline_checks_evidence_and_reuses_only_extraction(tmp_path):
    settings = Settings("ollama", "http://localhost:11434", "test-model", language="en")
    text = "Mara has gray eyes.\n\nMara has brown eyes."
    client = FakeClient()
    report = analyze(text, settings, client=client, cache_dir=tmp_path)
    assert len(report["findings"]) == 1 and client.extractions == 1 and client.requests == 2
    second = FakeClient()
    cached = analyze(text, settings, client=second, cache_dir=tmp_path)
    assert cached["stats"]["cached_batches"] == 1 and second.extractions == 0 and second.requests == 1
    bad = analyze(text, settings, client=FakeClient(bad_quote=True))
    assert not bad["findings"] and bad["warnings"]
    explained = analyze(text, settings, client=FakeClient(verdict="explained"))
    assert not explained["findings"] and explained["stats"]["filtered"] == 1


def test_cancellation_prevents_model_calls():
    cancel = threading.Event()
    cancel.set()
    client = FakeClient()
    with pytest.raises(Cancelled):
        analyze(
            "Mara has gray eyes.",
            Settings("ollama", "http://localhost:11434", "test"),
            cancel=cancel,
            client=client,
        )
    assert client.requests == 0


def test_model_invalid_shape_fails_instead_of_claiming_no_issues():
    class Invalid:
        def complete(self, *args):
            return {"wrong": []}

    with pytest.raises(ProviderError):
        analyze("Mara has gray eyes.", Settings("ollama", "http://localhost:11434", "test"), client=Invalid())
