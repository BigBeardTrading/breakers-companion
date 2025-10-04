# app.py — Breakers Companion (with TEST data isolation via BC_DATA_DIR)
import os, sys, shutil, logging, json, webbrowser, traceback
from pathlib import Path

import pandas as pd

from PySide6.QtCore import Qt, QAbstractTableModel, QModelIndex, QSortFilterProxyModel, QSettings, QByteArray
from PySide6.QtGui import QAction, QIcon
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QFileDialog, QTableView, QStatusBar, QToolBar,
    QLineEdit, QMessageBox, QWidget, QVBoxLayout, QMenu, QMenuBar
)

APP_NAME = "The Breakers Companion"
ORG_NAME = "Big Beard Trading"
GITHUB_RELEASES = "https://github.com/BigBeardTrading/breakers-companion/releases"

# ---------- TEST awareness (uses BC_DATA_DIR to isolate data/settings) ----------
IS_TEST = bool(os.getenv("BC_DATA_DIR"))
APP_NAME_DISPLAY = APP_NAME + (" TEST" if IS_TEST else "")

# ---------- helpers ----------
def resource_root() -> Path:
    """Where bundled resources live (PyInstaller-safe)."""
    return Path(getattr(sys, "_MEIPASS", Path.cwd()))

def app_assets() -> Path:
    return resource_root() / "assets"

def read_version() -> str:
    for p in (resource_root() / "VERSION", Path(__file__).with_name("VERSION")):
        if p.exists():
            return p.read_text(encoding="utf-8").strip()
    return "0.0.0"

APP_VERSION = read_version()

def user_data_dir() -> Path:
    """Local data folder. If BC_DATA_DIR is set, use it (for TEST builds)."""
    override = os.getenv("BC_DATA_DIR")
    if override:
        d = Path(override)
    else:
        d = Path(os.getenv("LOCALAPPDATA", Path.home())) / "BreakersCompanion"
    d.mkdir(parents=True, exist_ok=True)
    return d

def sets_dir() -> Path:
    d = user_data_dir() / "sets"
    d.mkdir(parents=True, exist_ok=True)
    return d

def logs_dir() -> Path:
    d = user_data_dir() / "logs"
    d.mkdir(parents=True, exist_ok=True)
    return d

# logging
logging.basicConfig(
    filename=str(logs_dir() / "app.log"),
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)

def migrate_sets_once():
    """First-run copy of any bundled .xlsx into user sets folder."""
    flag = user_data_dir() / ".migrated"
    if flag.exists():
        return
    candidates: list[Path] = []

    base = Path(sys.executable).parent if getattr(sys, "frozen", False) else Path.cwd()
    for sub in ("data", "sets"):
        p = base / sub
        if p.is_dir():
            candidates.append(p)
    script_sets = Path(__file__).with_name("sets")
    if script_sets.is_dir():
        candidates.append(script_sets)

    moved = 0
    for folder in candidates:
        for p in folder.glob("*.xlsx"):
            dst = sets_dir() / p.name
            try:
                if p.resolve() != dst.resolve():
                    shutil.copy2(p, dst)
                    moved += 1
            except Exception as e:
                logging.exception(f"Failed to move {p} -> {dst}: {e}")
    flag.touch()
    if moved:
        logging.info(f"Migrated {moved} set file(s) to {sets_dir()}")

# ---------- DataFrame model ----------
class DataFrameModel(QAbstractTableModel):
    def __init__(self, df: pd.DataFrame):
        super().__init__()
        self._df = df

    def rowCount(self, parent=QModelIndex()):
        return 0 if parent.isValid() else len(self._df)

    def columnCount(self, parent=QModelIndex()):
        return 0 if parent.isValid() else len(self._df.columns)

    def data(self, index, role=Qt.DisplayRole):
        if not index.isValid():
            return None
        value = self._df.iat[index.row(), index.column()]
        colname = self._df.columns[index.column()]
        if role in (Qt.DisplayRole, Qt.EditRole):
            if str(colname).lower() == "owned" and role == Qt.DisplayRole:
                return "✓" if bool(value) else ""
            return "" if pd.isna(value) else str(value)
        if role == Qt.TextAlignmentRole:
            return Qt.AlignLeft | Qt.AlignVCenter
        return None

    def headerData(self, section, orientation, role=Qt.DisplayRole):
        if role != Qt.DisplayRole:
            return None
        if orientation == Qt.Horizontal:
            return str(self._df.columns[section])
        return str(section + 1)

    def flags(self, index):
        base = Qt.ItemIsSelectable | Qt.ItemIsEnabled
        colname = self._df.columns[index.column()].lower()
        if colname == "owned":
            return base | Qt.ItemIsEditable | Qt.ItemIsUserCheckable
        return base  # other columns read-only for now

    def setData(self, index, value, role=Qt.EditRole):
        if not index.isValid():
            return False
        colname = self._df.columns[index.column()].lower()
        if colname == "owned":
            cur = bool(self._df.iat[index.row(), index.column()])
            self._df.iat[index.row(), index.column()] = not cur
            self.dataChanged.emit(index, index, [Qt.DisplayRole, Qt.EditRole])
            return True
        return False

    def dataframe(self) -> pd.DataFrame:
        return self._df

# ---------- Main Window ----------
class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowIcon(QIcon(str(app_assets() / "BBT_BreakersCompanion.ico")))
        self.current_path: Path | None = None
        self.dirty = False

        # settings (namespaced by APP_NAME_DISPLAY so TEST is separate)
        self.settings = QSettings(ORG_NAME, APP_NAME_DISPLAY)
        try:
            self.recent_files: list[str] = json.loads(self.settings.value("recentFiles", "[]"))
        except Exception:
            self.recent_files = []
        self.dark = self.settings.value("dark", "false") == "true"

        # UI
        self.table = QTableView(self)
        self.table.setSortingEnabled(True)
        self.table.doubleClicked.connect(self.on_double_click)

        self.filter_edit = QLineEdit(self)
        self.filter_edit.setPlaceholderText("Filter (player/team/card #)…  |  Esc clears")
        self.filter_edit.textChanged.connect(self.apply_filter)

        central = QWidget(self)
        lay = QVBoxLayout(central)
        lay.addWidget(self.filter_edit)
        lay.addWidget(self.table)
        self.setCentralWidget(central)

        # status bar
        sb = QStatusBar(self)
        self.setStatusBar(sb)

        # menus + actions
        self._make_menus()
        self._apply_theme(self.dark)

        # restore geometry/state
        g = self.settings.value("geom", None)
        s = self.settings.value("state", None)
        if isinstance(g, QByteArray):
            self.restoreGeometry(g)
        if isinstance(s, QByteArray):
            self.restoreState(s)

        self.update_title()
        self.update_status()

        # drag & drop
        self.setAcceptDrops(True)

        # open last file if exists
        last = self.settings.value("lastFile", "")
        if last and Path(last).exists():
            self.load_file(Path(last))

    # ----- menus / actions
    def _make_menus(self):
        menubar = QMenuBar(self)
        self.setMenuBar(menubar)

        # File
        file_menu = QMenu("&File", self)
        act_open = QAction("Open set…", self, shortcut="Ctrl+O", triggered=self.open_dialog)
        act_save = QAction("Save", self, shortcut="Ctrl+S", triggered=self.save)
        act_save_as = QAction("Save As…", self, shortcut="Ctrl+Shift+S", triggered=self.save_as)
        act_export = QAction("Export CSV…", self, triggered=self.export_csv)
        act_exit = QAction("Exit", self, shortcut="Ctrl+Q", triggered=self.close)
        file_menu.addActions([act_open, act_save, act_save_as, act_export])
        # recent files submenu
        self.recent_menu = QMenu("Open &Recent", self)
        self.refresh_recent_menu()
        file_menu.addMenu(self.recent_menu)
        file_menu.addSeparator()
        file_menu.addAction(act_exit)
        menubar.addMenu(file_menu)

        # View
        view_menu = QMenu("&View", self)
        self.dark_act = QAction("Dark mode", self, checkable=True, checked=self.dark, triggered=self.toggle_dark)
        view_menu.addAction(self.dark_act)
        menubar.addMenu(view_menu)

        # Help
        help_menu = QMenu("&Help", self)
        about = QAction("About", self, triggered=self.show_about)
        upd = QAction("Check for updates…", self, triggered=lambda: webbrowser.open(GITHUB_RELEASES))
        help_menu.addActions([about, upd])
        menubar.addMenu(help_menu)

        # toolbar quick buttons
        tb = QToolBar("Main", self)
        tb.addAction(act_open)
        tb.addAction(act_save)
        tb.addAction(self.dark_act)
        self.addToolBar(tb)

    # ----- file ops
    def open_dialog(self):
        start = str(sets_dir())
        path_str, _ = QFileDialog.getOpenFileName(self, "Open set (.xlsx)", start, "Excel (*.xlsx)")
        if path_str:
            self.load_file(Path(path_str))

    def load_file(self, path: Path):
        try:
            df = pd.read_excel(path)
        except Exception as e:
            QMessageBox.critical(self, "Open failed", f"Could not read:\n{path}\n\n{e}")
            return

        if "Owned" not in df.columns:
            df.insert(0, "Owned", False)
        df["Owned"] = df["Owned"].astype(bool)

        self._df_model = DataFrameModel(df)
        self._proxy = QSortFilterProxyModel(self)
        self._proxy.setSourceModel(self._df_model)
        self._proxy.setFilterCaseSensitivity(Qt.CaseInsensitive)
        self._proxy.setFilterKeyColumn(-1)  # search all columns

        self.table.setModel(self._proxy)
        self.table.resizeColumnsToContents()
        self.table.horizontalHeader().setStretchLastSection(True)

        self.current_path = Path(path)
        self.dirty = False
        self._touch_recent(str(path))
        self.settings.setValue("lastFile", str(path))
        self.update_title()
        self.update_status()

    def save(self):
        if not hasattr(self, "_df_model"):
            return
        if not self.current_path:
            return self.save_as()
        try:
            df = self._df_model.dataframe()
            df.to_excel(self.current_path, index=False)
            self.dirty = False
            self.update_status("Saved.")
        except Exception as e:
            logging.exception("Save failed")
            QMessageBox.critical(self, "Save failed", f"Could not save:\n{self.current_path}\n\n{e}")

    def save_as(self):
        if not hasattr(self, "_df_model"):
            return
        start = str(self.current_path.parent if self.current_path else sets_dir())
        path_str, _ = QFileDialog.getSaveFileName(self, "Save As", start, "Excel (*.xlsx)")
        if path_str:
            self.current_path = Path(path_str)
            self.save()
            self._touch_recent(path_str)
            self.update_title()

    def export_csv(self):
        if not hasattr(self, "_df_model"):
            return
        start = str(self.current_path.parent if self.current_path else sets_dir())
        path_str, _ = QFileDialog.getSaveFileName(self, "Export CSV", start, "CSV (*.csv)")
        if path_str:
            try:
                self._df_model.dataframe().to_csv(path_str, index=False)
                self.update_status("Exported CSV.")
            except Exception as e:
                QMessageBox.critical(self, "Export failed", f"Could not export CSV:\n{e}")

    # ----- UI bits
    def on_double_click(self, index):
        if not index.isValid():
            return
        src_index = self._proxy.mapToSource(index)
        col = self._df_model.dataframe().columns[src_index.column()]
        if str(col).lower() == "owned":
            self._df_model.setData(src_index, True, Qt.EditRole)
            self.dirty = True
            self.update_status()

    def apply_filter(self, text: str):
        self._proxy.setFilterFixedString(text)
        self.update_status()

    def update_status(self, msg: str | None = None):
        if msg is None and hasattr(self, "_df_model"):
            df = self._df_model.dataframe()
            total = len(df)
            owned = int(df["Owned"].sum()) if "Owned" in df.columns else 0
            msg = f"Rows: {total}   Owned: {owned}   Sets: {sets_dir()}"
        self.statusBar().showMessage(msg or "")

    def update_title(self):
        name = self.current_path.name if self.current_path else "No set loaded"
        dirty = " *" if self.dirty else ""
        self.setWindowTitle(f"{APP_NAME_DISPLAY} v{APP_VERSION} — {name}{dirty}")

    def toggle_dark(self, checked):
        self.dark = checked
        self._apply_theme(self.dark)
        self.settings.setValue("dark", "true" if self.dark else "false")

    def _apply_theme(self, dark: bool):
        if dark:
            self.setStyleSheet("""
                QMainWindow, QWidget { background: #151515; color: #e6e6e6; }
                QLineEdit { background: #1e1e1e; border:1px solid #333; padding:4px; }
                QTableView { gridline-color:#333; background:#1a1a1a; }
                QHeaderView::section { background:#202020; color:#ddd; border:1px solid #333; }
                QMenuBar, QMenu { background:#1a1a1a; color:#e6e6e6; }
                QStatusBar { background:#202020; }
            """)
        else:
            self.setStyleSheet("")

    def show_about(self):
        QMessageBox.information(
            self, "About",
            f"{APP_NAME_DISPLAY}\nVersion {APP_VERSION}\n© {ORG_NAME}\n\n"
            "Open/Save Excel sets (.xlsx), toggle 'Owned', filter, export CSV.\n"
            "Releases: " + GITHUB_RELEASES
        )

    # ----- recent files
    def _touch_recent(self, path_str: str):
        if path_str in self.recent_files:
            self.recent_files.remove(path_str)
        self.recent_files.insert(0, path_str)
        self.recent_files = self.recent_files[:5]
        self.settings.setValue("recentFiles", json.dumps(self.recent_files))
        self.refresh_recent_menu()

    def refresh_recent_menu(self):
        self.recent_menu.clear()
        if not self.recent_files:
            a = QAction("(empty)", self); a.setEnabled(False); self.recent_menu.addAction(a)
            return
        for p in self.recent_files:
            act = QAction(p, self)
            act.triggered.connect(lambda chk=False, s=p: self.load_file(Path(s)) if Path(s).exists() else QMessageBox.warning(self, "Missing", f"File not found:\n{s}"))
            self.recent_menu.addAction(act)

    # ----- drag & drop
    def dragEnterEvent(self, e):
        if e.mimeData().hasUrls() and any(u.toString().lower().endswith(".xlsx") for u in e.mimeData().urls()):
            e.acceptProposedAction()

    def dropEvent(self, e):
        for u in e.mimeData().urls():
            if u.isLocalFile() and u.toLocalFile().lower().endswith(".xlsx"):
                self.load_file(Path(u.toLocalFile()))
                break

    # ----- close & errors
    def closeEvent(self, ev):
        try:
            self.settings.setValue("geom", self.saveGeometry())
            self.settings.setValue("state", self.saveState())
        except Exception:
            pass
        if self.dirty and hasattr(self, "_df_model"):
            r = QMessageBox.question(self, "Unsaved changes", "Save changes before exit?",
                                     QMessageBox.Yes | QMessageBox.No | QMessageBox.Cancel, QMessageBox.Yes)
            if r == QMessageBox.Yes:
                self.save()
            elif r == QMessageBox.Cancel:
                ev.ignore()
                return
        super().closeEvent(ev)

# ---------- main ----------
def main():
    try:
        migrate_sets_once()
        app = QApplication(sys.argv)
        w = MainWindow()
        w.resize(1100, 700)
        w.show()
        sys.exit(app.exec())
    except Exception:
        logging.exception("Fatal crash:\n" + traceback.format_exc())
        raise

if __name__ == "__main__":
    main()
