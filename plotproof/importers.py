"""Manuscript import without Office, browser services or external converters."""

import re
import zipfile
from pathlib import Path
from xml.etree import ElementTree as ET

from .document import normalize_text, parse

NS = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}


def read_manuscript(path: Path) -> tuple[str, str]:
    path = Path(path)
    if path.stat().st_size > 30_000_000:
        raise ValueError("文件超过 30 MB / File exceeds 30 MB.")
    if path.suffix.lower() == ".docx":
        try:
            with zipfile.ZipFile(path) as archive:
                info = archive.getinfo("word/document.xml")
                if info.file_size > 15_000_000:
                    raise ValueError("文档内容过大 / Document content is too large.")
                root = ET.fromstring(archive.read(info))
            paragraphs = []
            for paragraph in root.findall(".//w:body//w:p", NS):
                # Reject tracked changes instead of silently importing deleted prose.
                if paragraph.find(".//w:del", NS) is not None or paragraph.find(".//w:ins", NS) is not None:
                    raise ValueError(
                        "请先在 Word 中接受或拒绝修订，再导入 / Accept or reject tracked changes in Word before importing."
                    )
                parts = []
                for element in paragraph.iter():
                    tag = element.tag.rsplit("}", 1)[-1]
                    if tag == "t":
                        parts.append(element.text or "")
                    elif tag in {"br", "cr"}:
                        parts.append("\n")
                    elif tag == "tab":
                        parts.append("\t")
                value = "".join(parts).strip()
                style = paragraph.find("w:pPr/w:pStyle", NS)
                if style is not None:
                    name = style.get("{" + NS["w"] + "}val", "")
                    if re.match(r"(?:heading|标题)[1-6]$", name, re.I):
                        value = "# " + value
                if value:
                    paragraphs.append(value)
            text, encoding = "\n\n".join(paragraphs), "DOCX"
        except (zipfile.BadZipFile, KeyError, ET.ParseError):
            raise ValueError("这不是可读取的 DOCX 文档 / Could not read this DOCX document.") from None
    elif path.suffix.lower() in {".txt", ".md", ".markdown"}:
        raw = path.read_bytes()
        encoding = "UTF-8"
        try:
            if raw.startswith((b"\xff\xfe", b"\xfe\xff")):
                text, encoding = raw.decode("utf-16"), "UTF-16"
            else:
                text = raw.decode("utf-8-sig")
        except UnicodeError:
            try:
                text, encoding = raw.decode("gb18030"), "GB18030"
            except UnicodeError:
                raise ValueError(
                    "无法识别编码，请另存为 UTF-8 / Save this file as UTF-8 before importing."
                ) from None
    else:
        raise ValueError("支持 TXT、Markdown 和 DOCX / Supported formats: TXT, Markdown, DOCX.")
    text = normalize_text(text)
    parse(text)
    return text, encoding
