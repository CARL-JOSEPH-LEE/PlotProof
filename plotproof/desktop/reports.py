"""Print-ready PDF export using Qt, without a browser or online renderer."""

from html import escape
from pathlib import Path

from PySide6.QtCore import QMarginsF
from PySide6.QtGui import QFont, QPageSize, QPdfWriter, QTextDocument


def export_pdf(doc, path: Path, language="zh"):
    def e(value):
        return escape(str(value), quote=True)

    report = doc["report"]
    rows = []
    for i, finding in enumerate(report["findings"], 1):
        quotes = []
        for side in ("before", "after"):
            source = finding[side]
            context = e(source["context"]).replace(
                e(source["quote"]),
                '<span style="background-color:#e7e6bd">' + e(source["quote"]) + "</span>",
                1,
            )
            quotes.append(
                f'<td width="50%" valign="top" bgcolor="#f3f3e8"><p style="font-size:9pt;color:#5b7555">{e(source["chapter"])} · L{source["line"]}</p><p>{context}</p></td>'
            )
        page_break = "page-break-before:always;" if i > 1 else ""
        rows.append(
            f'<div style="{page_break}"><h2>{i:02d} · {e(finding["title"])}</h2><p>{e(finding["reason"])}</p><table width="100%" cellspacing="8" cellpadding="14"><tr>{"".join(quotes)}</tr></table><p><b>{e(finding["status"])}</b></p><p>{e(finding["note"])}</p></div>'
        )
    header = f'<p style="color:#5b7555;font-size:9pt">PLOTPROOF · CONTINUITY REVIEW · R{doc["revision"]:02d}</p><h1>{e(doc["title"])}</h1><p>{len(report["findings"])} 个待核对变化 / changes to review</p>'
    warnings = "".join(
        '<p style="font-size:9pt;color:#75806d">' + e(w) + "</p>" for w in report.get("warnings", [])
    )
    footer = (
        warnings
        + '<p style="font-size:9pt;color:#75806d">引文已经核对，判断仍需作者复核。 / Exact quotes; author judgment required.</p>'
    )
    text = QTextDocument()
    text.setDefaultFont(QFont("Segoe UI", 11))
    text.setHtml(
        '<html><body style="color:#263a2d;line-height:150%;">'
        + header
        + ("".join(rows) or "<p>No suspected issues found. This is not a consistency guarantee.</p>")
        + footer
        + "</body></html>"
    )
    temporary = Path(str(path) + ".tmp")
    writer = QPdfWriter(str(temporary))
    writer.setTitle(doc["title"] + " · PlotProof")
    writer.setCreator("PlotProof native desktop")
    writer.setResolution(144)
    writer.setPageSize(QPageSize(QPageSize.PageSizeId.A4))
    writer.setPageMargins(QMarginsF(18, 18, 18, 18))
    text.print_(writer)
    del writer
    if not temporary.exists() or temporary.stat().st_size < 100:
        raise OSError("PDF export did not produce a valid file.")
    temporary.replace(path)
