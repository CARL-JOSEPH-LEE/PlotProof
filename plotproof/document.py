"""Parse source text without losing the positions behind a piece of evidence."""

import re
from dataclasses import asdict, dataclass
from hashlib import sha256

MAX_CHARS = 300_000
MAX_PARAGRAPH = 1800
HEADING = re.compile(
    r"^(?:#{1,6}\s+.+|第[零〇一二三四五六七八九十百千万两\d]+[章回卷节].*|(?:chapter|part|prologue|epilogue)\b.*)$",
    re.I,
)


def digest(value: str) -> str:
    return sha256(value.encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class Paragraph:
    id: str
    chapter: str
    chapter_index: int
    text: str
    start: int
    end: int
    line: int
    index: int

    def to_dict(self):
        return asdict(self)


def normalize_text(text: str) -> str:
    if not isinstance(text, str) or not text.strip():
        raise ValueError("稿件不能为空 / Manuscript is empty.")
    if len(text) > MAX_CHARS:
        raise ValueError(f"第一版单份稿件最多 {MAX_CHARS:,} 个字符 / Manuscript too large.")
    if "\x00" in text:
        raise ValueError("请导入 UTF-8 的 TXT 或 Markdown 文本 / Binary files are not supported.")
    return text.removeprefix("\ufeff").replace("\r\n", "\n").replace("\r", "\n")


def parse(text: str) -> list[Paragraph]:
    text = normalize_text(text)
    result = []
    occurrences: dict[str, int] = {}
    chapter, chapter_index = "开篇 / Opening", 0
    # Blank lines and chapter headings delimit paragraphs. Line numbers refer to
    # the normalized manuscript visible in the editor, never to a model's output.
    offset = 0
    pending_start = None
    pending_end = 0

    def flush():
        nonlocal pending_start
        if pending_start is None:
            return
        pos, end = pending_start, pending_end
        while pos < end:
            stop = min(pos + MAX_PARAGRAPH, end)
            if stop < end:
                boundary = max(text.rfind(c, pos + MAX_PARAGRAPH // 2, stop) for c in "。！？.!?\n")
                if boundary >= 0:
                    stop = boundary + 1
            raw = text[pos:stop]
            left = len(raw) - len(raw.lstrip())
            value = raw.strip()
            if value:
                start = pos + left
                key = digest(value)[:16]
                occurrence = occurrences.get(key, 0)
                occurrences[key] = occurrence + 1
                result.append(
                    Paragraph(
                        f"p-{key}-{occurrence}",
                        chapter,
                        chapter_index,
                        value,
                        start,
                        start + len(value),
                        text.count("\n", 0, start) + 1,
                        len(result),
                    )
                )
            pos = stop
        pending_start = None

    for line in text.splitlines(keepends=True):
        clean = line.strip()
        if HEADING.match(clean):
            flush()
            chapter = re.sub(r"^#{1,6}\s+", "", clean)
            chapter_index += 1
        elif not clean:
            flush()
        else:
            if pending_start is None:
                pending_start = offset
            pending_end = offset + len(line.rstrip("\n"))
        offset += len(line)
    flush()
    if not result:
        raise ValueError("稿件只有标题，请添加正文 / Add manuscript text below the headings.")
    return result


def evidence(paragraph: Paragraph, quote: str) -> dict:
    if not isinstance(quote, str) or len(quote.strip()) < 4 or quote not in paragraph.text:
        raise ValueError("Evidence must be an exact excerpt of its source paragraph.")
    # An ambiguous quotation cannot point to a unique position.
    if paragraph.text.count(quote) != 1:
        raise ValueError("Evidence is ambiguous; quote a longer unique excerpt.")
    local = paragraph.text.index(quote)
    return {
        "paragraph_id": paragraph.id,
        "quote": quote,
        "context": paragraph.text,
        "chapter": paragraph.chapter,
        "chapter_index": paragraph.chapter_index,
        "line": paragraph.line + paragraph.text.count("\n", 0, local),
        "start": paragraph.start + local,
        "end": paragraph.start + local + len(quote),
    }


def batches(paragraphs: list[Paragraph], limit: int = 10_000):
    group, size = [], 0
    for paragraph in paragraphs:
        if group and size + len(paragraph.text) > limit:
            yield group
            group, size = [], 0
        group.append(paragraph)
        size += len(paragraph.text)
    if group:
        yield group
