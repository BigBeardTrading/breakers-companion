# app.py — Breakers Companion v2.0.2
# - Gold header (Home / Add Set / Saved Sets + BIG BEARD TRADING)
# - Home screen: background only (no center logo/title), subtle dark overlay
# - Top mask equals header height to prevent any background strip under header
# - Theme toggle (Dark/Light), Window mode (Windowed/Maximized/Fullscreen, F11)
# - Windowed by default (resizable), persists windowed geometry
# - Saved Sets "wall" with live filter via top Search
# - Readable search field, trimmed table title (e.g., "2025 Donruss Football")

import json
import sys
from pathlib import Path
from typing import List, Optional

import pandas as pd

from PySide6.QtCore import (
    Qt, QAbstractTableModel, QModelIndex, QSortFilterProxyModel,
    QTimer, QDateTime, QByteArray
)
from PySide6.QtGui import (
    QIcon, QPixmap, QAction, QActionGroup, QShortcut, QKeySequence
)
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
    QLabel, QLineEdit, QFileDialog, QTableView, QStackedWidget, QMessageBox,
    QStatusBar, QScrollArea, QMenu, QSizePolicy, QGraphicsDropShadowEffect
)

APP_TITLE = "Breakers Companion — v2.0.2"
EXCEL_ENGINE = "openpyxl"

# ---------- App paths ----------
if getattr(sys, "frozen", False):
    APP_DIR = Path(sys.executable).resolve().parent
else:
    APP_DIR = Path(__file__).resolve().parent

ASSETS_DIR         = APP_DIR / "assets"
RECENTS_PATH       = APP_DIR / "saved_sets.json"
SETTINGS_PATH      = APP_DIR / "settings.json"
PREFERRED_SETS_DIR = APP_DIR / "sets"

def pick(paths: list[Path]) -> Optional[Path]:
    for p in paths:
        if p.exists():
            return p
    return None

ICON_PATH = pick([ASSETS_DIR / "BBT_BreakersCompanion.ico", ASSETS_DIR / "bbt.ico"])
HOME_LOGO = pick([ASSETS_DIR / "bbt.png", ASSETS_DIR / "BBT-icon on brick.png"])
HOME_BG   = pick([ASSETS_DIR / "Background.png"])

# ---------- recents ----------
def load_recent_files(max_items: int = 60) -> List[str]:
    if not RECENTS_PATH.exists(): return []
    try:
        data = json.loads(RECENTS_PATH.read_text(encoding="utf-8"))
        items = [s for s in data if isinstance(s, str)]
        items = [s for s in items if Path(s).exists()]
        return items[:max_items]
    except Exception:
        return []

def save_recent_files(items: List[str]):
    seen, out = set(), []
    for s in items:
        if s not in seen:
            seen.add(s); out.append(s)
    RECENTS_PATH.write_text(json.dumps(out, indent=2), encoding="utf-8")

def push_recent(path: Path):
    items = load_recent_files()
    s = str(Path(path))
    items = [s] + [x for x in items if x != s]
    save_recent_files(items[:60])

def remove_recent(path: Path):
    s = str(Path(path))
    items = [x for x in load_recent_files() if x != s]
    save_recent_files(items)

# ---------- settings ----------
DEFAULT_SETTINGS = {
    "theme": "dark",           # "dark" | "light"
    "window_mode": "windowed", # default resizable
    "normal_geom": ""          # base64 geometry for windowed mode
}

def load_settings() -> dict:
    if SETTINGS_PATH.exists():
        try:
            data = json.loads(SETTINGS_PATH.read_text(encoding="utf-8"))
            out = DEFAULT_SETTINGS.copy()
            out.update({k: v for k, v in data.items() if k in out})
            return out
        except Exception:
            pass
    return DEFAULT_SETTINGS.copy()

def save_settings(cfg: dict):
    try:
        SETTINGS_PATH.write_text(json.dumps(cfg, indent=2), encoding="utf-8")
    except Exception:
        pass

# ---------- model ----------
class DataFrameModel(QAbstractTableModel):
    def __init__(self, df: Optional[pd.DataFrame] = None, parent=None):
        super().__init__(parent)
        self._df = df if df is not None else pd.DataFrame()

    def setDataFrame(self, df: pd.DataFrame):
        self.beginResetModel(); self._df = df; self.endResetModel()

    def rowCount(self, parent=QModelIndex()):    return 0 if (parent.isValid() or self._df is None) else len(self._df)
    def columnCount(self, parent=QModelIndex()): return 0 if (parent.isValid() or self._df is None) else self._df.shape[1]

    def data(self, index, role=Qt.DisplayRole):
        if not index.isValid() or self._df is None: return None
        if role == Qt.DisplayRole:
            val = self._df.iat[index.row(), index.column()]
            return "" if pd.isna(val) else str(val)
        return None

    def headerData(self, section, orientation, role=Qt.DisplayRole):
        if role != Qt.DisplayRole or self._df is None: return None
        if orientation == Qt.Horizontal:
            try: return str(self._df.columns[section])
            except Exception: return ""
        return str(section + 1)

    def dataframe(self) -> pd.DataFrame: return self._df

# ---------- fast filter ----------
class RowFilterProxy(QSortFilterProxyModel):
    def __init__(self, parent=None):
        super().__init__(parent); self._needle = ""; self._mask = None
    def setFilterQuery(self, text: str):
        text = (text or "").strip().lower()
        if text != self._needle:
            self._needle = text; self.invalidateFilter()
    def invalidate(self): self._mask = None; super().invalidate()
    def invalidateFilter(self): self._mask = None; super().invalidateFilter()
    def _compute_mask(self):
        src = self.sourceModel(); df = getattr(src, "dataframe", lambda: None)() if src else None
        if df is None or df.empty: self._mask = None; return
        if not self._needle: self._mask = pd.Series(True, index=df.index); return
        joined = df.fillna("").astype(str).agg(" ".join, axis=1).str.lower()
        self._mask = joined.str.contains(self._needle, na=False)
    def filterAcceptsRow(self, r: int, parent: QModelIndex) -> bool:
        if self._mask is None: self._compute_mask()
        if self._mask is None or r < 0 or r >= len(self._mask): return True
        try: return bool(self._mask.iat[r])
        except Exception: return True

# ---------- themes ----------
THEME_DARK = """
QMainWindow, QWidget { background-color: #0e1015; color: #e6e6e6; }
QStatusBar { background: #0b0d12; color: #cbd5e1; border-top: 1px solid #1f2937; }
QScrollArea { background: transparent; border: none; }
QLabel { color: #e8e8e8; }
QTableView {
    background-color: #0f131a;
    alternate-background-color: #121823;
    gridline-color: #1f2937;
    color: #e6e6e6;
    selection-background-color: #c4831d;
    selection-color: #0b0d12;
}
QHeaderView::section {
    background: #121723;
    color: #f1f5f9;
    border: 0px;
    padding: 6px;
}
QTableCornerButton::section { background: #121723; border: 0px; }
"""

THEME_LIGHT = """
QMainWindow, QWidget { background-color: #f6f7fb; color: #11131a; }
QStatusBar { background: #eef2f7; color: #11131a; border-top: 1px solid #d9dee7; }
QScrollArea { background: transparent; border: none; }
QLabel { color: #11131a; }
QTableView {
    background-color: #ffffff;
    alternate-background-color: #f2f5fa;
    gridline-color: #d6d9df;
    color: #11131a;
    selection-background-color: #ffd56a;
    selection-color: #151515;
}
QHeaderView::section {
    background: #f0f2f6;
    color: #11131a;
    border: 0px;
    padding: 6px;
}
QTableCornerButton::section { background: #f0f2f6; border: 0px; }
"""

# ---------- UI helpers ----------
GOLD_BOLD_BTN = """
QPushButton {
    font-family: 'Segoe UI';
    font-size: 18px;
    font-weight: 800;
    letter-spacing: 1px;
    text-transform: uppercase;
    color: #1b1202;
    padding: 10px 22px;
    border-radius: 22px;
    border: 1px solid #b98a28;
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
        stop:0   #ffe9a8,
        stop:0.45 #f9c851,
        stop:0.46 #e7b23f,
        stop:1   #c4831d);
}
QPushButton:hover {
    border-color: #c99a34;
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
        stop:0   #fff3c9,
        stop:0.45 #ffd977,
        stop:0.46 #f1c252,
        stop:1   #d0922a);
}
QPushButton:pressed {
    color: #120a00;
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
        stop:0 #c4831d,
        stop:1 #ffe9a8);
}
"""

def add_soft_shadow(w):
    sh = QGraphicsDropShadowEffect(w)
    sh.setBlurRadius(24)
    sh.setOffset(0, 2)
    sh.setColor(Qt.black)
    w.setGraphicsEffect(sh)

def pretty_set_title_from_filename(path: Path) -> str:
    """'... 2025 Donruss Football Master Checklist.xlsx' -> '2025 Donruss Football'."""
    base = Path(path).stem
    b = base.replace("_", " ").replace("-", " ").replace("—", " ").replace("–", " ")
    key = "master checklist"
    low = b.lower()
    if key in low:
        b = b[:low.index(key)]
    b = " ".join(b.strip(" _-–—").split())
    return b or base

# ---------- Header bar ----------
class HomeBar(QWidget):
    def __init__(self, on_home, on_add_set, on_open_saved, on_settings, parent=None):
        super().__init__(parent)
        self.setObjectName("homebar")
        self.setAttribute(Qt.WA_StyledBackground, True)

        row = QHBoxLayout(self)
        row.setContentsMargins(12, 8, 12, 8)
        row.setSpacing(12)

        self.brand_left = QLabel("Breakers Companion")
        self.brand_left.setStyleSheet("""
            QLabel { color: #ffd66e; font-family: 'Segoe UI'; font-weight: 900; font-size: 16px; letter-spacing: .5px; }
        """)

        self.home_btn  = QPushButton("HOME")
        self.add_btn   = QPushButton("ADD SET")
        self.saved_btn = QPushButton("SAVED SETS")
        for b in (self.home_btn, self.add_btn, self.saved_btn):
            b.setMinimumHeight(44); b.setStyleSheet(GOLD_BOLD_BTN); add_soft_shadow(b)

        self.brand_center = QLabel("BIG BEARD TRADING")
        self.brand_center.setStyleSheet("""
            QLabel { color: #ffd66e; font-family: 'Segoe UI'; font-weight: 1000; font-size: 30px; letter-spacing: 1.2px; }
        """)

        self.search_label = QLabel("Search:")
        self.search_label.setStyleSheet("font-weight:700; color:#e9c15a;")
        self.search = QLineEdit()
        self.search.setPlaceholderText("Player, Team, … or Set name on Saved Sets")
        self.search.setClearButtonEnabled(True)
        self.search.setFixedWidth(420)
        self.search.setMinimumHeight(38)
        self.search.setStyleSheet("""
            QLineEdit {
                font-size: 14px; padding: 8px 12px;
                border-radius: 14px; border: 2px solid #b98a28;
                background: #fff8e1; color: #111;
                selection-background-color: #c4831d; selection-color: #fff;
            }
            QLineEdit:hover { background: #fff3c4; }
            QLineEdit:focus  { border: 2px solid #c99a34; background: #ffefad; }
        """)

        self.settings_btn = QPushButton("⚙")
        self.settings_btn.setToolTip("Settings")
        self.settings_btn.setFixedSize(36, 36)
        self.settings_btn.setCursor(Qt.PointingHandCursor)
        self.settings_btn.setStyleSheet("""
            QPushButton {
                font-size:18px; font-weight:700; color:#1b1202;
                border-radius:18px; border:1px solid #b98a28;
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #ffe9a8, stop:0.45 #f9c851, stop:0.46 #e7b23f, stop:1 #c4831d);
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #fff3c9, stop:0.45 #ffd977, stop:0.46 #f1c252, stop:1 #d0922a);
            }
        """)
        add_soft_shadow(self.settings_btn)

        self.settings_btn.clicked.connect(on_settings)
        self.home_btn.clicked.connect(on_home)
        self.add_btn.clicked.connect(on_add_set)
        self.saved_btn.clicked.connect(on_open_saved)

        row.addWidget(self.brand_left); row.addSpacing(8)
        row.addWidget(self.home_btn); row.addWidget(self.add_btn); row.addWidget(self.saved_btn)
        row.addSpacing(6); row.addWidget(self.brand_center)
        row.addStretch(1)

        right_box = QHBoxLayout(); right_box.setSpacing(8)
        right_box.addWidget(self.search_label); right_box.addWidget(self.search); right_box.addWidget(self.settings_btn)
        right_wrap = QWidget(); right_wrap.setLayout(right_box)
        right_wrap.setSizePolicy(QSizePolicy.Minimum, QSizePolicy.Preferred)
        row.addWidget(right_wrap)

    def searchLine(self) -> QLineEdit: return self.search
    def set_search_visible(self, v: bool): self.search_label.setVisible(v); self.search.setVisible(v)
    def set_settings_visible(self, v: bool): self.settings_btn.setVisible(v)

    def apply_bar_theme(self, theme: str):
        # Fully opaque header (no border line)
        if theme == "dark":
            self.setStyleSheet("#homebar { background:#0b0d12; }")
        else:
            self.setStyleSheet("#homebar { background:#eef2f7; }")

# ---------- Home page (background only, overlay, header-height mask) ----------
class HomePage(QWidget):
    def __init__(self, bg_path: Optional[Path], logo_path: Optional[Path], show_center: bool = False, parent=None):
        super().__init__(parent)

        self._mask_h = 64  # will be synced to header height

        # Full-bleed background
        self.bg = QLabel(self)
        self.bg.setScaledContents(True)
        if bg_path:
            pm = QPixmap(str(bg_path))
            if not pm.isNull():
                self.bg.setPixmap(pm)
        else:
            self.bg.setStyleSheet("background:#0e1015;")

        # Full-bleed overlay (darken a bit)
        self.overlay = QWidget(self)
        self.overlay.setAttribute(Qt.WA_StyledBackground, True)
        self.overlay.setStyleSheet("background-color: rgba(0,0,0,0.35);")

        # Top mask: same color as header, then fade transparent
        self.top_mask = QLabel(self.overlay)
        self.apply_mask_theme("dark")

        # Overlay layout
        self.ov = QVBoxLayout(self.overlay)
        self.ov.setContentsMargins(0, 0, 0, 0)

        # Spacer so optional content sits below the header area
        self._spacer = QWidget(self.overlay)
        self._spacer.setFixedHeight(self._mask_h)
        self.ov.addWidget(self._spacer)

        # (Optional) center branding — disabled by default
        if show_center:
            if logo_path:
                logo = QLabel()
                pm = QPixmap(str(logo_path))
                if not pm.isNull():
                    logo.setPixmap(pm.scaledToWidth(220, Qt.SmoothTransformation))
                    logo.setAlignment(Qt.AlignCenter)
                    logo.setStyleSheet("background: transparent;")
                    self.ov.addWidget(logo)

            title = QLabel("The Breakers Companion")
            title.setAlignment(Qt.AlignCenter)
            title.setStyleSheet("background: transparent; font-size:26px; font-weight:900; color:#f8f8f8; letter-spacing:.5px;")
            glow = QGraphicsDropShadowEffect(title)
            glow.setBlurRadius(28); glow.setOffset(0, 0); glow.setColor(Qt.black)
            title.setGraphicsEffect(glow)
            self.ov.addWidget(title)

        self.ov.addStretch(2)

    def set_mask_height(self, h: int):
        h = max(0, int(h))
        if h != self._mask_h:
            self._mask_h = h
            self._spacer.setFixedHeight(h)
            self._relayout()

    def apply_mask_theme(self, theme: str):
        # Solid few px, then quick fade to transparent
        if theme == "dark":
            self.top_mask.setStyleSheet("""
                QLabel { background: qlineargradient(x1:0,y1:0,x2:0,y2:1,
                    stop:0 rgba(11,13,18,255),
                    stop:0.06 rgba(11,13,18,255),
                    stop:1 rgba(11,13,18,0)); }
            """)
        else:
            self.top_mask.setStyleSheet("""
                QLabel { background: qlineargradient(x1:0,y1:0,x2:0,y2:1,
                    stop:0 rgba(238,242,247,255),
                    stop:0.06 rgba(238,242,247,255),
                    stop:1 rgba(238,242,247,0)); }
            """)

    def resizeEvent(self, e):
        self._relayout()
        super().resizeEvent(e)

    def _relayout(self):
        r = self.rect()
        self.bg.setGeometry(r)
        self.overlay.setGeometry(r)
        self.top_mask.setGeometry(0, 0, r.width(), self._mask_h)

# ---------- Saved Sets + Table ----------
class SetCard(QPushButton):
    def __init__(self, path: Path, on_open, parent=None):
        super().__init__(parent)
        self.path = Path(path); self.on_open = on_open
        self.setMinimumSize(260, 110); self.setMaximumWidth(360)
        self.setCursor(Qt.PointingHandCursor); self.setCheckable(False)
        self.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Fixed)
        self.setStyleSheet("""
            QPushButton { text-align:left; border:1px solid rgba(0,0,0,0.18);
                border-radius:12px; padding:12px 14px; background:rgba(255,255,255,0.96); color:#111; }
            QPushButton:hover { border-color:rgba(0,0,0,0.35); background:rgba(255,255,255,1.0); }
        """)
        name = self.path.name; folder = str(self.path.parent)
        try:
            mtime = QDateTime.fromSecsSinceEpoch(int(self.path.stat().st_mtime)).toString("yyyy-MM-dd  HH:mm")
        except Exception:
            mtime = "—"
        self.setText(f"{name}\n{folder}\nModified: {mtime}")
        self.setToolTip(str(self.path)); self.clicked.connect(lambda: self.on_open(self.path))
    def contextMenuEvent(self, e):
        m = QMenu(self); act = m.addAction("Remove from Saved")
        if m.exec(e.globalPos()) == act: remove_recent(self.path); self.setDisabled(True)

class SavedSetsWall(QWidget):
    def __init__(self, on_open_path, on_back, parent=None):
        super().__init__(parent); self.on_open_path = on_open_path
        self.all_paths: List[Path] = []
        v = QVBoxLayout(self); v.setContentsMargins(10,10,10,10)
        header = QHBoxLayout()
        title = QLabel("Saved Sets"); title.setStyleSheet("font-size:22px; font-weight:700;")
        back = QPushButton("← Back"); back.setStyleSheet(GOLD_BOLD_BTN); back.setMinimumHeight(36); add_soft_shadow(back)
        back.clicked.connect(on_back)
        header.addWidget(title); header.addStretch(1); header.addWidget(back); v.addLayout(header)
        self.scroll = QScrollArea(); self.scroll.setWidgetResizable(True); v.addWidget(self.scroll, 1)
        self.inner = QWidget(); self.row = QHBoxLayout(self.inner)
        self.row.setContentsMargins(10,10,10,10); self.row.setSpacing(10); self.scroll.setWidget(self.inner)
        self.refresh()
    def _rebuild_cards(self, paths: List[Path]):
        while self.row.count():
            it = self.row.takeAt(0); w = it.widget(); w and w.setParent(None)
        if not paths:
            empty = QLabel("No saved sets match your search.")
            empty.setStyleSheet("color:#bbb; font-style:italic;")
            self.row.addWidget(empty); self.row.addStretch(1); return
        for p in paths: self.row.addWidget(SetCard(p, on_open=self.on_open_path, parent=self.inner))
        self.row.addStretch(1)
    def refresh(self):
        recent = load_recent_files(); self.all_paths = [Path(s) for s in recent]; self._rebuild_cards(self.all_paths)
    def apply_filter(self, text: str):
        n = (text or "").strip().lower()
        self._rebuild_cards(self.all_paths if not n else [p for p in self.all_paths if n in p.name.lower()])

class TablePage(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        v = QVBoxLayout(self); v.setContentsMargins(10,10,10,10)
        self.title_label = QLabel(""); self.title_label.setStyleSheet("font-size:20px; font-weight:800; color:#ffd66e;")
        add_soft_shadow(self.title_label); v.addWidget(self.title_label)
        self.src_model = DataFrameModel(pd.DataFrame()); self.proxy = RowFilterProxy(self)
        self.proxy.setSourceModel(self.src_model)
        self.table = QTableView(); self.table.setModel(self.proxy)
        self.table.setSortingEnabled(True); self.table.setAlternatingRowColors(True)
        self.table.setSelectionBehavior(QTableView.SelectRows); self.table.setEditTriggers(QTableView.NoEditTriggers)
        self.table.horizontalHeader().setStretchLastSection(True); v.addWidget(self.table, 1)
    def set_dataframe(self, df: pd.DataFrame):
        self.src_model.setDataFrame(df); self.proxy.invalidate()
        self.table.resizeColumnsToContents(); self.table.horizontalHeader().setStretchLastSection(True)
    def set_title(self, title: str): self.title_label.setText(title)

# ---------- Main Window ----------
class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__(); self.setWindowTitle(APP_TITLE)
        self.setMinimumSize(900, 560)
        self.resize(1280, 800)

        # Windows taskbar grouping
        if sys.platform.startswith("win"):
            try:
                import ctypes
                ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("BigBeardTrading.BreakersCompanion")
            except Exception:
                pass

        self.settings = load_settings()
        self.status = QStatusBar(self); self.setStatusBar(self.status)

        central = QWidget(self)
        outer = QVBoxLayout(central)
        outer.setContentsMargins(0,0,0,0)
        outer.setSpacing(0)  # no gap under header

        self.bar = HomeBar(
            on_home=self._show_home,
            on_add_set=self._open_file_dialog,
            on_open_saved=self._show_saved_wall,
            on_settings=self._open_settings_menu
        )
        outer.addWidget(self.bar)

        self.stack = QStackedWidget(self)
        outer.addWidget(self.stack, 1)

        # Home page: background only, overlay + header-height mask
        self.home = HomePage(HOME_BG, HOME_LOGO, show_center=False)
        self.stack.addWidget(self.home)   # index 0

        self.saved_wall = SavedSetsWall(self._open_saved_path, self._show_home)
        self.stack.addWidget(self.saved_wall)  # index 1

        self.table = TablePage()
        self.stack.addWidget(self.table)  # index 2

        self.setCentralWidget(central)

        # Debounced search
        self._debounce = QTimer(self); self._debounce.setInterval(200); self._debounce.setSingleShot(True)
        self.bar.searchLine().textChanged.connect(lambda _: self._debounce.start())
        self._debounce.timeout.connect(self._apply_search)

        # Theme
        self._apply_theme(self.settings["theme"])

        # Keyboard toggle
        QShortcut(QKeySequence("F11"), self, activated=self._toggle_fullscreen)

        if ICON_PATH: self.setWindowIcon(QIcon(str(ICON_PATH)))
        self._show_home()

        # Sync mask height to the actual header height once laid out
        QTimer.singleShot(0, self._sync_mask_to_header)

        # Restore windowed geometry if applicable
        if self.settings.get("window_mode") == "windowed":
            self._restore_normal_geometry()

    def _sync_mask_to_header(self):
        self.home.set_mask_height(self.bar.height())

    # ----- geometry persistence -----
    def _restore_normal_geometry(self):
        b64 = self.settings.get("normal_geom") or ""
        if b64:
            try:
                ba = QByteArray.fromBase64(b64.encode("ascii"))
                if not ba.isEmpty():
                    self.restoreGeometry(ba)
            except Exception:
                pass

    def _save_normal_geometry(self):
        try:
            ba = self.saveGeometry()
            self.settings["normal_geom"] = bytes(ba.toBase64()).decode("ascii")
            save_settings(self.settings)
        except Exception:
            pass

    def resizeEvent(self, e):
        # Keep the mask synced if header height changes
        self.home.set_mask_height(self.bar.height())
        super().resizeEvent(e)

    def closeEvent(self, e):
        if self.settings.get("window_mode") == "windowed" and not self.isFullScreen():
            self._save_normal_geometry()
        super().closeEvent(e)

    # ----- Settings menu -----
    def _open_settings_menu(self):
        m = QMenu(self)

        theme_menu = m.addMenu("Theme")
        group_theme = QActionGroup(m); group_theme.setExclusive(True)
        act_dark = QAction("Dark", m, checkable=True); act_light = QAction("Light", m, checkable=True)
        group_theme.addAction(act_dark); group_theme.addAction(act_light)
        theme_menu.addAction(act_dark); theme_menu.addAction(act_light)
        (act_dark if self.settings["theme"] == "dark" else act_light).setChecked(True)
        act_dark.triggered.connect(lambda: self._set_theme("dark"))
        act_light.triggered.connect(lambda: self._set_theme("light"))

        mode_menu = m.addMenu("Window mode")
        group_mode = QActionGroup(m); group_mode.setExclusive(True)
        act_fs  = QAction("Fullscreen", m, checkable=True)
        act_max = QAction("Maximized", m, checkable=True)
        act_win = QAction("Windowed", m, checkable=True)
        for a in (act_fs, act_max, act_win): group_mode.addAction(a); mode_menu.addAction(a)
        cur = self.settings["window_mode"]
        (act_fs if cur == "fullscreen" else act_max if cur == "maximized" else act_win).setChecked(True)
        act_fs.triggered.connect(lambda: self._set_window_mode("fullscreen"))
        act_max.triggered.connect(lambda: self._set_window_mode("maximized"))
        act_win.triggered.connect(lambda: self._set_window_mode("windowed"))

        m.exec(self.bar.settings_btn.mapToGlobal(self.bar.settings_btn.rect().bottomRight()))

    def _set_theme(self, which: str):
        self.settings["theme"] = which; self._apply_theme(which); save_settings(self.settings)

    def _set_window_mode(self, which: str):
        self.settings["window_mode"] = which; save_settings(self.settings)
        self._apply_window_mode(which)

    def _apply_theme(self, theme: str):
        QApplication.instance().setStyleSheet(THEME_DARK if theme == "dark" else THEME_LIGHT)
        self.bar.apply_bar_theme(theme)
        self.home.apply_mask_theme(theme)

    def _apply_window_mode(self, mode: str):
        if mode == "fullscreen":
            self.showFullScreen()
        elif mode == "maximized":
            self.showMaximized()
        else:
            self.showNormal()
            self._restore_normal_geometry()

    def _toggle_fullscreen(self):
        if self.isFullScreen():
            self._apply_window_mode(self.settings.get("window_mode", "windowed"))
        else:
            self.showFullScreen()

    # ----- Page switching -----
    def _show_home(self):
        self.bar.set_search_visible(False); self.bar.set_settings_visible(True)
        self.stack.setCurrentIndex(0); self.status.showMessage("Ready", 1500)

    def _show_saved_wall(self):
        self.bar.set_settings_visible(False); self.bar.set_search_visible(True)
        self.saved_wall.refresh(); self.stack.setCurrentIndex(1)

    def _show_table(self):
        self.bar.set_settings_visible(False); self.bar.set_search_visible(True)
        self.stack.setCurrentIndex(2)

    # ----- Search router -----
    def _apply_search(self):
        txt = self.bar.searchLine().text()
        idx = self.stack.currentIndex()
        if idx == 1: self.saved_wall.apply_filter(txt)
        elif idx == 2: self.table.proxy.setFilterQuery(txt)

    # ----- File ops -----
    def _open_file_dialog(self):
        preferred = PREFERRED_SETS_DIR
        if not preferred.exists(): preferred.mkdir(parents=True, exist_ok=True)
        path_str, _ = QFileDialog.getOpenFileName(self, "Open Set (.xlsx)", str(preferred), "Excel Files (*.xlsx)")
        if path_str: self._open_path(Path(path_str))

    def _open_saved_path(self, p: Path): self._open_path(p)

    def _open_path(self, p: Path):
        try:
            self.status.showMessage(f"Loading {p.name} …")
            df = pd.read_excel(p, engine=EXCEL_ENGINE)
            df.columns = [str(c) if c is not None else "" for c in df.columns]
            self.table.set_dataframe(df)
            self.table.set_title(pretty_set_title_from_filename(p))
            push_recent(p); self._show_table()
            self.status.showMessage(f"Loaded {p.name} — {len(df):,} rows × {df.shape[1]} cols", 5000)
        except Exception as e:
            QMessageBox.critical(self, "Load Error", f"Failed to open file:\n{p}\n\n{e}")

# ---------- entry ----------
def main():
    app = QApplication(sys.argv)
    app.setApplicationName(APP_TITLE)

    w = MainWindow()

    mode = w.settings.get("window_mode", "windowed")
    if mode == "fullscreen":
        w.showFullScreen()
    elif mode == "maximized":
        w.showMaximized()
    else:
        w.showNormal()
        w._restore_normal_geometry()

    if ICON_PATH: app.setWindowIcon(QIcon(str(ICON_PATH)))
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
