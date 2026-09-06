"""An editorial desktop design system: ink, paper, pine and amber."""

from PySide6.QtCore import QByteArray, Qt
from PySide6.QtGui import QIcon, QPainter, QPixmap
from PySide6.QtSvg import QSvgRenderer

INK = "#172c30"
MUTED = "#788582"
PINE = "#21735e"
AMBER = "#bd7d36"

PATHS = {
    "book": '<path d="M3 4h7l2 2 2-2h7v16h-7l-2 2-2-2H3zM12 6v16"/>',
    "import": '<path d="M4 14v6h16v-6M12 3v12m-5-5 5 5 5-5"/>',
    "export": '<path d="M4 14v6h16v-6M12 15V3m-5 5 5-5 5 5"/>',
    "plus": '<path d="M12 4v16M4 12h16"/>',
    "play": '<path d="m8 4 13 8-13 8z"/>',
    "check": '<path d="m4 12 5 5L20 6"/>',
    "x": '<path d="m6 6 12 12M6 18 18 6"/>',
    "search": '<circle cx="10" cy="10" r="6"/><path d="m15 15 6 6"/>',
    "grid": '<rect x="3" y="3" width="7" height="7" rx="1"/><rect x="14" y="3" width="7" height="7" rx="1"/><rect x="3" y="14" width="7" height="7" rx="1"/><rect x="14" y="14" width="7" height="7" rx="1"/>',
    "review": '<rect x="3" y="4" width="7" height="16" rx="1"/><rect x="14" y="4" width="7" height="16" rx="1"/><path d="M6 9h1m10 6h1M9 12h6"/>',
    "edit": '<path d="m4 16-1 5 5-1L21 7l-6-5zM12 5l6 6"/>',
    "map": '<circle cx="5" cy="6" r="3"/><circle cx="19" cy="6" r="3"/><circle cx="12" cy="19" r="3"/><path d="m7 8 4 8m6-8-4 8M8 6h8"/>',
    "history": '<path d="M3 10a9 9 0 1 1 0 5M3 3v7h7M12 7v6l4 2"/>',
    "settings": '<circle cx="12" cy="12" r="3"/><path d="m9 3 1-2h4l1 2 3 2 3 1v4l-2 2 2 2v4l-3 1-3 2-1 2h-4l-1-2-3-2-3-1v-4l2-2-2-2V6l3-1z"/>',
    "arrow": '<path d="M4 12h16m-6-6 6 6-6 6"/>',
    "back": '<path d="M20 12H4m6-6-6 6 6 6"/>',
    "archive": '<rect x="3" y="3" width="18" height="4" rx="1"/><path d="M5 7v14h14V7M9 11h6"/>',
    "file": '<path d="M5 2h9l5 5v15H5zM14 2v6h5M8 12h8m-8 4h6"/>',
    "spark": '<path d="m12 3 2.5 6.5L21 12l-6.5 2.5L12 21l-2.5-6.5L3 12l6.5-2.5z"/>',
    "save": '<path d="M3 3h15l3 3v15H3zM7 3v7h10V3M7 21v-7h10v7"/>',
    "info": '<circle cx="12" cy="12" r="9"/><path d="M12 11v6M12 7v1"/>',
    "copy": '<rect x="8" y="8" width="13" height="13" rx="2"/><path d="M16 8V3H3v13h5"/>',
}


def icon(name, color=INK, size=20):
    source = f'<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="{color}" stroke-width="1.65" stroke-linecap="round" stroke-linejoin="round">{PATHS.get(name, PATHS["file"])}</svg>'
    renderer = QSvgRenderer(QByteArray(source.encode()))
    pix = QPixmap(size * 2, size * 2)
    pix.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pix)
    renderer.render(painter)
    painter.end()
    pix.setDevicePixelRatio(2)
    return QIcon(pix)


STYLE = """
QWidget { color:#233937; font-family:'Segoe UI','Microsoft YaHei UI'; font-size:13px; }
QMainWindow, QDialog { background:#f4f3ed; }
QWidget#Sidebar { background:#122323; border:0; }
QWidget#Sidebar QLabel { color:#aabdb5; background:transparent; }
QLabel#Brand { color:#f1f3e9; font-size:27px; font-weight:600; letter-spacing:-1px; }
QLabel#SidebarOverline { color:#698b7e; font-size:10px; letter-spacing:2px; }
QLabel#SidebarFoot { color:#7c9b8d; font-size:11px; }
QPushButton { background:#fffefa; border:1px solid #daddd4; border-radius:7px; padding:9px 14px; color:#304640; text-align:center; }
QPushButton:hover { background:#eaece3; border-color:#b6c5ba; }
QPushButton:pressed { background:#dce8dc; }
QPushButton:focus { border:1px solid #4a9177; }
QPushButton:disabled { color:#a4aca5; background:#eeefe9; border-color:#e3e5dd; }
QPushButton#Primary { background:#246b54; color:#ffffff; border:1px solid #246b54; font-weight:600; padding:11px 18px; }
QPushButton#Primary:hover { background:#1d5a46; border-color:#1d5a46; }
QPushButton#Primary:disabled { background:#bac9be; color:#eff3ed; border-color:#bac9be; }
QPushButton#Subtle { border:0; background:transparent; text-align:left; padding:8px 10px; color:#657b70; }
QPushButton#Subtle:hover { background:#e6eae0; color:#214e3d; }
QPushButton#SideButton { border:0; background:transparent; color:#adbbb3; text-align:left; padding:11px 12px; }
QPushButton#SideButton:hover { background:#213831; color:#f1f4e9; }
QPushButton#SideButton:checked { background:#294637; color:#d7e9d4; border:1px solid #385d47; }
QPushButton#SideImport { background:#d8e8ce; color:#18372c; border:0; font-weight:600; text-align:left; padding:12px 14px; }
QPushButton#SideImport:hover { background:#ebf5df; }
QPushButton#Tab { background:transparent; border:0; border-bottom:2px solid transparent; border-radius:0; padding:15px 17px; color:#889188; }
QPushButton#Tab:checked { color:#245c44; border-bottom:2px solid #286d52; font-weight:600; }
QPushButton#Tab:hover { color:#245c44; background:#eaece3; }
QPushButton#Chip { background:transparent; border:0; padding:7px 10px; font-size:12px; border-radius:5px; color:#7a887d; }
QPushButton#Chip:checked { background:#e1e9dc; color:#365c40; font-weight:600; }
QPushButton#Chip:hover { background:#e6eadf; }
QLabel#Eyebrow { color:#768c75; font-size:10px; letter-spacing:2px; font-weight:600; }
QLabel#HeroTitle { font-size:45px; color:#1b3b31; font-weight:500; }
QLabel#PageTitle { font-size:28px; font-weight:600; color:#203b31; }
QLabel#SectionTitle { font-size:19px; font-weight:600; color:#203b31; }
QLabel#Subhead { font-size:14px; color:#7a857b; }
QLabel#Muted { color:#8a9389; font-size:12px; }
QLabel#Pill { padding:5px 9px; color:#4a7759; background:#e5eddc; border-radius:5px; font-size:11px; }
QLabel#WarningPill { padding:5px 9px; color:#976529; background:#f1e8d6; border-radius:5px; font-size:11px; }
QFrame#Rule { background:#dddfd5; max-height:1px; border:0; }
QFrame#Panel { background:#fffef9; border:1px solid #dde1d4; border-radius:11px; }
QFrame#SoftPanel { background:#ebeee2; border:1px solid #dde4d5; border-radius:11px; }
QFrame#NotePanel { background:#eeefe5; border-left:3px solid #9dad88; border-radius:4px; }
QFrame#SourceBefore { background:#f4f1e8; border:1px solid #e1dbca; border-radius:9px; }
QFrame#SourceAfter { background:#f0f3e9; border:1px solid #dce4d3; border-radius:9px; }
QLabel#SourceTitle { color:#6c7a63; font-size:12px; font-weight:600; }
QLabel#Quote { color:#344238; font-family:'Georgia','Microsoft YaHei UI'; font-size:17px; line-height:170%; }
QLabel#BigNumber { font-family:'Bahnschrift','Segoe UI'; font-size:36px; color:#335541; }
QLabel#SummaryLabel { color:#87927e; font-size:11px; }
QFrame#Toast { background:#e2ebd8; border:1px solid #b8cfab; border-radius:7px; }
QFrame#Toast[error="true"] { background:#f2e4d9; border:1px solid #d7b79d; }
QFrame#StatusBar { background:#e9ede2; border-top:1px solid #d9e0d1; }
QFrame#StatusBar QLabel { color:#6c826d; font-size:11px; }
QScrollArea { border:0; background:transparent; }
QScrollArea>QWidget>QWidget { background:transparent; }
QScrollBar:vertical { border:0; background:transparent; width:9px; margin:3px 1px; }
QScrollBar::handle:vertical { background:#bec6b6; border-radius:3px; min-height:30px; }
QScrollBar::handle:vertical:hover { background:#97a990; }
QScrollBar::add-line:vertical,QScrollBar::sub-line:vertical { height:0; }
QScrollBar::add-page:vertical,QScrollBar::sub-page:vertical { background:transparent; }
QListWidget { background:transparent; border:0; outline:0; }
QListWidget#Projects { color:#abbeb0; padding:0; }
QListWidget#Projects::item { padding:10px 8px; border-radius:5px; margin:2px 0; }
QListWidget#Projects::item:selected { background:#2b4535; color:#e3edda; }
QListWidget#Projects::item:hover { background:#213a2e; }
QListWidget#Findings::item { border:1px solid #dce1d4; border-radius:9px; margin:0 6px 8px 0; background:#fffef9; }
QListWidget#Findings::item:selected { background:#e9efde; border:1px solid #a5b792; }
QListWidget#Findings::item:hover { border-color:#a6b996; }
QLineEdit,QPlainTextEdit,QTextEdit,QComboBox { background:#fffef9; color:#344338; border:1px solid #d8dfcf; border-radius:6px; padding:9px 11px; selection-background-color:#c3d5ac; selection-color:#253c29; }
QLineEdit:focus,QPlainTextEdit:focus,QTextEdit:focus,QComboBox:focus { border-color:#8eaa7c; }
QPlainTextEdit#Manuscript { border:0; border-radius:0; padding:26px 36px; background:#fcfbf5; font-family:'Georgia','Microsoft YaHei UI'; font-size:18px; }
QComboBox { padding-right:24px; min-height:19px; }
QComboBox::drop-down { border:0; width:23px; }
QComboBox QAbstractItemView { background:#fffef9; color:#263c31; selection-background-color:#e1e9d7; border:1px solid #becdad; }
QTreeWidget,QTableWidget { background:#fffef9; border:1px solid #e0e4d8; border-radius:8px; selection-background-color:#e4ecd8; selection-color:#25432d; outline:0; alternate-background-color:#f5f6ef; }
QTreeWidget::item { padding:8px 4px; border-bottom:1px solid #edf0e6; }
QHeaderView::section { background:#edf0e5; color:#708367; border:0; border-bottom:1px solid #dce3d0; padding:10px; font-size:11px; }
QSplitter::handle { background:#e0e5d7; width:1px; }
QProgressBar { border:0; background:#e0e7d8; height:5px; border-radius:2px; text-align:center; color:transparent; }
QProgressBar::chunk { background:#65924e; border-radius:2px; }
QToolTip { color:#eef1e5; background:#244134; border:0; padding:7px; }
QMenu { background:#fffef9; border:1px solid #d6dfca; padding:5px; }
QMenu::item { padding:9px 28px 9px 14px; border-radius:4px; }
QMenu::item:selected { background:#e6eddc; }
QMessageBox { background:#f4f3ed; }
QDialog QLabel { background:transparent; }
QCheckBox { spacing:8px; }
"""
