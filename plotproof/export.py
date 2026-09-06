"""Portable reports with escaped evidence and explicit review status."""

import json
from html import escape


def json_report(doc):
    return json.dumps(
        {"title": doc["title"], "revision": doc["revision"], "report": doc["report"]},
        ensure_ascii=False,
        indent=2,
    )


def html_report(doc):
    report = doc["report"]

    def e(value):
        return escape(str(value), quote=True)

    rows = []
    for f in report["findings"]:
        quotes = []
        for side in ("before", "after"):
            v = f[side]
            context = e(v["context"]).replace(e(v["quote"]), "<mark>" + e(v["quote"]) + "</mark>", 1)
            quotes.append(
                f"<section><small>{e(v['chapter'])} · L{v['line']}</small><blockquote>{context}</blockquote></section>"
            )
        rows.append(
            f'<article><small>{e(f["category"])} · {e(f["status"])}</small><h2>{e(f["title"])}</h2><p>{e(f["reason"])}</p><div class="quotes">{"".join(quotes)}</div><p class="note">{e(f["note"])}</p></article>'
        )
    warnings = "".join(f"<p>{e(w)}</p>" for w in report["warnings"])
    return f'''<!doctype html><html lang="{e(report["provider"]["language"])}"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><meta http-equiv="Content-Security-Policy" content="default-src 'none'; style-src 'unsafe-inline'"><title>PlotProof — {e(doc["title"])}</title>
<style>body{{font:16px/1.7 system-ui,sans-serif;background:#f4f6fa;color:#19283d;max-width:1000px;margin:40px auto;padding:0 24px}}h1{{font:42px Georgia,serif}}h2{{font-size:20px}}article{{background:white;border:1px solid #dce2eb;border-radius:16px;margin:24px 0;padding:28px}}small{{color:#56667d}}.quotes{{display:grid;grid-template-columns:1fr 1fr;gap:24px}}blockquote{{margin:12px 0;white-space:pre-wrap}}mark{{background:#fff0bc}}.note{{color:#506275}}footer{{font-size:14px}}@media(max-width:640px){{.quotes{{grid-template-columns:1fr}}}}@media print{{body{{background:white}}article{{break-inside:avoid}}}}</style>
<header><small>PLOTPROOF · CONTINUITY REVIEW</small><h1>{e(doc["title"])}</h1><p>{len(report["findings"])} 个疑似问题 / suspected issues · {e(report["provider"]["model"])}</p><small>{e(report["created_at"])} · revision {doc["revision"]} · {e(report["source_hash"][:12])}</small></header>
{"".join(rows) or "<article>本次未发现疑似矛盾，不代表稿件没有问题。 / No suspected issues found; this is not a consistency guarantee.</article>"}
<footer>{warnings}<p>原文引文已经核对。疑似矛盾仍需作者判断。 / Quotations verified against the source; interpretation requires author review.</p></footer></html>'''
