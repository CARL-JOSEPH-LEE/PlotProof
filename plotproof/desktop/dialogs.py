import json
from urllib.request import Request, build_opener

from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QLineEdit,
    QMessageBox,
    QPlainTextEdit,
    QWidget,
)

from ..providers import NoRedirect, Settings
from .widgets import box, button, label, panel
from .worker import Worker


class NewManuscript(QDialog):
    def __init__(self, parent, tr):
        super().__init__(parent)
        self.setWindowTitle(tr("新建稿件", "New manuscript"))
        self.resize(720, 600)
        layout = box(self, margins=(28, 26, 28, 24), spacing=13)
        layout.addWidget(label(tr("一个故事，从这里开始。", "A story starts here."), "PageTitle"))
        layout.addWidget(
            label(
                tr(
                    "粘贴正文，或回到书架导入 TXT、Markdown、Word 文件。",
                    "Paste your manuscript, or import a TXT, Markdown or Word file from the library.",
                ),
                "Subhead",
                True,
            )
        )
        layout.addWidget(label(tr("稿件名称", "Title")))
        self.title = QLineEdit()
        self.title.setMaxLength(150)
        self.title.setPlaceholderText(tr("给故事起一个名字", "Give your story a name"))
        layout.addWidget(self.title)
        layout.addWidget(label(tr("正文", "Manuscript")))
        self.text = QPlainTextEdit()
        self.text.setPlaceholderText(tr("第一章\n\n在这里粘贴故事…", "Chapter 1\n\nPaste your story here…"))
        layout.addWidget(self.text, 1)
        footer = box(horizontal=True)
        footer.addWidget(label(tr("稿件只保存在本机", "Stored on this device"), "Muted"))
        footer.addStretch()
        footer.addWidget(button(tr("取消", "Cancel"), self.reject))
        self.create = button(tr("创建稿件", "Create manuscript"), self.accept, "Primary", "plus")
        self.create.setEnabled(False)
        footer.addWidget(self.create)
        layout.addLayout(footer)
        self.title.textChanged.connect(self.validate)
        self.text.textChanged.connect(self.validate)

    def validate(self):
        self.create.setEnabled(
            bool(self.title.text().strip()) and 0 < len(self.text.toPlainText().strip()) <= 300_000
        )


class ModelDialog(QDialog):
    def __init__(self, parent, settings, tr):
        super().__init__(parent)
        self.tr2, self.original, self.worker = tr, settings, None
        self.setWindowTitle(tr("检查方式与模型", "Review engine"))
        self.setMinimumWidth(600)
        self.setModal(True)
        layout = box(self, margins=(28, 26, 28, 24), spacing=14)
        layout.addWidget(
            label(tr("为你的故事，选择检查方式。", "Choose the lens for your story."), "SectionTitle")
        )
        self.mode = QComboBox()
        for title, value in (
            (tr("离线规则 · 开箱即用", "Offline rules · Ready to use"), "rules"),
            ("Ollama · " + tr("本机模型", "Local model"), "ollama"),
            (tr("兼容 Chat Completions 的模型服务", "Chat Completions compatible service"), "compatible"),
        ):
            self.mode.addItem(title, value)
        self.mode.setCurrentIndex(self.mode.findData(settings.provider))
        layout.addWidget(self.mode)
        self.offline = panel("SoftPanel")
        offline_layout = box(self.offline, margins=(20, 18, 20, 18), spacing=10)
        offline_layout.addWidget(
            label(tr("不联网，也能开始审阅。", "Start reviewing without a connection."), "SectionTitle")
        )
        offline_layout.addWidget(
            label(
                tr(
                    "检查明确陈述的瞳色、惯用手、血型、出生年份，以及部分物品与生死状态。带梦境、回忆或引号的段落会保守跳过。",
                    "Checks explicit eye color, handedness, blood type, birth year and some object/life states. Recognized dreams, flashbacks and quoted paragraphs are conservatively skipped.",
                ),
                wrap=True,
            )
        )
        offline_layout.addWidget(
            label(
                tr(
                    "规则覆盖有限。复杂伏笔、别名和隐含时间关系需要模型与作者判断。",
                    "Coverage is limited. Complex clues, aliases and implicit timelines require model and author judgment.",
                ),
                "Muted",
                True,
            )
        )
        layout.addWidget(self.offline)
        self.remote = QWidget()
        form = box(self.remote, spacing=10)
        form.addWidget(label(tr("接口基础地址", "Base URL")))
        self.url = QLineEdit(settings.base_url)
        self.url.setPlaceholderText("http://localhost:11434")
        form.addWidget(self.url)
        form.addWidget(
            label(
                tr(
                    "模型服务凭据（本机 Ollama 通常留空）",
                    "Provider credential (usually empty for local Ollama)",
                )
            )
        )
        self.key = QLineEdit(settings.api_key)
        self.key.setEchoMode(QLineEdit.EchoMode.Password)
        form.addWidget(self.key)
        form.addWidget(label(tr("模型名称", "Model name")))
        model_row = box(horizontal=True)
        self.model = QComboBox()
        self.model.setEditable(True)
        self.model.setCurrentText(settings.model)
        model_row.addWidget(self.model, 1)
        self.discover = button(tr("读取模型", "Find models"), self.load_models)
        model_row.addWidget(self.discover)
        form.addLayout(model_row)
        self.connection = label(
            tr(
                "可直接填写服务中已安装或可用的模型名称。",
                "You can also enter the exact model name manually.",
            ),
            "Muted",
            True,
        )
        form.addWidget(self.connection)
        form.addWidget(
            label(
                tr(
                    "模型设置会保留，凭据只在本次运行中保存。检查时，相关原文会发送给这里配置的服务。",
                    "Model settings persist. Credentials stay in memory for this session. Model review sends relevant passages to the service configured here.",
                ),
                "Muted",
                True,
            )
        )
        layout.addWidget(self.remote)
        actions = box(horizontal=True)
        actions.addStretch()
        actions.addWidget(button(tr("取消", "Cancel"), self.reject))
        self.save = button(tr("使用此方式", "Use this engine"), self.submit, "Primary", "check")
        actions.addWidget(self.save)
        layout.addLayout(actions)
        self.mode.currentIndexChanged.connect(self.change_mode)
        self.update_fields()

    def update_fields(self):
        online = self.mode.currentData() != "rules"
        self.remote.setVisible(online)
        self.offline.setVisible(not online)
        self.adjustSize()

    def change_mode(self):
        mode = self.mode.currentData()
        self.key.clear()
        self.url.setText("http://localhost:11434" if mode == "ollama" else "")
        self.url.setPlaceholderText(
            "http://localhost:11434" if mode == "ollama" else "https://your-provider.example/v1"
        )
        self.model.clear()
        self.update_fields()

    def settings(self):
        return Settings(
            provider=self.mode.currentData(),
            base_url=self.url.text().strip(),
            model=self.model.currentText().strip(),
            api_key=self.key.text(),
            language=self.original.language,
        ).validate()

    def submit(self):
        try:
            self.settings()
        except ValueError as exc:
            QMessageBox.warning(self, "PlotProof", str(exc))
            return
        self.accept()

    def load_models(self):
        tr = self.tr2
        try:
            settings = Settings(
                provider=self.mode.currentData(),
                base_url=self.url.text().strip(),
                model="discovery",
                api_key=self.key.text(),
            ).validate()
        except ValueError as exc:
            self.connection.setText(str(exc))
            return

        def query(progress, cancel):
            base = settings.base_url
            if settings.provider == "ollama":
                url = base + ("/tags" if base.endswith("/api") else "/api/tags")
            else:
                url = base.removesuffix("/chat/completions") + "/models"
            headers = {"Accept": "application/json"}
            if settings.api_key:
                headers["Authorization"] = "Bearer " + settings.api_key
            with build_opener(NoRedirect).open(Request(url, headers=headers), timeout=12) as response:
                value = json.loads(response.read(2_000_000))
            values = value.get("models", []) if settings.provider == "ollama" else value.get("data", [])
            return [v.get("name", v.get("id", "")) for v in values if isinstance(v, dict)][:300]

        self.worker = Worker(query, self)
        self.worker.result.connect(self.show_models)
        self.worker.failed.connect(
            lambda message: self.connection.setText(
                tr(
                    "未能读取模型。请核对服务，或手动填写模型名。",
                    "Could not list models. Check the service, or enter the model name manually.",
                )
            )
        )
        self.worker.finished.connect(self.probe_finished)
        self.discover.setEnabled(False)
        self.mode.setEnabled(False)
        self.save.setEnabled(False)
        self.connection.setText(tr("正在连接…", "Connecting…"))
        self.worker.start()

    def show_models(self, models):
        selected = self.model.currentText()
        self.model.clear()
        self.model.addItems(sorted(set(v for v in models if isinstance(v, str) and v)))
        if selected:
            self.model.setCurrentText(selected)
        self.connection.setText(self.tr2(f"读取到 {len(models)} 个模型。", f"Found {len(models)} models."))

    def probe_finished(self):
        self.worker.deleteLater()
        self.worker = None
        self.discover.setEnabled(True)
        self.mode.setEnabled(True)
        self.save.setEnabled(True)

    def reject(self):
        if self.worker and self.worker.isRunning():
            self.connection.setText(
                self.tr2(
                    "请等待连接检查结束（最多 12 秒）。",
                    "Wait for the connection check to finish (up to 12 seconds).",
                )
            )
            return
        super().reject()

    def closeEvent(self, event):
        if self.worker and self.worker.isRunning():
            event.ignore()
        else:
            event.accept()
