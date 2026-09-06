"""Native desktop workbench. All persistent actions use the shared core store."""

from datetime import datetime
from pathlib import Path

from PySide6.QtCore import QSize, Qt, QTimer, Signal
from PySide6.QtGui import QKeySequence, QShortcut, QTextCursor
from PySide6.QtWidgets import (
    QApplication,
    QButtonGroup,
    QComboBox,
    QDialog,
    QFileDialog,
    QHeaderView,
    QInputDialog,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QMenu,
    QMessageBox,
    QPlainTextEdit,
    QProgressBar,
    QSplitter,
    QStackedWidget,
    QTreeWidget,
    QTreeWidgetItem,
    QWidget,
)

from .. import __version__
from ..document import parse
from ..engine import analyze
from ..export import html_report, json_report
from ..importers import read_manuscript
from ..preferences import Preferences
from ..rules import STATE_LABELS
from ..storage import Store
from .dialogs import ModelDialog, NewManuscript
from .theme import STYLE, icon
from .widgets import (
    ChapterMap,
    EvidenceCard,
    FindingCard,
    Mark,
    StoryArt,
    box,
    button,
    clear,
    label,
    panel,
    scroll,
)
from .worker import Worker


def qt_offset(text, index):
    """Qt cursors count UTF-16 units; source evidence counts Unicode code points."""
    return len(text[:index].encode("utf-16-le")) // 2


class WorkbenchWindow(QMainWindow):
    analysisCompleted = Signal(object)

    def __init__(self, data_dir, language=None):
        super().__init__()
        self.store = Store(Path(data_dir))
        self.preferences = Preferences(Path(data_dir))
        self.lang = language or self.preferences.get("language", "zh")
        if self.lang not in {"zh", "en"}:
            self.lang = "zh"
        self.model = self.preferences.model(self.lang)
        self.doc = None
        self.selected_id = ""
        self.filter_status = "pending"
        self.worker = None
        self.pending_close = False
        self.note_owner = None
        self._rendering = False
        self.draft_timer = QTimer(self)
        self.draft_timer.setSingleShot(True)
        self.draft_timer.setInterval(800)
        self.draft_timer.timeout.connect(self.flush_draft)
        self.note_timer = QTimer(self)
        self.note_timer.setSingleShot(True)
        self.note_timer.setInterval(750)
        self.note_timer.timeout.connect(self.flush_note)
        self.setWindowTitle("PlotProof")
        self.setWindowIcon(icon("review", "#4b7d45", 64))
        self.setMinimumSize(1100, 740)
        screen = QApplication.primaryScreen().availableGeometry()
        self.resize(min(1500, screen.width() - 60), min(960, screen.height() - 70))
        self.setAcceptDrops(True)
        self.setStyleSheet(STYLE)
        self.build_ui()
        self.shortcuts = []
        for key, callback in (
            ("Ctrl+O", self.import_dialog),
            ("Ctrl+N", self.new_project),
            ("Ctrl+S", self.commit_editor),
            ("Ctrl+Return", self.start_analysis),
            ("Ctrl+F", self.focus_search),
            ("Ctrl+Shift+E", self.export_dialog),
            ("Alt+Down", lambda: self.move_finding(1)),
            ("Alt+Up", lambda: self.move_finding(-1)),
            ("F1", self.about),
        ):
            shortcut = QShortcut(QKeySequence(key), self)
            shortcut.activated.connect(callback)
            self.shortcuts.append(shortcut)
        for index in range(4):
            shortcut = QShortcut(QKeySequence(f"Ctrl+{index + 1}"), self)
            shortcut.activated.connect(lambda i=index: self.set_tab(i))
            self.shortcuts.append(shortcut)
        self.refresh_projects()
        last = self.preferences.get("last_project")
        if last and any(
            self.projects.item(i).data(Qt.ItemDataRole.UserRole) == last for i in range(self.projects.count())
        ):
            self.open_project(last)

    def tr2(self, zh, en):
        return zh if self.lang == "zh" else en

    def localize(self, value):
        parts = value.split(" / ")
        return parts[0] if self.lang == "zh" else parts[-1]

    def categories(self):
        return {
            "character": self.tr2("人物设定", "Character"),
            "object": self.tr2("物品状态", "Object"),
            "timeline": self.tr2("时间线", "Timeline"),
            "world": self.tr2("世界规则", "World"),
        }

    def build_ui(self):
        t = self.tr2
        root = QWidget()
        self.setCentralWidget(root)
        outer = box(root, horizontal=True, spacing=0)
        sidebar = QWidget()
        sidebar.setObjectName("Sidebar")
        sidebar.setFixedWidth(216)
        side = box(sidebar, margins=(20, 27, 20, 16), spacing=10)
        brand = box(horizontal=True, spacing=8)
        brand.addWidget(Mark())
        brand.addWidget(label("PlotProof", "Brand"))
        side.addLayout(brand)
        side.addWidget(label("STORY CONTINUITY STUDIO", "SidebarOverline"))
        side.addSpacing(22)
        self.import_btn = button(
            t("导入稿件", "Import manuscript"), self.import_dialog, "SideImport", "import", "#264332"
        )
        self.import_btn.setToolTip("Ctrl+O · TXT / Markdown / Word")
        side.addWidget(self.import_btn)
        self.library_btn = button(t("我的书架", "Your library"), self.show_library, "SideButton", "grid")
        side.addWidget(self.library_btn)
        self.new_btn = button(
            t("开始一个新故事", "Start a new story"), self.new_project, "SideButton", "plus"
        )
        side.addWidget(self.new_btn)
        side.addSpacing(19)
        side.addWidget(label(t("最近打开", "RECENT MANUSCRIPTS"), "SidebarOverline"))
        self.projects = QListWidget()
        self.projects.setObjectName("Projects")
        self.projects.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.projects.itemClicked.connect(lambda item: self.open_project(item.data(Qt.ItemDataRole.UserRole)))
        self.projects.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.projects.customContextMenuRequested.connect(self.project_menu)
        side.addWidget(self.projects, 1)
        self.sample_btn = button(t("体验示例故事", "Try a sample story"), self.sample, "SideButton", "spark")
        side.addWidget(self.sample_btn)
        side.addSpacing(5)
        self.model_btn = button(
            t("检查方式与模型", "Review engine"), self.configure, "SideButton", "settings"
        )
        side.addWidget(self.model_btn)
        bottom = box(horizontal=True)
        bottom.addWidget(label(f"v{__version__}   ·   MIT", "SidebarFoot"))
        bottom.addStretch()
        language = button("EN" if self.lang == "zh" else "中文", self.switch_language, "SideButton")
        language.setFixedWidth(47)
        bottom.addWidget(language)
        self.lang_button = language
        side.addLayout(bottom)
        outer.addWidget(sidebar)

        main = QWidget()
        layout = box(main, spacing=0)
        top = box(horizontal=True, margins=(30, 17, 28, 15))
        self.breadcrumb = label(t("工作空间  /  我的书架", "WORKSPACE  /  YOUR LIBRARY"), "Eyebrow")
        top.addWidget(self.breadcrumb)
        top.addStretch()
        top.addWidget(label(t("●  本机保存", "●  Saved on this device"), "Pill"))
        self.help_btn = button("?", self.about, "Subtle")
        self.help_btn.setFixedWidth(30)
        top.addWidget(self.help_btn)
        layout.addLayout(top)
        self.toast = panel("Toast")
        toast_line = box(self.toast, horizontal=True, margins=(14, 8, 8, 8))
        self.toast_label = label("", wrap=True)
        toast_line.addWidget(self.toast_label, 1)
        toast_line.addWidget(button("×", self.toast.hide, "Subtle"))
        layout.addWidget(self.toast)
        self.toast.hide()
        self.pages = QStackedWidget()
        layout.addWidget(self.pages, 1)
        self.home = QWidget()
        self.home_layout = box(self.home, margins=(38, 28, 38, 30), spacing=24)
        self.pages.addWidget(scroll(self.home))
        self.workspace = QWidget()
        work = box(self.workspace, margins=(28, 14, 28, 0), spacing=0)
        head = box(horizontal=True, spacing=16)
        titles = box(spacing=7)
        self.document_title = label("", "PageTitle")
        titles.addWidget(self.document_title)
        self.document_meta = label("", "Muted")
        titles.addWidget(self.document_meta)
        head.addLayout(titles, 1)
        self.export_btn = button(t("导出", "Export"), self.export_dialog, glyph="export")
        self.export_btn.setToolTip("Ctrl+Shift+E")
        head.addWidget(self.export_btn)
        self.run_btn = button(t("检查故事", "Check story"), self.start_analysis, "Primary", "play")
        self.run_btn.setToolTip("Ctrl+Enter")
        head.addWidget(self.run_btn)
        work.addLayout(head)
        work.addSpacing(16)
        self.progress = QProgressBar()
        self.progress.setTextVisible(False)
        self.progress.setFixedHeight(4)
        work.addWidget(self.progress)
        self.progress.hide()
        self.job_line = QWidget()
        job = box(self.job_line, horizontal=True, margins=(0, 8, 0, 0))
        self.job_label = label("", "Muted")
        job.addWidget(self.job_label, 1)
        self.cancel_btn = button(t("取消检查", "Cancel review"), self.cancel_analysis, "Subtle")
        job.addWidget(self.cancel_btn)
        work.addWidget(self.job_line)
        self.job_line.hide()
        tabs = box(horizontal=True, spacing=4)
        self.tab_buttons = []
        self.tab_group = QButtonGroup(self)
        for i, (zh, en, glyph) in enumerate(
            (
                ("审阅台", "Review desk", "review"),
                ("稿件编辑", "Manuscript", "edit"),
                ("故事地图", "Story map", "map"),
                ("版本记录", "Versions", "history"),
            )
        ):
            tab = button(t(zh, en), lambda checked=False, index=i: self.set_tab(index), "Tab", glyph)
            tab.setCheckable(True)
            self.tab_group.addButton(tab)
            self.tab_buttons.append(tab)
            tabs.addWidget(tab)
        tabs.addStretch()
        self.revision_tag = label("R01", "Muted")
        tabs.addWidget(self.revision_tag)
        work.addLayout(tabs)
        rule = panel("Rule")
        work.addWidget(rule)
        self.stale_label = label(
            t(
                "稿件有更新。当前显示上次检查的证据；重新检查后继续审阅。",
                "Manuscript updated. These are previous findings. Run checks to review the current draft.",
            ),
            "WarningPill",
            True,
        )
        work.addWidget(self.stale_label)
        self.stale_label.hide()
        self.tabs = QStackedWidget()
        work.addWidget(self.tabs, 1)
        self.build_review()
        self.build_editor()
        self.build_map()
        self.build_history()
        self.pages.addWidget(self.workspace)
        status = panel("StatusBar")
        footer = box(status, horizontal=True, margins=(20, 6, 18, 6))
        self.save_status = label(t("就绪", "Ready"))
        footer.addWidget(self.save_status)
        footer.addStretch()
        self.engine_status = label("")
        footer.addWidget(self.engine_status)
        layout.addWidget(status)
        outer.addWidget(main, 1)
        self.set_tab(0)
        self.update_engine_status()

    def build_review(self):
        t = self.tr2
        review = QWidget()
        layout = box(review, spacing=0)
        controls = box(horizontal=True, margins=(0, 17, 0, 15), spacing=5)
        self.status_buttons = {}
        self.status_group = QButtonGroup(self)
        for key in ("pending", "confirmed", "dismissed", "all"):
            chip = button("", lambda checked=False, status=key: self.set_filter(status), "Chip")
            chip.setCheckable(True)
            self.status_group.addButton(chip)
            self.status_buttons[key] = chip
            controls.addWidget(chip)
        controls.addStretch()
        self.search = QLineEdit()
        self.search.setPlaceholderText(t("搜索人物、物品或疑点", "Search people, objects or issues"))
        self.search.setMaximumWidth(250)
        self.search.setClearButtonEnabled(True)
        self.search.textChanged.connect(self.render_findings)
        controls.addWidget(self.search)
        layout.addLayout(controls)
        self.review_split = QSplitter(Qt.Orientation.Horizontal)
        left = QWidget()
        list_layout = box(left, margins=(0, 0, 12, 8), spacing=8)
        filter_row = box(horizontal=True)
        self.findings_count = label("", "Eyebrow")
        filter_row.addWidget(self.findings_count, 1)
        self.category = QComboBox()
        self.category.addItem(t("全部类别", "All categories"), "all")
        for key, title in self.categories().items():
            self.category.addItem(title, key)
        self.category.setMaximumWidth(145)
        self.category.currentIndexChanged.connect(self.render_findings)
        filter_row.addWidget(self.category)
        list_layout.addLayout(filter_row)
        self.findings = QListWidget()
        self.findings.setObjectName("Findings")
        self.findings.setSpacing(1)
        self.findings.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.findings.currentItemChanged.connect(self.select_finding)
        list_layout.addWidget(self.findings, 1)
        list_layout.addWidget(label(t("Alt + ↑ / ↓ 切换疑点", "Alt + ↑ / ↓  Navigate issues"), "Muted"))
        self.review_split.addWidget(left)
        self.details = QWidget()
        self.detail_layout = box(self.details, margins=(22, 2, 2, 14), spacing=12)
        self.review_split.addWidget(scroll(self.details))
        self.review_split.setSizes([320, 760])
        self.review_split.setStretchFactor(1, 1)
        self.review_split.setCollapsible(0, False)
        self.review_split.setCollapsible(1, False)
        left.setMinimumWidth(260)
        layout.addWidget(self.review_split, 1)
        self.coverage = label("", "Muted", True)
        self.coverage.setContentsMargins(0, 10, 0, 10)
        layout.addWidget(self.coverage)
        self.tabs.addWidget(review)

    def build_editor(self):
        t = self.tr2
        page = QWidget()
        layout = box(page, margins=(0, 15, 0, 0), spacing=10)
        toolbar = box(horizontal=True)
        toolbar.addWidget(label(t("章节大纲", "CHAPTER OUTLINE"), "Eyebrow"))
        toolbar.addStretch()
        self.editor_search = QLineEdit()
        self.editor_search.setPlaceholderText(
            t("在稿件中查找 · Enter 下一处", "Find in manuscript · Enter for next")
        )
        self.editor_search.setMaximumWidth(300)
        self.editor_search.returnPressed.connect(self.find_in_editor)
        toolbar.addWidget(self.editor_search)
        self.save_btn = button(t("保存新版本", "Save version"), self.commit_editor, glyph="save")
        self.save_btn.setToolTip("Ctrl+S")
        toolbar.addWidget(self.save_btn)
        layout.addLayout(toolbar)
        split = QSplitter()
        self.outline = QListWidget()
        self.outline.setMinimumWidth(130)
        self.outline.setMaximumWidth(230)
        self.outline.itemClicked.connect(self.jump_outline)
        split.addWidget(self.outline)
        self.editor = QPlainTextEdit()
        self.editor.setObjectName("Manuscript")
        self.editor.setTabChangesFocus(False)
        self.editor.textChanged.connect(self.on_edit)
        self.editor.setAccessibleName(t("稿件正文编辑器", "Manuscript editor"))
        split.addWidget(self.editor)
        split.setStretchFactor(1, 1)
        split.setSizes([190, 1000])
        layout.addWidget(split, 1)
        editor_footer = box(horizontal=True, margins=(0, 5, 0, 10))
        editor_footer.addWidget(
            label(
                t(
                    "草稿自动保存；检查前会建立新版本。",
                    "Drafts save automatically. Running checks creates a version.",
                ),
                "Muted",
            )
        )
        editor_footer.addStretch()
        self.word_count = label("", "Muted")
        editor_footer.addWidget(self.word_count)
        layout.addLayout(editor_footer)
        self.tabs.addWidget(page)

    def build_map(self):
        t = self.tr2
        page = QWidget()
        layout = box(page, margins=(0, 23, 0, 16), spacing=14)
        heading = box(horizontal=True)
        heading.addWidget(label(t("看见故事之间的联系。", "See how your story connects."), "SectionTitle"))
        heading.addStretch()
        self.map_count = label("", "Pill")
        heading.addWidget(self.map_count)
        layout.addLayout(heading)
        layout.addWidget(
            label(
                t(
                    "每条连线对应一处待核对的前后变化。点击章节节点定位稿件。",
                    "Each connection represents a change to review. Click a chapter node to jump to the manuscript.",
                ),
                "Muted",
                True,
            )
        )
        map_panel = panel("SoftPanel")
        map_layout = box(map_panel, margins=(15, 5, 15, 2))
        self.chapter_map = ChapterMap()
        self.chapter_map.chapterClicked.connect(self.jump_chapter)
        map_layout.addWidget(self.chapter_map)
        layout.addWidget(map_panel)
        layout.addWidget(label(t("有据可查的故事事实", "THE STORY FACT INDEX"), "Eyebrow"))
        self.fact_tree = QTreeWidget()
        self.fact_tree.setColumnCount(4)
        self.fact_tree.setHeaderLabels(
            [
                t("人物 / 物品", "Subject"),
                t("属性与状态", "Attribute / state"),
                t("章节", "Chapter"),
                t("原文证据", "Source evidence"),
            ]
        )
        self.fact_tree.setRootIsDecorated(True)
        self.fact_tree.setAlternatingRowColors(True)
        self.fact_tree.header().setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)
        self.fact_tree.setColumnWidth(0, 175)
        self.fact_tree.setColumnWidth(1, 220)
        self.fact_tree.setColumnWidth(2, 150)
        self.fact_tree.itemDoubleClicked.connect(
            lambda item: (
                self.jump_source(item.data(0, Qt.ItemDataRole.UserRole))
                if item.data(0, Qt.ItemDataRole.UserRole)
                else None
            )
        )
        layout.addWidget(self.fact_tree, 1)
        self.tabs.addWidget(page)

    def build_history(self):
        t = self.tr2
        page = QWidget()
        layout = box(page, margins=(0, 26, 0, 20), spacing=17)
        layout.addWidget(
            label(t("每一次修改，都能回头看。", "Every revision has a way back."), "SectionTitle")
        )
        layout.addWidget(
            label(
                t(
                    "保存或检查时保留上一版。恢复会生成新版本，不会删除后来的记录。",
                    "Saving or checking preserves the previous version. Restoring creates a new version and keeps your later history.",
                ),
                "Muted",
                True,
            )
        )
        self.history_tree = QTreeWidget()
        self.history_tree.setRootIsDecorated(False)
        self.history_tree.setColumnCount(3)
        self.history_tree.setHeaderLabels(
            [t("版本", "Version"), t("保存时间", "Saved"), t("字符数", "Characters")]
        )
        self.history_tree.header().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.history_tree.currentItemChanged.connect(
            lambda: self.restore_btn.setEnabled(bool(self.history_tree.currentItem()) and self.worker is None)
        )
        layout.addWidget(self.history_tree, 1)
        line = box(horizontal=True)
        line.addWidget(
            label(t("当前稿件和草稿仍保存在本机。", "Manuscripts and drafts remain on this device."), "Muted")
        )
        line.addStretch()
        self.restore_btn = button(
            t("恢复所选版本", "Restore selected version"), self.restore_version, glyph="history"
        )
        self.restore_btn.setEnabled(False)
        line.addWidget(self.restore_btn)
        layout.addLayout(line)
        self.tabs.addWidget(page)

    def render_home(self):
        t = self.tr2
        clear(self.home_layout)
        hero = box(horizontal=True, spacing=32)
        copy = box(spacing=17)
        copy.addWidget(label("THE NEXT DRAFT STARTS HERE", "Eyebrow"))
        copy.addWidget(
            label(
                t("别让一个漏洞，\n辜负整个故事。", "A brilliant story.\nNo loose ends."), "HeroTitle", True
            )
        )
        copy.addWidget(
            label(
                t(
                    "人物记得住，线索接得上。\n把前后矛盾留在草稿里，把好故事交给读者。",
                    "Keep your characters true and your clues connected.\nCatch the contradictions while the story is still yours.",
                ),
                "Subhead",
                True,
            )
        )
        actions = box(horizontal=True)
        actions.addWidget(
            button(t("导入你的故事", "Bring your story"), self.import_dialog, "Primary", "import")
        )
        actions.addWidget(button(t("先看示例", "Explore a sample"), self.sample, glyph="arrow"))
        actions.addStretch()
        copy.addLayout(actions)
        copy.addWidget(
            label(
                t(
                    "TXT / Markdown / DOCX   ·   无需注册   ·   本机保存",
                    "TXT / Markdown / DOCX   ·   No account   ·   Local storage",
                ),
                "Muted",
                True,
            )
        )
        hero.addLayout(copy, 6)
        hero.addWidget(StoryArt(), 5)
        self.home_layout.addLayout(hero)
        guide = panel("SoftPanel")
        guide_layout = box(guide, horizontal=True, margins=(22, 18, 22, 18), spacing=28)
        for index, (zh, en, zhbody, enbody) in enumerate(
            (
                ("放入稿件", "Bring a draft", "保留章节与原文位置", "Keep chapters and source positions"),
                (
                    "找到疑点",
                    "Follow the evidence",
                    "前后两处原文一起看",
                    "Compare the two original passages",
                ),
                ("由你定稿", "Make the final call", "确认、解释，然后修订", "Confirm, explain and revise"),
            )
        ):
            step = box(spacing=5)
            step.addWidget(label(f"0{index + 1}   " + t(zh, en), "SourceTitle"))
            step.addWidget(label(t(zhbody, enbody), "Muted", True))
            guide_layout.addLayout(step, 1)
        self.home_layout.addWidget(guide)
        recent = box(horizontal=True)
        recent.addWidget(label(t("继续你的故事", "Back to your stories"), "SectionTitle"))
        recent.addStretch()
        recent.addWidget(button(t("已归档", "Archived"), self.show_archived, "Subtle", "archive"))
        self.home_layout.addLayout(recent)
        projects = self.store.list()
        if not projects:
            empty = panel()
            content = box(empty, margins=(24, 25, 24, 25))
            content.addWidget(
                label(t("你的第一份稿件，即将出现在这里。", "Your first manuscript belongs here."), "Subhead")
            )
            self.home_layout.addWidget(empty)
        for doc in projects[:6]:
            card = panel()
            row = box(card, horizontal=True, margins=(21, 18, 21, 18), spacing=15)
            book = label("", "Pill")
            book.setPixmap(icon("book", "#58734a", 28).pixmap(28, 28))
            row.addWidget(book)
            description = box(spacing=5)
            title = label(doc["title"])
            title.setStyleSheet("font-size:16px;font-weight:600;")
            description.addWidget(title)
            description.addWidget(
                label(
                    t(
                        f"{doc['characters']:,} 字符  ·  版本 {doc['revision']}  ·  {doc['findings']} 处疑点",
                        f"{doc['characters']:,} characters  ·  Revision {doc['revision']}  ·  {doc['findings']} findings",
                    ),
                    "Muted",
                )
            )
            row.addLayout(description, 1)
            row.addWidget(
                button(
                    t("继续审阅", "Continue"),
                    lambda checked=False, ident=doc["id"]: self.open_project(ident),
                    glyph="arrow",
                )
            )
            self.home_layout.addWidget(card)
        self.home_layout.addStretch()

    def notify(self, message, error=False):
        self.toast_label.setText(self.localize(str(message)))
        self.toast.setProperty("error", error)
        self.toast.style().unpolish(self.toast)
        self.toast.style().polish(self.toast)
        self.toast.show()
        if not error:
            message_text = self.toast_label.text()
            QTimer.singleShot(
                6000, lambda: self.toast.hide() if self.toast_label.text() == message_text else None
            )

    def guard(self, function):
        try:
            return function()
        except Exception as exc:
            self.notify(str(exc), True)
            return None

    def refresh_projects(self):
        self.projects.blockSignals(True)
        self.projects.clear()
        for doc in self.store.list():
            item = QListWidgetItem(icon("book", "#819c7d", 17), doc["title"])
            item.setData(Qt.ItemDataRole.UserRole, doc["id"])
            item.setToolTip(doc["title"])
            item.setSizeHint(QSize(175, 43))
            self.projects.addItem(item)
            if self.doc and doc["id"] == self.doc["id"]:
                item.setSelected(True)
        self.projects.blockSignals(False)
        if self.store.warnings:
            self.notify(
                self.tr2(
                    "部分项目文件无法读取，原文件已保留。请从版本备份恢复。",
                    "Some project files could not be read. Originals are preserved; recover them from version backups.",
                ),
                True,
            )
        self.render_home()

    def show_library(self):
        if self.worker or not self.flush_all():
            return
        self.render_home()
        self.pages.setCurrentIndex(0)
        self.breadcrumb.setText(self.tr2("工作空间  /  我的书架", "WORKSPACE  /  YOUR LIBRARY"))

    def open_project(self, ident):
        if self.worker or not self.flush_all():
            return
        doc = self.guard(lambda: self.store.read(ident))
        if doc:
            self.load_document(doc)

    def load_document(self, doc):
        self.draft_timer.stop()
        self.note_timer.stop()
        self.note_owner = None
        self.doc = doc
        self.selected_id = ""
        self.search.blockSignals(True)
        self.search.clear()
        self.search.blockSignals(False)
        self.category.blockSignals(True)
        self.category.setCurrentIndex(0)
        self.category.blockSignals(False)
        self.filter_status = "pending"
        self.editor.blockSignals(True)
        self.editor.setPlainText((doc.get("draft") or {}).get("text", doc["text"]))
        self.editor.blockSignals(False)
        self.document_title.setText(doc["title"])
        self.setWindowTitle(f"{doc['title']} — PlotProof")
        self.breadcrumb.setText(self.tr2("工作空间  /  稿件审阅", "WORKSPACE  /  MANUSCRIPT REVIEW"))
        self.pages.setCurrentIndex(1)
        self.preferences.set(last_project=doc["id"])
        self.refresh_document()
        self.set_tab(0 if doc.get("report") else 1)
        if doc.get("draft"):
            self.notify(
                self.tr2(
                    "已恢复上次自动保存的草稿。检查前将保存为新版本。",
                    "Recovered your autosaved draft. Running checks will create a new version.",
                )
            )

    def refresh_document(self):
        if not self.doc:
            return
        report = self.doc.get("report")
        self.revision_tag.setText(f"R{self.doc['revision']:02d}")
        chapters = (
            (report or {})
            .get("stats", {})
            .get("chapters", len({p.chapter_index for p in parse(self.doc["text"])}))
        )
        self.document_meta.setText(
            self.tr2(
                f"{chapters} 章  ·  {len(self.doc['text']):,} 字符  ·  修改、核对、再打磨",
                f"{chapters} chapters  ·  {len(self.doc['text']):,} characters  ·  Revise, review, refine",
            )
        )
        self.update_outline()
        self.render_findings()
        self.render_map()
        self.render_history()
        self.update_stale()

    def is_stale(self):
        if not self.doc:
            return False
        report = self.doc.get("report")
        return bool(
            report
            and (
                report.get("revision") != self.doc["revision"]
                or self.editor.toPlainText() != self.doc["text"]
            )
        )

    def update_stale(self):
        stale = self.is_stale()
        self.stale_label.setVisible(stale)
        self.export_btn.setEnabled(
            bool(self.doc and self.doc.get("report")) and not stale and not self.worker
        )
        for widget in getattr(self, "decision_buttons", []):
            widget.setEnabled(not stale and not self.worker)
        if getattr(self, "note_edit", None) is not None:
            self.note_edit.setReadOnly(stale or bool(self.worker))

    def set_tab(self, index):
        if not self.flush_note():
            return
        self.tabs.setCurrentIndex(index)
        self.tab_buttons[index].setChecked(True)
        if self.doc:
            self.pages.setCurrentIndex(1)
        if index == 3 and self.doc:
            self.render_history()
        if index == 2 and self.doc:
            self.chapter_map.setReport(self.doc.get("report"), self.selected_id)

    def set_filter(self, status):
        if not self.flush_note():
            return
        self.filter_status = status
        self.render_findings()

    def render_findings(self):
        if not self.doc or self._rendering:
            return
        if not self.flush_note():
            return
        self._rendering = True
        report = self.doc.get("report") or {}
        findings = report.get("findings", [])
        titles = {
            "pending": self.tr2("待核对", "To review"),
            "confirmed": self.tr2("已确认", "Confirmed"),
            "dismissed": self.tr2("已有解释", "Explained"),
            "all": self.tr2("全部", "All"),
        }
        for key, control in self.status_buttons.items():
            number = len(findings) if key == "all" else sum(f["status"] == key for f in findings)
            control.setText(f"{titles[key]}  {number:02d}")
            control.setChecked(key == self.filter_status)
        query = self.search.text().strip().casefold()
        category = self.category.currentData()
        visible = [
            f
            for f in findings
            if (self.filter_status == "all" or f["status"] == self.filter_status)
            and (category == "all" or f["category"] == category)
            and (not query or query in (f["subject"] + f["title"] + f["reason"]).casefold())
        ]
        self.findings.blockSignals(True)
        self.findings.clear()
        selected_row = 0
        for index, finding in enumerate(visible):
            item = QListWidgetItem()
            item.setData(Qt.ItemDataRole.UserRole, finding["id"])
            title = self.finding_title(finding)
            item.setData(Qt.ItemDataRole.AccessibleTextRole, title)
            card = FindingCard(
                finding, self.categories()[finding["category"]], title, titles[finding["status"]], index + 1
            )
            item.setSizeHint(QSize(250, 130))
            self.findings.addItem(item)
            self.findings.setItemWidget(item, card)
            if finding["id"] == self.selected_id:
                selected_row = index
        self.findings.blockSignals(False)
        self.findings_count.setText(self.tr2(f"{len(visible):02d} 处疑点", f"{len(visible):02d} FINDINGS"))
        self._rendering = False
        if visible:
            self.findings.setCurrentRow(selected_row)
        else:
            self.render_detail(None)
        mode = (
            self.tr2("离线规则", "Offline rules")
            if report.get("provider", {}).get("provider") == "rules"
            else report.get("provider", {}).get("model", "")
        )
        count = report.get("stats", {}).get("facts", 0)
        self.coverage.setText(
            self.tr2(
                f"{mode}  ·  {count} 条事实  ·  引文存在 ≠ 判断必然正确。最终由作者决定。",
                f"{mode}  ·  {count} facts  ·  A verified quote is not a verified interpretation. You make the final call.",
            )
            if report
            else self.tr2(
                "先检查稿件，建立有原文依据的事实索引。", "Run a review to build a source-backed fact index."
            )
        )
        self.coverage.setToolTip("\n".join(self.localize(w) for w in report.get("warnings", [])))
        self.update_stale()

    def finding_title(self, finding):
        value = self.localize(finding["title"])
        if finding["subject"] not in value:
            value = finding["subject"] + " · " + value
        return value

    def select_finding(self, item, previous=None):
        if self._rendering:
            return
        if not self.flush_note():
            return
        ident = item.data(Qt.ItemDataRole.UserRole) if item else None
        finding = (
            next((f for f in (self.doc.get("report") or {}).get("findings", []) if f["id"] == ident), None)
            if self.doc
            else None
        )
        self.selected_id = ident or ""
        self.render_detail(finding)

    def render_detail(self, finding):
        self.note_timer.stop()
        self.note_owner = None
        self.note_edit = None
        self.decision_buttons = []
        clear(self.detail_layout)
        t = self.tr2
        if not finding:
            self.detail_layout.addStretch()
            self.detail_layout.addWidget(
                label(t("让故事，经得起前后推敲。", "Give your story a second look."), "PageTitle", True)
            )
            has_report = bool(self.doc and self.doc.get("report"))
            self.detail_layout.addWidget(
                label(
                    t(
                        "当前筛选下没有待审阅疑点。可以切换筛选，或继续修订稿件。",
                        "No findings match this view. Change the filters, or keep refining your manuscript.",
                    )
                    if has_report
                    else t(
                        "点击“检查故事”，从原文提取事实、对照前后变化。",
                        "Choose Check story to extract facts and compare changes across your manuscript.",
                    ),
                    "Subhead",
                    True,
                )
            )
            if has_report and not self.doc["report"]["findings"]:
                self.detail_layout.addWidget(
                    label(
                        t(
                            "没有发现疑点不代表没有矛盾。离线规则的覆盖范围有限。",
                            "No findings does not prove consistency. Offline rules have limited coverage.",
                        ),
                        "Muted",
                        True,
                    )
                )
            self.detail_layout.addStretch()
            return
        heading = box(horizontal=True)
        heading.addWidget(label(t("证据对照", "EVIDENCE COMPARISON"), "Eyebrow"))
        heading.addStretch()
        heading.addWidget(
            label(
                t("等待作者判断", "AUTHOR REVIEW")
                if finding["status"] == "pending"
                else t("审阅结论已保存", "DECISION SAVED"),
                "Pill",
            )
        )
        self.detail_layout.addLayout(heading)
        self.detail_layout.addWidget(label(self.finding_title(finding), "PageTitle", True))
        reason = panel("NotePanel")
        reason_layout = box(reason, margins=(16, 12, 16, 12), spacing=6)
        reason_layout.addWidget(label(t("这处变化值得核对", "A CHANGE WORTH CHECKING"), "Eyebrow"))
        reason_layout.addWidget(label(self.localize(finding["reason"]), wrap=True))
        self.detail_layout.addWidget(reason)
        pair = box(horizontal=True, spacing=13)
        for later, side in enumerate(("before", "after")):
            card = EvidenceCard(finding[side], later, t)
            card.openSource.connect(self.jump_source)
            pair.addWidget(card, 1)
        self.detail_layout.addLayout(pair)
        review_heading = box(horizontal=True)
        review_heading.addWidget(
            label(t("这是漏洞，还是你的安排？", "A plot hole, or part of the plan?"), "SectionTitle")
        )
        self.detail_layout.addLayout(review_heading)
        self.note_edit = QPlainTextEdit()
        self.note_edit.setPlaceholderText(
            t(
                "写下解释或修改方向。备注会自动保存。",
                "Leave an explanation or a possible fix. Notes save automatically.",
            )
        )
        self.note_edit.setFixedHeight(70)
        self.note_edit.setPlainText(finding["note"])
        self.note_owner = (self.doc["id"], finding["id"], self.doc["revision"])
        self.note_edit.textChanged.connect(lambda: self.note_timer.start())
        self.detail_layout.addWidget(self.note_edit)
        actions = box(horizontal=True, spacing=9)
        confirm = button(
            t("确认是问题", "Confirm issue"), lambda: self.decide("confirmed"), "Primary", "check"
        )
        dismiss = button(t("已有解释", "Explained"), lambda: self.decide("dismissed"), glyph="check")
        actions.addWidget(confirm)
        actions.addWidget(dismiss)
        self.decision_buttons.extend((confirm, dismiss))
        if finding["status"] != "pending":
            reopen = button(t("重新待审", "Reopen"), lambda: self.decide("pending"), "Subtle", "history")
            actions.addWidget(reopen)
            self.decision_buttons.append(reopen)
        actions.addStretch()
        self.detail_layout.addLayout(actions)
        self.detail_layout.addWidget(
            label(
                t(
                    "回忆、谎言、化名和明确的状态变化，都可能是合理解释。",
                    "Flashbacks, lies, aliases and explicit changes can explain a difference.",
                ),
                "Muted",
                True,
            )
        )
        self.detail_layout.addStretch()
        self.update_stale()

    def flush_note(self):
        if not self.note_owner or getattr(self, "note_edit", None) is None or not self.doc:
            return True
        self.note_timer.stop()
        ident, finding_id, revision = self.note_owner
        note = self.note_edit.toPlainText()
        finding = next(
            (f for f in (self.doc.get("report") or {}).get("findings", []) if f["id"] == finding_id), None
        )
        if not finding or note == finding["note"]:
            return True
        if len(note) > 2000:
            self.notify(
                self.tr2(
                    "备注最多 2,000 字符，请缩短后保存。",
                    "Notes are limited to 2,000 characters. Shorten this note before saving.",
                ),
                True,
            )
            return False
        try:
            self.doc = self.store.review(ident, finding_id, finding["status"], note, revision)
            self.save_status.setText(self.tr2("●  备注已自动保存", "●  Note saved automatically"))
            return True
        except Exception as exc:
            self.notify(str(exc), True)
            return False

    def decide(self, status):
        if not self.doc or self.is_stale() or self.worker or not self.flush_note():
            return
        doc = self.guard(
            lambda: self.store.review(
                self.doc["id"], self.selected_id, status, self.note_edit.toPlainText(), self.doc["revision"]
            )
        )
        if doc:
            self.doc = doc
            self.note_owner = None
            self.render_findings()
            self.save_status.setText(self.tr2("●  审阅结论已保存", "●  Review decision saved"))

    def move_finding(self, offset):
        if self.doc and self.findings.count():
            self.set_tab(0)
            row = max(0, min(self.findings.count() - 1, self.findings.currentRow() + offset))
            self.findings.setCurrentRow(row)

    def on_edit(self):
        if not self.doc:
            return
        count = len(self.editor.toPlainText())
        self.word_count.setText(f"{count:,} / 300,000")
        self.save_status.setText(self.tr2("正在保存草稿…", "Saving draft…"))
        self.draft_timer.start()
        self.update_stale()

    def flush_draft(self):
        self.draft_timer.stop()
        if not self.doc:
            return True
        text = self.editor.toPlainText()
        existing = (self.doc.get("draft") or {}).get("text", self.doc["text"])
        if text == existing:
            return True
        try:
            self.doc = self.store.save_draft(self.doc["id"], text, self.doc["revision"])
            self.save_status.setText(self.tr2("●  草稿已自动保存", "●  Draft saved automatically"))
            self.update_outline()
            return True
        except Exception as exc:
            self.notify(str(exc), True)
            return False

    def flush_all(self):
        return self.flush_note() and self.flush_draft()

    def commit_editor(self):
        if self.worker or not self.doc or not self.flush_all():
            return False
        doc = self.guard(
            lambda: self.store.update(self.doc["id"], self.editor.toPlainText(), self.doc["revision"])
        )
        if not doc:
            return False
        self.doc = doc
        self.note_owner = None
        self.refresh_document()
        self.refresh_projects()
        self.save_status.setText(
            self.tr2(f"●  已保存为版本 {doc['revision']}", f"●  Saved revision {doc['revision']}")
        )
        return True

    def update_outline(self):
        text = self.editor.toPlainText()
        self.word_count.setText(f"{len(text):,} / 300,000")
        self.outline.clear()
        try:
            paragraphs = parse(text)
        except ValueError:
            return
        seen = set()
        for paragraph in paragraphs:
            if paragraph.chapter_index not in seen:
                item = QListWidgetItem(paragraph.chapter)
                item.setData(Qt.ItemDataRole.UserRole, paragraph.start)
                item.setToolTip(paragraph.chapter)
                self.outline.addItem(item)
                seen.add(paragraph.chapter_index)

    def jump_outline(self, item):
        cursor = self.editor.textCursor()
        cursor.setPosition(qt_offset(self.editor.toPlainText(), item.data(Qt.ItemDataRole.UserRole)))
        self.editor.setTextCursor(cursor)
        self.editor.centerCursor()
        self.editor.setFocus()

    def jump_chapter(self, chapter):
        if self.doc:
            paragraph = next(
                (
                    p
                    for p in (self.doc.get("report") or {}).get("paragraphs", [])
                    if p["chapter_index"] == chapter
                ),
                None,
            )
            if paragraph:
                self.jump_source(paragraph["id"])

    def jump_source(self, paragraph_id):
        if not self.doc or not paragraph_id:
            return
        report = self.doc.get("report") or {}
        paragraph = next((p for p in report.get("paragraphs", []) if p["id"] == paragraph_id), None)
        if not paragraph:
            return
        if self.is_stale():
            dialog = QDialog(self)
            dialog.setWindowTitle(self.tr2("上次检查的原文快照", "Previous source snapshot"))
            dialog.resize(700, 450)
            layout = box(dialog, margins=(25, 25, 25, 25))
            layout.addWidget(label(paragraph["chapter"], "SectionTitle"))
            read = QPlainTextEdit(paragraph["text"])
            read.setReadOnly(True)
            layout.addWidget(read, 1)
            layout.addWidget(
                label(
                    self.tr2(
                        "稿件已变化。重新检查后可以定位当前原文。",
                        "The manuscript changed. Run checks to navigate the current source.",
                    ),
                    "Muted",
                    True,
                )
            )
            layout.addWidget(button(self.tr2("关闭", "Close"), dialog.accept))
            dialog.exec()
            return
        self.set_tab(1)
        start, end = paragraph["start"], paragraph["end"]
        finding = next((f for f in report.get("findings", []) if f["id"] == self.selected_id), None)
        if finding:
            evidence = next(
                (
                    finding[side]
                    for side in ("before", "after")
                    if finding[side]["paragraph_id"] == paragraph_id
                ),
                None,
            )
            if evidence:
                start, end = evidence["start"], evidence["end"]
        cursor = self.editor.textCursor()
        cursor.setPosition(qt_offset(self.doc["text"], start))
        cursor.setPosition(qt_offset(self.doc["text"], end), QTextCursor.MoveMode.KeepAnchor)
        self.editor.setTextCursor(cursor)
        self.editor.centerCursor()
        self.editor.setFocus()

    def focus_search(self):
        target = self.editor_search if self.tabs.currentIndex() == 1 else self.search
        target.setFocus()
        target.selectAll()

    def find_in_editor(self):
        value = self.editor_search.text()
        if value and not self.editor.find(value):
            cursor = self.editor.textCursor()
            cursor.movePosition(QTextCursor.MoveOperation.Start)
            self.editor.setTextCursor(cursor)
            if not self.editor.find(value):
                self.notify(self.tr2("稿件中未找到这段文字。", "This text was not found in the manuscript."))

    def start_analysis(self, settings_override=None):
        if self.worker or not self.doc or not self.commit_editor():
            return
        self.toast.hide()
        ident, text, revision = self.doc["id"], self.doc["text"], self.doc["revision"]
        from ..providers import Settings

        selected_model = settings_override if isinstance(settings_override, Settings) else self.model
        settings = Settings(**vars(selected_model))
        settings.language = self.lang

        def review(progress, cancel):
            report = analyze(
                text, settings, progress=progress, cancel=cancel, cache_dir=self.store.root / "cache"
            )
            if cancel.is_set():
                from ..engine import Cancelled

                raise Cancelled()
            return self.store.save_report(ident, report, revision)

        self.worker = Worker(review, self)
        self.worker.progress.connect(self.analysis_progress)
        self.worker.result.connect(self.analysis_result)
        self.worker.failed.connect(
            lambda message: self.notify(
                self.tr2("检查未完成：", "Review did not finish: ") + self.localize(message), True
            )
        )
        self.worker.cancelled.connect(
            lambda: self.notify(
                self.tr2(
                    "检查已取消，之前的结果仍然保留。", "Review cancelled. Your previous report is preserved."
                )
            )
        )
        self.worker.finished.connect(self.worker_finished)
        self.set_busy(True)
        self.set_tab(0)
        self.job_label.setText(self.tr2("开始建立事实索引…", "Building the fact index…"))
        self.worker.start()

    def analysis_progress(self, value):
        total = max(1, value["total"])
        self.progress.setRange(0, total)
        self.progress.setValue(value["current"])
        text = (
            self.tr2("提取原文事实", "Extracting source facts")
            if value["stage"] == "extract"
            else self.tr2("复核前后变化", "Reviewing changes")
        )
        if self.worker and self.worker.cancel.is_set():
            text = self.tr2("等待当前模型请求结束后取消", "Cancelling after the current request")
        self.job_label.setText(f"{text}   ·   {value['current']} / {value['total']}")

    def analysis_result(self, doc):
        self.doc = doc
        self.note_owner = None
        self.selected_id = ""
        self.filter_status = "pending"
        self.refresh_document()
        self.refresh_projects()
        self.set_tab(0)
        self.notify(
            self.tr2(
                f"检查完成。发现 {len(doc['report']['findings'])} 处待核对变化。",
                f"Review complete. {len(doc['report']['findings'])} changes to examine.",
            )
        )
        self.analysisCompleted.emit(doc)

    def worker_finished(self):
        self.worker.deleteLater()
        self.worker = None
        self.set_busy(False)
        self.update_stale()
        if self.pending_close:
            QTimer.singleShot(0, self.close)

    def set_busy(self, busy):
        for widget in (
            self.run_btn,
            self.import_btn,
            self.library_btn,
            self.new_btn,
            self.sample_btn,
            self.model_btn,
            self.lang_button,
            self.projects,
            self.save_btn,
            self.restore_btn,
        ):
            widget.setEnabled(not busy)
        self.editor.setReadOnly(busy)
        self.progress.setVisible(busy)
        self.job_line.setVisible(busy)
        self.cancel_btn.setEnabled(busy)
        self.export_btn.setEnabled(
            not busy and bool(self.doc and self.doc.get("report")) and not self.is_stale()
        )
        self.update_stale()

    def cancel_analysis(self):
        if self.worker:
            self.worker.cancel.set()
            self.cancel_btn.setEnabled(False)
            self.job_label.setText(
                self.tr2(
                    "正在取消；当前请求可能需要等待超时。",
                    "Cancelling; an in-flight request may need to time out.",
                )
            )

    def render_map(self):
        report = (self.doc or {}).get("report") or {}
        self.chapter_map.setReport(report, self.selected_id)
        facts = report.get("facts", [])
        subjects = {}
        self.fact_tree.clear()
        for fact in facts:
            subject = fact["subject"]
            if subject not in subjects:
                parent = QTreeWidgetItem([subject, self.categories().get(fact["category"], ""), "", ""])
                self.fact_tree.addTopLevelItem(parent)
                subjects[subject] = parent
            from ..rules import LABELS

            attribute = self.localize(LABELS.get(fact["attribute"], fact["attribute"]))
            evidence = fact["evidence"]
            child = QTreeWidgetItem(
                [
                    "",
                    attribute
                    + " · "
                    + self.tr2(STATE_LABELS.get(fact["value"], fact["value"]), fact["value"]),
                    evidence["chapter"],
                    fact["quote"],
                ]
            )
            child.setData(0, Qt.ItemDataRole.UserRole, fact["paragraph_id"])
            child.setToolTip(3, evidence["context"])
            subjects[subject].addChild(child)
        self.fact_tree.expandAll()
        self.map_count.setText(
            self.tr2(
                f"{len(subjects)} 个主体  ·  {len(facts)} 条事实",
                f"{len(subjects)} subjects  ·  {len(facts)} facts",
            )
        )

    def render_history(self):
        self.history_tree.clear()
        self.restore_btn.setEnabled(False)
        if not self.doc:
            return
        for version in self.store.history(self.doc["id"]):
            try:
                time = datetime.fromisoformat(version["updated_at"]).astimezone().strftime("%Y-%m-%d  %H:%M")
            except ValueError:
                time = version["updated_at"]
            item = QTreeWidgetItem([f"R{version['revision']:02d}", time, f"{version['characters']:,}"])
            item.setData(0, Qt.ItemDataRole.UserRole, version["revision"])
            self.history_tree.addTopLevelItem(item)

    def restore_version(self):
        item = self.history_tree.currentItem()
        if not item or not self.doc or self.worker:
            return
        revision = item.data(0, Qt.ItemDataRole.UserRole)
        answer = QMessageBox.question(
            self,
            self.tr2("恢复版本", "Restore version"),
            self.tr2(
                f"将 R{revision:02d} 恢复为新版本？当前草稿会先保存。",
                f"Restore R{revision:02d} as a new version? Your current draft will be saved first.",
            ),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if answer != QMessageBox.StandardButton.Yes or not self.commit_editor():
            return
        doc = self.guard(lambda: self.store.restore(self.doc["id"], revision, self.doc["revision"]))
        if doc:
            self.load_document(doc)
            self.set_tab(1)
            self.notify(
                self.tr2(
                    "版本已恢复。重新检查以更新证据。", "Version restored. Run checks to update the evidence."
                )
            )

    def sample(self):
        if self.worker or not self.flush_all():
            return
        text = (Path(__file__).parents[1] / "examples" / f"{self.lang}.txt").read_text(encoding="utf-8")
        title = self.tr2("雾港来信 · 示例", "Letters from the Harbor · Sample")
        doc = self.guard(lambda: self.store.create(title, text))
        if doc:
            self.load_document(doc)
            self.refresh_projects()
            from ..providers import Settings

            self.start_analysis(Settings(language=self.lang))

    def new_project(self):
        if self.worker or not self.flush_all():
            return
        dialog = NewManuscript(self, self.tr2)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            doc = self.guard(lambda: self.store.create(dialog.title.text(), dialog.text.toPlainText()))
            if doc:
                self.load_document(doc)
                self.refresh_projects()
                self.set_tab(1)

    def import_dialog(self):
        if self.worker:
            return
        path, _ = QFileDialog.getOpenFileName(
            self, self.tr2("导入稿件", "Import manuscript"), "", "Manuscripts (*.txt *.md *.markdown *.docx)"
        )
        if path:
            self.import_path(Path(path))

    def import_path(self, path):
        if self.worker or not self.flush_all():
            return
        result = self.guard(lambda: read_manuscript(Path(path)))
        if result:
            text, encoding = result
            doc = self.guard(lambda: self.store.create(Path(path).stem[:150], text))
            if doc:
                self.load_document(doc)
                self.refresh_projects()
                self.set_tab(1)
                self.notify(
                    self.tr2(
                        f"已导入 {Path(path).name}。来源文件保持原样。",
                        f"Imported {Path(path).name}. Your original file is unchanged.",
                    )
                    + f"  ·  {encoding}"
                )

    def dragEnterEvent(self, event):
        if (
            not self.worker
            and event.mimeData().hasUrls()
            and any(
                Path(url.toLocalFile()).suffix.lower() in {".txt", ".md", ".markdown", ".docx"}
                for url in event.mimeData().urls()
            )
        ):
            event.acceptProposedAction()

    def dropEvent(self, event):
        paths = [Path(url.toLocalFile()) for url in event.mimeData().urls() if url.isLocalFile()]
        if paths and not self.worker:
            self.import_path(paths[0])
            event.acceptProposedAction()

    def configure(self):
        if self.worker:
            return
        dialog = ModelDialog(self, self.model, self.tr2)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.model = dialog.settings()
            self.preferences.save_model(self.model)
            self.update_engine_status()
            self.notify(self.tr2("检查方式已更新。", "Review engine updated."))

    def update_engine_status(self):
        value = (
            self.tr2("离线规则 · 无需模型", "Offline rules · No model required")
            if self.model.provider == "rules"
            else self.model.model
        )
        self.engine_status.setText(value + "   ·   " + self.tr2("本机工作台", "Native desktop"))

    def export_dialog(self):
        if not self.doc or not self.doc.get("report") or self.worker or not self.flush_all():
            return
        if self.is_stale():
            self.notify(
                self.tr2(
                    "请先检查当前稿件，再导出最新报告。",
                    "Run checks on the current manuscript before exporting.",
                ),
                True,
            )
            return
        path, format = QFileDialog.getSaveFileName(
            self,
            self.tr2("导出审阅报告", "Export review report"),
            "PlotProof-report.pdf",
            "PDF (*.pdf);;HTML (*.html);;JSON (*.json)",
        )
        if path:
            extension = (
                ".pdf" if format.startswith("PDF") else ".html" if format.startswith("HTML") else ".json"
            )
            destination = Path(path)
            if destination.suffix.lower() != extension:
                destination = Path(str(destination) + extension)
            self.guard(lambda: self.export_to(destination))

    def export_to(self, path):
        if not self.doc or not self.doc.get("report") or self.is_stale():
            raise ValueError("Analyze the current manuscript before exporting.")
        path = Path(path)
        if path.suffix.lower() == ".pdf":
            from .reports import export_pdf

            export_pdf(self.doc, path, self.lang)
        else:
            content = json_report(self.doc) if path.suffix.lower() == ".json" else html_report(self.doc)
            temp = path.with_suffix(path.suffix + ".tmp")
            temp.write_text(content, encoding="utf-8")
            temp.replace(path)
        self.notify(self.tr2("报告已导出：", "Report exported: ") + str(path))
        return path

    def project_menu(self, position):
        item = self.projects.itemAt(position)
        if not item or self.worker:
            return
        ident = item.data(Qt.ItemDataRole.UserRole)
        menu = QMenu(self)
        rename = menu.addAction(self.tr2("重命名", "Rename"))
        archive = menu.addAction(self.tr2("移至归档", "Archive"))
        chosen = menu.exec(self.projects.mapToGlobal(position))
        if chosen == rename:
            title, ok = QInputDialog.getText(
                self, self.tr2("重命名稿件", "Rename manuscript"), self.tr2("名称", "Title"), text=item.text()
            )
            if ok:
                doc = self.guard(lambda: self.store.rename(ident, title))
                if doc and self.doc and self.doc["id"] == ident:
                    self.doc["title"] = doc["title"]
                    self.document_title.setText(doc["title"])
                    self.setWindowTitle(doc["title"] + " — PlotProof")
        elif chosen == archive and self.flush_all():
            self.guard(lambda: self.store.archive(ident))
            if self.doc and self.doc["id"] == ident:
                self.doc = None
                self.note_owner = None
                self.pages.setCurrentIndex(0)
        self.refresh_projects()

    def show_archived(self):
        dialog = QDialog(self)
        dialog.setWindowTitle(self.tr2("已归档的稿件", "Archived manuscripts"))
        dialog.resize(560, 400)
        layout = box(dialog, margins=(24, 24, 24, 24))
        layout.addWidget(
            label(
                self.tr2("故事还在，随时可以继续。", "Your stories are here when you need them."),
                "SectionTitle",
                True,
            )
        )
        listing = QListWidget()
        for doc in self.store.list(archived=True):
            item = QListWidgetItem(doc["title"])
            item.setData(Qt.ItemDataRole.UserRole, doc["id"])
            listing.addItem(item)
        layout.addWidget(listing, 1)

        def restore():
            if listing.currentItem():
                ident = listing.currentItem().data(Qt.ItemDataRole.UserRole)
                self.store.archive(ident, False)
                dialog.accept()
                self.refresh_projects()

        layout.addWidget(button(self.tr2("放回书架", "Return to library"), restore, "Primary"))
        layout.addWidget(button(self.tr2("关闭", "Close"), dialog.reject))
        dialog.exec()

    def switch_language(self):
        if self.worker or not self.flush_all():
            return
        doc = self.doc
        index = self.tabs.currentIndex()
        was_home = self.pages.currentIndex() == 0
        self.note_owner = None
        self.note_edit = None
        self.lang = "en" if self.lang == "zh" else "zh"
        self.model.language = self.lang
        self.preferences.set(language=self.lang)
        self.build_ui()
        self.refresh_projects()
        if doc:
            self.load_document(self.store.read(doc["id"]))
            self.set_tab(index)
        if was_home:
            self.pages.setCurrentIndex(0)

    def about(self):
        dialog = QDialog(self)
        dialog.setWindowTitle("PlotProof · " + self.tr2("关于与快捷键", "About & shortcuts"))
        dialog.resize(610, 490)
        layout = box(dialog, margins=(30, 28, 30, 25), spacing=15)
        layout.addWidget(label("PlotProof  " + __version__, "PageTitle"))
        layout.addWidget(
            label(
                self.tr2("让故事的每一条线，都有迹可循。", "Catch plot holes before your readers do."),
                "Subhead",
                True,
            )
        )
        text = self.tr2(
            "Ctrl+O  导入稿件\nCtrl+N  新建稿件\nCtrl+S  保存新版本\nCtrl+Enter  检查故事\nCtrl+F  搜索\nCtrl+1…4  切换工作区\nAlt+↑ / ↓  上一处 / 下一处疑点\nCtrl+Shift+E  导出报告",
            "Ctrl+O  Import manuscript\nCtrl+N  New manuscript\nCtrl+S  Save version\nCtrl+Enter  Check story\nCtrl+F  Search\nCtrl+1…4  Switch workspace\nAlt+↑ / ↓  Previous / next finding\nCtrl+Shift+E  Export report",
        )
        layout.addWidget(label(text, wrap=True))
        layout.addWidget(
            label(
                self.tr2(
                    "MIT 完全开源。原生桌面窗口，不启动浏览器。离线规则覆盖有限；模型检查需自行配置模型。引文核对不代表语义判断一定正确。",
                    "MIT open source. Native desktop window; no browser. Offline rules have limited coverage. Model review requires your own model. Source verification does not prove an interpretation correct.",
                ),
                "Muted",
                True,
            )
        )
        layout.addWidget(label(self.tr2("本机数据：", "Local data: ") + str(self.store.root), "Muted", True))
        layout.addWidget(button(self.tr2("继续写故事", "Back to the story"), dialog.accept, "Primary"))
        dialog.exec()

    def closeEvent(self, event):
        if not self.flush_all():
            event.ignore()
            return
        if self.worker and self.worker.isRunning():
            self.pending_close = True
            self.cancel_analysis()
            self.notify(
                self.tr2(
                    "正在结束检查，完成后窗口会自动关闭。稿件已经保存。",
                    "Finishing the current request before closing. Your manuscript is saved.",
                )
            )
            event.ignore()
            return
        self.preferences.set(language=self.lang)
        event.accept()
