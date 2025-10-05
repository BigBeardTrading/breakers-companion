# app.py
# Breakers Companion — v2.0.1
# - Saved Sets WALL (stable)
# - Debounced, vectorized search
# - No custom paintEvent (prevents crash)
#
# Requirements: PySide6, pandas, openpyxl

import json
import sys
from pathlib import Path
from typing import List, Optional

import pandas as pd

from PySide6.QtCore import (
    Qt,
    QAbstractTableModel,
    QModelIndex,
    QSortFilterProxyModel,
    QTimer,
    QDateTime,
)
from PySide6.QtGui import QAction
from PySide6.QtWidgets import (
    QApplication,
    QMainWindow,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QPushButton,
    QLabel,
    QLineEdit,
    QFileDialog,
    QTableView,
    QStackedWidget,
    QMessageBox,
    QStatusBar,
    QToolBar,
    QScrollArea,
    QMenu,
    QSizePolicy,
)

APP_TITLE = "Breakers Companion — v2.0.1"
RECENTS_FILE = "saved_sets.json"
EXCEL_ENGINE = "openpyxl"  # ensure openpyxl is in requirements.txt


# -------------------
# Persistence helpers
# -------------------
def load_recent_files(max_items: int = 60) -> List[str]:
    p = Path(RECENTS_FILE)
    if not p.exists():
        return []
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
        items = [s for s in data if isinstance(s, str)]
        items = [s for s in items if Path(s).exists()]
        return items[:max_items]
    except Exception:
        return []


def save_recent_files(items: List[str]):
    seen = set()
    out: List[str] = []
    for s in items:
        if s not in seen:
            seen.add(s)
            out.append(s)
    Path(RECENTS_FILE).write_text(json.dumps(out, indent=2), encoding="utf-8")


def push_recent(path: Path):
    items = load_recent_files()
    s = str(Path(path))
    items = [s] + [x for x in items if x != s]
    save_recent_files(items[:60])


def remove_recent(path: Path):
    s = str(Path(path))
    items = [x for x in load_recent_files() if x != s]
    save_recent_files(items)


# ---------------------
# DataFrame table model
# ---------------------
class DataFrameModel(QAbstractTableModel):
    def __init__(self, df: Optional[pd.DataFrame] = None, parent=None):
        super().__init__(parent)
        self._df = df if df is not None else pd.DataFrame()

    def setDataFrame(self, df: pd.DataFrame):
        self.beginResetModel()
        self._df = df
        self.endResetModel()

    def rowCount(self, parent=QModelIndex()):
        if parent.isValid():
            return 0
        return 0 if self._df is None else len(self._df)

    def columnCount(self, parent=QModelIndex()):
        if parent.isValid():
            return 0
        return 0 if self._df is None else self._df.shape[1]

    def data(self, index, role=Qt.DisplayRole):
        if not index.isValid() or self._df is None:
            return None
        if role == Qt.DisplayRole:
            val = self._df.iat[index.row(), index.column()]
            if pd.isna(val):
                return ""
            return str(val)
        return None

    def headerData(self, section, orientation, role=Qt.DisplayRole):
        if role != Qt.DisplayRole or self._df is None:
            return None
        if orientation == Qt.Horizontal:
            try:
                return str(self._df.columns[section])
            except Exception:
                return ""
        return str(section + 1)

    def dataframe(self) -> pd.DataFrame:
        return self._df


# ---------------------------------
# Fast, debounced all-columns filter
# ---------------------------------
class RowFilterProxy(QSortFilterProxyModel):
    """Case-insensitive contains filter using a vectorized mask per query."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._needle = ""
        self._mask = None  # pandas Series[bool] aligned to source rows

    def setFilterQuery(self, text: str):
        text = (text or "").strip().lower()
        if text == self._needle:
            return
        self._needle = text
        self.invalidateFilter()

    def invalidate(self):
        self._mask = None
        super().invalidate()

    def invalidateFilter(self):
        self._mask = None
        super().invalidateFilter()

    def _compute_mask(self):
        src = self.sourceModel()
        if src is None:
            self._mask = None
            return
        df = getattr(src, "dataframe", lambda: None)()
        if df is None or df.empty:
            self._mask = None
            return
        if not self._needle:
            self._mask = pd.Series(True, index=df.index)
            return

        joined = (
            df.fillna("")
            .astype(str)
            .agg(" ".join, axis=1)
            .str.lower()
        )
        self._mask = joined.str.contains(self._needle, na=False)

    def filterAcceptsRow(self, source_row: int, source_parent: QModelIndex) -> bool:
        if self._mask is None:
            self._compute_mask()
        if self._mask is None:
            return True
        if source_row < 0 or source_row >= len(self._mask):
            return True
        try:
            return bool(self._mask.iat[source_row])
        except Exception:
            return True


# ------------
# UI Components
# ------------
class HomeBar(QWidget):
    """Top strip with your existing buttons, matching the v2.0.0 layout."""

    def __init__(self, on_home, on_add_set, on_open_saved, on_save_current, parent=None):
        super().__init__(parent)
        row = QHBoxLayout(self)
        row.setContentsMargins(8, 4, 8, 4)

        home_btn = QPushButton("Home")
        add_btn = QPushButton("Add Set")
        saved_btn = QPushButton("Open Saved Sets")
        save_btn = QPushButton("Save Current As...")

        home_btn.clicked.connect(on_home)
        add_btn.clicked.connect(on_add_set)
        saved_btn.clicked.connect(on_open_saved)
        save_btn.clicked.connect(on_save_current)

        row.addWidget(home_btn)
        row.addWidget(add_btn)
        row.addWidget(saved_btn)
        row.addWidget(save_btn)
        row.addStretch(1)

        row.addWidget(QLabel("Search:"))
        self.search = QLineEdit()
        self.search.setPlaceholderText("Player, Team, ...")
        self.search.setClearButtonEnabled(True)
        self.search.setFixedWidth(220)
        row.addWidget(self.search)

    def searchLine(self) -> QLineEdit:
        return self.search


class SetCard(QPushButton):
    """A big clickable 'card' for one recent .xlsx file. Plain text (no HTML), no custom painting."""

    def __init__(self, path: Path, on_open, parent=None):
        super().__init__(parent)
        self.path = Path(path)
        self.on_open = on_open

        self.setMinimumSize(260, 110)
        self.setMaximumWidth(360)
        self.setCursor(Qt.PointingHandCursor)
        self.setCheckable(False)
        self.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Fixed)
        self.setStyleSheet("""
            QPushButton {
                text-align: left;
                border: 1px solid rgba(0,0,0,0.15);
                border-radius: 12px;
                padding: 12px 14px;
                background: rgba(255,255,255,0.9);
            }
            QPushButton:hover {
                border-color: rgba(0,0,0,0.35);
                background: rgba(255,255,255,0.98);
            }
        """)

        name = self.path.name
        folder = str(self.path.parent)
        try:
            mtime_ts = int(self.path.stat().st_mtime)
            mtime = QDateTime.fromSecsSinceEpoch(mtime_ts).toString("yyyy-MM-dd  HH:mm")
        except Exception:
            mtime = "—"

        # Plain text with newlines (Qt renders nicely on a QPushButton)
        self.setText(f"{name}\n{folder}\nModified: {mtime}")
        self.setToolTip(str(self.path))

        self.clicked.connect(lambda: self.on_open(self.path))

    def contextMenuEvent(self, event):
        menu = QMenu(self)
        remove_action = menu.addAction("Remove from Saved")
        action = menu.exec(event.globalPos())
        if action == remove_action:
            remove_recent(self.path)
            self.setDisabled(True)  # visual hint; wall refreshes next time


class SavedSetsWall(QWidget):
    """Scrollable 'flow' wall of SetCard buttons."""

    def __init__(self, on_open_path, on_back, parent=None):
        super().__init__(parent)
        self.on_open_path = on_open_path

        v = QVBoxLayout(self)
        header = QHBoxLayout()
        title = QLabel("Saved Sets")
        title.setStyleSheet("font-size: 22px; font-weight: 600;")
        back = QPushButton("← Back")
        back.clicked.connect(on_back)
        header.addWidget(title)
        header.addStretch(1)
        header.addWidget(back)
        v.addLayout(header)

        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        v.addWidget(self.scroll, 1)

        self.inner = QWidget()
        self.row = QHBoxLayout(self.inner)
        self.row.setContentsMargins(10, 10, 10, 10)
        self.row.setSpacing(10)
        self.scroll.setWidget(self.inner)

        self.refresh()

    def refresh(self):
        # Clear old widgets
        while self.row.count():
            item = self.row.takeAt(0)
            w = item.widget()
            if w:
                w.setParent(None)

        recents = load_recent_files()
        if not recents:
            empty = QLabel("No saved sets yet. Open a .xlsx file to add it here.")
            empty.setStyleSheet("color:#666; font-style: italic;")
            self.row.addWidget(empty)
            self.row.addStretch(1)
            return

        for s in recents:
            self.row.addWidget(SetCard(Path(s), on_open=self.on_open_path, parent=self.inner))

        self.row.addStretch(1)


class TablePage(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        v = QVBoxLayout(self)

        self.src_model = DataFrameModel(pd.DataFrame())
        self.proxy = RowFilterProxy(self)
        self.proxy.setSourceModel(self.src_model)

        self.table = QTableView()
        self.table.setModel(self.proxy)
        self.table.setSortingEnabled(True)
        self.table.setAlternatingRowColors(True)
        self.table.setSelectionBehavior(QTableView.SelectRows)
        self.table.setEditTriggers(QTableView.NoEditTriggers)
        self.table.horizontalHeader().setStretchLastSection(True)

        v.addWidget(self.table, 1)

    def set_dataframe(self, df: pd.DataFrame):
        self.src_model.setDataFrame(df)
        self.proxy.invalidate()
        self.table.resizeColumnsToContents()
        self.table.horizontalHeader().setStretchLastSection(True)


# --------------
# Main Window
# --------------
class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle(APP_TITLE)
        self.resize(1200, 800)

        tb = QToolBar("Main")
        tb.setMovable(False)
        self.addToolBar(tb)
        open_act = QAction("Open .xlsx", self)
        open_act.triggered.connect(self._open_file_dialog)
        tb.addAction(open_act)

        self.status = QStatusBar(self)
        self.setStatusBar(self.status)

        central = QWidget(self)
        outer = QVBoxLayout(central)

        self.bar = HomeBar(
            on_home=self._show_home,
            on_add_set=self._open_file_dialog,
            on_open_saved=self._show_saved_wall,
            on_save_current=self._save_current_as,
        )
        outer.addWidget(self.bar)

        self.stack = QStackedWidget(self)
        outer.addWidget(self.stack, 1)

        self.home = QWidget()
        hv = QVBoxLayout(self.home)
        title = QLabel("The Breakers Companion")
        title.setAlignment(Qt.AlignCenter)
        title.setStyleSheet("font-size: 26px; font-weight: 700;")
        hv.addStretch(1)
        hv.addWidget(title)
        hv.addStretch(2)

        self.saved_wall = SavedSetsWall(self._open_saved_path, self._show_home)
        self.table = TablePage()

        self.stack.addWidget(self.home)       # 0
        self.stack.addWidget(self.saved_wall) # 1
        self.stack.addWidget(self.table)      # 2

        self.setCentralWidget(central)

        # Debounced search
        self._debounce = QTimer(self)
        self._debounce.setInterval(200)
        self._debounce.setSingleShot(True)
        self.bar.searchLine().textChanged.connect(lambda _: self._debounce.start())
        self._debounce.timeout.connect(self._apply_search)

        # State
        self._current_path: Optional[Path] = None

        self._show_home()

    # ----- Nav
    def _show_home(self):
        self.stack.setCurrentIndex(0)
        self.status.showMessage("Ready", 1500)

    def _show_saved_wall(self):
        self.saved_wall.refresh()
        self.stack.setCurrentIndex(1)
        self.status.clearMessage()

    def _show_table(self):
        self.stack.setCurrentIndex(2)
        self.status.clearMessage()

    # ----- Search
    def _apply_search(self):
        self.table.proxy.setFilterQuery(self.bar.searchLine().text())

    # ----- File ops
    def _open_file_dialog(self):
        path_str, _ = QFileDialog.getOpenFileName(
            self,
            "Open Set (.xlsx)",
            str(Path.home()),
            "Excel Files (*.xlsx)"
        )
        if not path_str:
            return
        self._open_path(Path(path_str))

    def _open_saved_path(self, p: Path):
        self._open_path(p)

    def _open_path(self, p: Path):
        try:
            self.status.showMessage(f"Loading {p.name} …")
            df = pd.read_excel(p, engine=EXCEL_ENGINE)
            df.columns = [str(c) if c is not None else "" for c in df.columns]
            self.table.set_dataframe(df)
            push_recent(p)
            self._current_path = p
            self._show_table()
            self.status.showMessage(f"Loaded {p.name} — {len(df):,} rows × {df.shape[1]} cols", 5000)
        except Exception as e:
            QMessageBox.critical(self, "Load Error", f"Failed to open file:\n{p}\n\n{e}")

    def _save_current_as(self):
        if self._current_path is None:
            QMessageBox.information(self, "No Set Loaded", "Open a set before saving.")
            return
        dest, _ = QFileDialog.getSaveFileName(
            self,
            "Save Current As…",
            str(self._current_path.with_suffix(".xlsx")),
            "Excel Files (*.xlsx)"
        )
        if not dest:
            return
        try:
            df = self.table.src_model.dataframe()
            if df is None or df.empty:
                QMessageBox.information(self, "Nothing to Save", "No data to save.")
                return
            df.to_excel(dest, index=False, engine=EXCEL_ENGINE)
            self.status.showMessage(f"Saved copy to {Path(dest).name}", 4000)
        except Exception as e:
            QMessageBox.critical(self, "Save Error", f"Failed to save:\n{dest}\n\n{e}")


# ----------
# Entry
# ----------
def main():
    app = QApplication(sys.argv)
    app.setApplicationName(APP_TITLE)
    w = MainWindow()
    w.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
