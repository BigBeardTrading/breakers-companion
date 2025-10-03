# app.py — The Breakers Companion (v2.0)
# Requires: PySide6, pandas, openpyxl

import os, sys, shutil, json
from pathlib import Path

from PySide6.QtCore import Qt, QAbstractTableModel, QModelIndex, QSize
from PySide6.QtGui import QIcon, QAction
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QFileDialog, QTableView, QLineEdit, QFrame, QMessageBox,
    QStatusBar
)

# -----------------------------
# Helpers for bundled resources
# -----------------------------
def resource_path(*relative_parts: str) -> str:
    """
    Resolve a file path that works for both source runs and PyInstaller onefile.
    """
    if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
        base = Path(sys._MEIPASS)  # type: ignore
    else:
        base = Path(__file__).parent
    return str(base.joinpath(*relative_parts))

APP_NAME = "Breakers Companion"
APP_VERSION = "v2.0"
APP_ID_DIR = Path(os.environ.get("LOCALAPPDATA", str(Path.home()))) / "BreakersCompanion"
SETS_DIR = APP_ID_DIR / "sets"
CONFIG_PATH = APP_ID_DIR / "config.json"
DEFAULT_SET_NAME = "2025 Donruss Football Master Checklist.xlsx"
DEFAULT_SET_SRC = resource_path("data", DEFAULT_SET_NAME)

# -----------------------------
# First-run setup
# -----------------------------
def ensure_app_dirs():
    APP_ID_DIR.mkdir(parents=True, exist_ok=True)
    SETS_DIR.mkdir(parents=True, exist_ok=True)
    if not CONFIG_PATH.exists():
        CONFIG_PATH.write_text(json.dumps({"recent": []}, indent=2))

def seed_default_set():
    dst = SETS_DIR / DEFAULT_SET_NAME
    if os.path.exists(DEFAULT_SET_SRC) and not dst.exists():
        try:
            shutil.copy2(DEFAULT_SET_SRC, dst)
        except Exception:
            pass

# -----------------------------
# Minimal Pandas -> Qt Model
# -----------------------------
import pandas as pd

class PandasModel(QAbstractTableModel):
    def __init__(self, df: pd.DataFrame):
        super().__init__()
        self._df = df.copy()
        self._display = self._df

    def rowCount(self, parent=QModelIndex()):
        return 0 if parent.isValid() else len(self._display)

    def columnCount(self, parent=QModelIndex()):
        return 0 if parent.isValid() else len(self._display.columns)

    def data(self, index, role=Qt.DisplayRole):
        if not index.isValid():
            return None
        if role in (Qt.DisplayRole, Qt.EditRole):
            val = self._display.iat[index.row(), index.column()]
            return "" if pd.isna(val) else str(val)
        return None

    def headerData(self, section, orientation, role=Qt.DisplayRole):
        if role != Qt.DisplayRole:
            return None
        if orientation == Qt.Horizontal:
            return str(self._display.columns[section])
        return str(section + 1)

    # simple filter
    def filter(self, text: str):
        if not text.strip():
            self._display = self._df
        else:
            t = text.strip().lower()
            mask = pd.Series(False, index=self._df.index)
            for col in self._df.columns:
                try:
                    mask = mask | self._df[col].astype(str).str.lower().str.contains(t, na=False)
                except Exception:
                    pass
            self._display = self._df[mask]
        self.layoutChanged.emit()

# -----------------------------
# Main Window
# -----------------------------
class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle(f"{APP_NAME} — {APP_VERSION}")
        self.setWindowIcon(QIcon(resource_path("assets", "BBT_BreakersCompanion.ico")))
        self.resize(1200, 800)

        # Central
        central = QWidget()
        self.setCentralWidget(central)
        root = QVBoxLayout(central)
        root.setContentsMargins(0, 0, 0, 0)

        # Header strip with logo left, version right
        header = QWidget()
        header.setObjectName("HeaderBar")
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(16, 10, 16, 10)

        logo = QLabel()
        logo.setPixmap(QIcon(resource_path("assets", "bbt.png")).pixmap(QSize(40, 40)))
        logo.setToolTip("Big Beard Trading")
        title = QLabel(f"<b style='font-size:20px;'>The Breakers Companion</b>")
        title.setTextFormat(Qt.RichText)

        left_box = QHBoxLayout()
        left_box.addWidget(logo)
        left_box.addSpacing(10)
        left_box.addWidget(title)
        left_box.addStretch(1)

        version = QLabel(f"{APP_VERSION}")
        version.setObjectName("VersionTag")
        version.setAlignment(Qt.AlignRight | Qt.AlignVCenter)

        header_layout.addLayout(left_box)
        header_layout.addWidget(version)
        root.addWidget(header)

        # Toolbar row (clean: Home, Add Set, Open Saved Sets, Save Current)
        tools = QWidget()
        tools_layout = QHBoxLayout(tools)
        tools_layout.setContentsMargins(16, 8, 16, 8)

        self.btn_home = QPushButton("Home")
        self.btn_add = QPushButton("Add Set")
        self.btn_open = QPushButton("Open Saved Sets")
        self.btn_save = QPushButton("Save Current As…")

        for b in (self.btn_home, self.btn_add, self.btn_open, self.btn_save):
            b.setCursor(Qt.PointingHandCursor)

        tools_layout.addWidget(self.btn_home)
        tools_layout.addSpacing(12)
        tools_layout.addWidget(self.btn_add)
        tools_layout.addWidget(self.btn_open)
        tools_layout.addWidget(self.btn_save)
        tools_layout.addStretch(1)

        # quick search
        tools_layout.addWidget(QLabel("Search:"))
        self.search = QLineEdit()
        self.search.setPlaceholderText("Player, Team, Subset, etc.")
        tools_layout.addWidget(self.search)

        root.addWidget(tools)

        # Divider
        line = QFrame()
        line.setFrameShape(QFrame.HLine)
        line.setFrameShadow(QFrame.Sunken)
        root.addWidget(line)

        # Table
        self.table = QTableView()
        self.table.setSortingEnabled(True)
        root.addWidget(self.table, stretch=1)

        # Status bar
        sb = QStatusBar()
        self.setStatusBar(sb)
        sb.showMessage("Ready")

        # Connects
        self.btn_home.clicked.connect(self.on_home)
        self.btn_add.clicked.connect(self.on_add_set)
        self.btn_open.clicked.connect(self.on_open_saved)
        self.btn_save.clicked.connect(self.on_save_as)
        self.search.textChanged.connect(self.on_search)

        # Load default
        self.current_path = None
        self.model = None
        self.apply_styles()
        self.ensure_seed_and_load()

    def apply_styles(self):
        # soft grayscale background & tag styles
        bg_path = resource_path("assets", "Background.png").replace("\\", "/")
        self.setStyleSheet(f"""
            QMainWindow {{
                background-image: url("{bg_path}");
                background-attachment: fixed;
                background-position: center;
            }}
            #HeaderBar {{
                background: rgba(0,0,0,0.55);
                color: white;
            }}
            #VersionTag {{
                color: #eaeaea;
                padding: 4px 8px;
                border: 1px solid rgba(255,255,255,0.25);
                border-radius: 8px;
                font-weight: 600;
            }}
            QPushButton {{
                padding: 6px 12px;
                border: 1px solid rgba(0,0,0,0.15);
                border-radius: 8px;
                background: rgba(255,255,255,0.85);
            }}
            QPushButton:hover {{
                background: white;
            }}
            QLineEdit {{
                padding: 6px 10px;
                border-radius: 8px;
                background: rgba(255,255,255,0.95);
            }}
            QTableView {{
                background: rgba(255,255,255,0.95);
                gridline-color: #ddd;
            }}
        """)

    def ensure_seed_and_load(self):
        ensure_app_dirs()
        seed_default_set()
        default_file = SETS_DIR / DEFAULT_SET_NAME
        if default_file.exists():
            self.load_file(default_file)
        else:
            QMessageBox.information(self, APP_NAME, "Click **Add Set** to import your first checklist.")

    # ---------- actions ----------
    def on_home(self):
        # For now, home just clears the search
        self.search.clear()
        self.statusBar().showMessage("Home")

    def on_add_set(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Add Set (Excel)", str(Path.home()),
            "Excel Files (*.xlsx *.xls)"
        )
        if not path:
            return
        # copy into SETS_DIR
        SETS_DIR.mkdir(parents=True, exist_ok=True)
        dst = SETS_DIR / Path(path).name
        try:
            shutil.copy2(path, dst)
            self.load_file(dst)
            self.statusBar().showMessage(f"Imported: {dst.name}")
        except Exception as e:
            QMessageBox.warning(self, APP_NAME, f"Failed to import:\n{e}")

    def on_open_saved(self):
        # open a picker inside SETS_DIR
        start = str(SETS_DIR if SETS_DIR.exists() else Path.home())
        path, _ = QFileDialog.getOpenFileName(
            self, "Open Saved Set", start, "Excel Files (*.xlsx *.xls)"
        )
        if path:
            self.load_file(Path(path))

    def on_save_as(self):
        if self.model is None or self.current_path is None:
            QMessageBox.information(self, APP_NAME, "No set is loaded.")
            return
        path, _ = QFileDialog.getSaveFileName(
            self, "Save Current As", str(SETS_DIR), "Excel Files (*.xlsx)"
        )
        if not path:
            return
        try:
            # Save displayed (filtered or not) to xlsx
            df = self.model._display  # current view
            df.to_excel(path, index=False)
            self.statusBar().showMessage(f"Saved: {Path(path).name}")
        except Exception as e:
            QMessageBox.warning(self, APP_NAME, f"Save failed:\n{e}")

    def on_search(self, text: str):
        if self.model:
            self.model.filter(text)

    # ---------- core ----------
    def load_file(self, path: Path):
        try:
            df = pd.read_excel(str(path))
            # If the template has a header row offset, you can massage here later.
            self.model = PandasModel(df)
            self.table.setModel(self.model)
            self.current_path = path
            self.setWindowTitle(f"{APP_NAME} — {APP_VERSION} — {path.name}")
            self.statusBar().showMessage(f"Loaded {path.name} ({len(df)} rows)")
            self.remember_recent(path)
        except Exception as e:
            QMessageBox.critical(self, APP_NAME, f"Could not load file:\n{e}")

    def remember_recent(self, path: Path):
        try:
            data = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
        except Exception:
            data = {"recent": []}
        recent = [str(path)] + [p for p in data.get("recent", []) if p != str(path)]
        data["recent"] = recent[:10]
        CONFIG_PATH.write_text(json.dumps(data, indent=2))

# -----------------------------
# Entry
# -----------------------------
def main():
    ensure_app_dirs()
    seed_default_set()

    app = QApplication(sys.argv)
    win = MainWindow()

    # Minimal menu with Quit (kept super clean)
    menu = win.menuBar().addMenu("File")
    act_quit = QAction("Quit", win)
    act_quit.triggered.connect(app.quit)
    menu.addAction(act_quit)

    win.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
