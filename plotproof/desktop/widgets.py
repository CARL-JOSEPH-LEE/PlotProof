"""Reusable native controls and a source-derived chapter map."""

from html import escape

from PySide6.QtCore import QPointF, QRectF, QSize, Qt, Signal
from PySide6.QtGui import QColor, QFont, QLinearGradient, QPainter, QPainterPath, QPen
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from .theme import icon


def label(text="", name="", wrap=False):
    widget = QLabel(text)
    if name:
        widget.setObjectName(name)
    widget.setWordWrap(wrap)
    widget.setTextFormat(Qt.TextFormat.PlainText)
    return widget


def button(text, callback=None, name="", glyph=None, color=None):
    widget = QPushButton(text)
    widget.setCursor(Qt.CursorShape.PointingHandCursor)
    widget.setMinimumHeight(34)
    if name:
        widget.setObjectName(name)
    if glyph:
        widget.setIcon(
            icon(
                glyph,
                color
                or ("#ffffff" if name == "Primary" else "#79947b" if name.startswith("Side") else "#57705b"),
            )
        )
        widget.setIconSize(QSize(17, 17))
    if callback:
        widget.clicked.connect(callback)
    return widget


def box(parent=None, horizontal=False, margins=(0, 0, 0, 0), spacing=10):
    layout = QHBoxLayout(parent) if horizontal else QVBoxLayout(parent)
    layout.setContentsMargins(*margins)
    layout.setSpacing(spacing)
    return layout


def panel(name="Panel"):
    widget = QFrame()
    widget.setObjectName(name)
    return widget


def scroll(content):
    area = QScrollArea()
    area.setWidgetResizable(True)
    area.setWidget(content)
    area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
    return area


def clear(layout):
    while layout.count():
        child = layout.takeAt(0)
        if child.widget():
            child.widget().deleteLater()
        elif child.layout():
            clear(child.layout())


class Mark(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(36, 40)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor("#c9dcb9"))
        painter.drawRoundedRect(QRectF(2, 3, 13, 31), 3, 3)
        painter.setBrush(QColor("#78a67c"))
        painter.drawRoundedRect(QRectF(21, 9, 13, 28), 3, 3)
        painter.setPen(QPen(QColor("#172f25"), 2))
        painter.drawLine(6, 12, 11, 12)
        painter.drawLine(25, 18, 30, 18)
        painter.setPen(QPen(QColor("#e7e5ba"), 1.5))
        painter.drawLine(12, 23, 23, 23)


class FindingCard(QWidget):
    def __init__(self, finding, category, title, status, number):
        super().__init__()
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        layout = box(self, margins=(15, 13, 15, 13), spacing=7)
        top = box(horizontal=True)
        tag = label(category, "Pill" if finding["category"] != "object" else "WarningPill")
        top.addWidget(tag)
        top.addStretch()
        top.addWidget(label(f"{number:02d}", "Muted"))
        layout.addLayout(top)
        heading = label(title, wrap=True)
        heading.setStyleSheet("font-size:14px;font-weight:600;color:#304c34;")
        layout.addWidget(heading)
        bottom = box(horizontal=True)
        bottom.addWidget(
            label(
                f"{finding['before']['chapter_index']:02d}  →  {finding['after']['chapter_index']:02d}   ·   {finding['subject']}",
                "Muted",
            )
        )
        bottom.addStretch()
        bottom.addWidget(label("●" if finding["status"] != "pending" else "○", "Muted"))
        layout.addLayout(bottom)
        self.setToolTip(status)


class EvidenceCard(QFrame):
    openSource = Signal(str)

    def __init__(self, evidence, later, tr):
        super().__init__()
        self.setObjectName("SourceAfter" if later else "SourceBefore")
        layout = box(self, margins=(20, 18, 20, 16), spacing=12)
        top = box(horizontal=True)
        top.addWidget(
            label(tr("后文", "LATER PASSAGE") if later else tr("前文", "EARLIER PASSAGE"), "Eyebrow")
        )
        top.addStretch()
        top.addWidget(label(tr("✓ 引文已核对", "✓ Exact quotation"), "Muted"))
        layout.addLayout(top)
        layout.addWidget(label(evidence["chapter"], "SourceTitle", True))
        quote = label("", "Quote", True)
        source = evidence["context"]
        # Keep the whole paragraph available in the editor; long cards show a bounded excerpt.
        pos = source.find(evidence["quote"])
        left, right = max(0, pos - 110), min(len(source), pos + len(evidence["quote"]) + 160)
        excerpt = ("…" if left else "") + source[left:right] + ("…" if right < len(source) else "")
        html = escape(excerpt).replace(
            escape(evidence["quote"]),
            '<span style="background-color:'
            + ("#dce7c5" if later else "#eadab8")
            + ';color:#36402f;">'
            + escape(evidence["quote"])
            + "</span>",
        )
        quote.setTextFormat(Qt.TextFormat.RichText)
        quote.setText('<p style="margin:0;line-height:150%;">' + html.replace("\n", "<br>") + "</p>")
        quote.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        quote.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred)
        layout.addWidget(quote)
        layout.addStretch()
        jump = button(
            tr(f"第 {evidence['line']} 行 · 定位原文", f"Line {evidence['line']} · Go to source"),
            name="Subtle",
            glyph="arrow",
        )
        jump.clicked.connect(lambda: self.openSource.emit(evidence["paragraph_id"]))
        layout.addWidget(jump, alignment=Qt.AlignmentFlag.AlignLeft)


class ChapterMap(QWidget):
    chapterClicked = Signal(int)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.report = None
        self.current = ""
        self.points = []
        self.setMinimumHeight(190)
        self.setMouseTracking(True)

    def setReport(self, report, current=""):
        self.report, self.current = report, current
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        width, height = self.width(), self.height()
        chapters = sorted({p["chapter_index"] for p in (self.report or {}).get("paragraphs", [])})
        if not chapters:
            return
        pad, baseline = 38, height - 44
        span = max(1, width - pad * 2)
        self.points = [
            (pad + i * span / max(1, len(chapters) - 1), number) for i, number in enumerate(chapters)
        ]
        painter.setPen(QPen(QColor("#d1dbbf"), 2))
        painter.drawLine(QPointF(pad, baseline), QPointF(width - pad, baseline))
        positions = dict((chapter, x) for x, chapter in self.points)
        for i, issue in enumerate((self.report or {}).get("findings", [])[:120]):
            a, b = positions[issue["before"]["chapter_index"]], positions[issue["after"]["chapter_index"]]
            selected = issue["id"] == self.current
            lift = min(baseline - 14, 34 + abs(b - a) * 0.26 + (i % 3) * 13)
            path = QPainterPath(QPointF(a, baseline))
            path.cubicTo(a, baseline - lift, b, baseline - lift, b, baseline)
            color = "#a87931" if selected else "#9fb38a"
            painter.setPen(QPen(QColor(color), 2.3 if selected else 1.2))
            painter.drawPath(path)
        for x, chapter in self.points:
            count = sum(
                chapter in (f["before"]["chapter_index"], f["after"]["chapter_index"])
                for f in (self.report or {}).get("findings", [])
            )
            painter.setPen(QPen(QColor("#839b6a" if count else "#b4c2a3"), 1.5))
            painter.setBrush(QColor("#dce8cd" if count else "#f0f3e9"))
            painter.drawEllipse(QPointF(x, baseline), 6, 6)
            painter.setPen(QColor("#75886a"))
            painter.setFont(QFont("Bahnschrift", 9))
            # Keep labels readable for long manuscripts by labelling at most ~16 points.
            if len(chapters) <= 16 or chapters.index(chapter) % max(1, len(chapters) // 12) == 0:
                painter.drawText(
                    QRectF(x - 20, baseline + 12, 40, 20), Qt.AlignmentFlag.AlignCenter, f"{chapter:02d}"
                )

    def mousePressEvent(self, event):
        if self.points:
            nearest = min(self.points, key=lambda point: abs(point[0] - event.position().x()))
            if abs(nearest[0] - event.position().x()) < 20:
                self.chapterClicked.emit(nearest[1])


class StoryArt(QWidget):
    """Code-native cover art, not a fabricated application screenshot."""

    def __init__(self):
        super().__init__()
        self.setMinimumSize(340, 300)
        self.setMaximumHeight(370)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.scale(self.width() / 450, self.height() / 340)
        gradient = QLinearGradient(0, 0, 450, 340)
        gradient.setColorAt(0, QColor("#e4ead8"))
        gradient.setColorAt(1, QColor("#f0eade"))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(gradient)
        painter.drawRoundedRect(QRectF(0, 0, 450, 340), 16, 16)
        painter.setPen(QPen(QColor("#c9d2b6"), 1))
        for radius in (70, 115, 160):
            painter.drawEllipse(QPointF(233, 170), radius, radius)
        for y, x, chapter, text, accent in (
            (55, 45, "CHAPTER 02", "The key was destroyed.", "#e8d7b3"),
            (204, 125, "CHAPTER 07", "The key opened the door.", "#d5e4bd"),
        ):
            painter.setPen(QPen(QColor("#d1d7c3"), 1))
            painter.setBrush(QColor("#fffef6"))
            painter.drawRoundedRect(QRectF(x, y, 278, 97), 8, 8)
            painter.setPen(QColor("#7e8c6d"))
            painter.setFont(QFont("Bahnschrift", 8))
            painter.drawText(x + 18, y + 26, chapter)
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QColor(accent))
            painter.drawRoundedRect(QRectF(x + 16, y + 38, 246, 28), 3, 3)
            painter.setPen(QColor("#405139"))
            painter.setFont(QFont("Georgia", 13))
            painter.drawText(x + 22, y + 58, text)
        path = QPainterPath(QPointF(183, 153))
        path.cubicTo(184, 205, 269, 150, 268, 204)
        painter.setPen(QPen(QColor("#a9b28a"), 2, Qt.PenStyle.DashLine))
        painter.drawPath(path)
