"""
Main Window — PhysioSkeptic
Left sidebar + stacked content + toolbar + status bar.
Professional dark medical UI.
"""
from __future__ import annotations

import time
from typing import Optional, Dict

from PySide6.QtWidgets import (
    QMainWindow, QWidget, QHBoxLayout, QVBoxLayout, QLabel, QFrame,
    QPushButton, QStackedWidget, QSplitter, QStatusBar, QToolBar,
    QComboBox, QSizePolicy, QSpacerItem, QScrollArea,
    QLineEdit, QProgressBar,
)
from PySide6.QtCore import Qt, QTimer, Signal, QSize
from PySide6.QtGui import QFont, QColor, QPalette, QIcon

from .theme import (
    BG_SIDEBAR, BG_MAIN, ACCENT, SUCCESS, DANGER, WARNING,
    TEXT_PRIMARY, TEXT_SECONDARY, BORDER,
)
from .widgets.nav_button import NavButton
from .pages.dashboard import DashboardPage
from .pages.signal_import import SignalImportPage
from .pages.analysis import AnalysisPage
from .pages.debate_viewer import DebateViewerPage
from .pages.batch import BatchPage
from .pages.history import HistoryPage
from .pages.settings import SettingsPage

from core.database import Database
from core.api_client import APIClientFactory


class _StatusDot(QLabel):
    """Small colored dot for API connection status."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setFixedSize(10, 10)
        self.set_status("unknown")

    def set_status(self, status: str) -> None:
        color = {
            "ok": SUCCESS,
            "error": DANGER,
            "unknown": "#484f58",
            "testing": WARNING,
        }.get(status, "#484f58")
        self.setStyleSheet(
            f"background-color: {color}; border-radius: 5px; border: none;"
        )
        self.setToolTip(f"API: {status}")


class Sidebar(QFrame):
    """Collapsible left sidebar with nav items."""

    nav_clicked = Signal(int)   # page index
    collapse_toggled = Signal(bool)

    EXPANDED_WIDTH = 210
    COLLAPSED_WIDTH = 52

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setObjectName("Sidebar")
        self._collapsed = False
        self._nav_buttons: list[NavButton] = []
        self._build_ui()

    def _build_ui(self) -> None:
        self.setFixedWidth(self.EXPANDED_WIDTH)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        # ── Logo area ──────────────────────────────────────────────────────
        logo_frame = QFrame()
        logo_frame.setFixedHeight(78)
        logo_frame.setStyleSheet(
            "background: qlineargradient(x1:0,y1:0,x2:0,y2:1,"
            "stop:0 #111820, stop:1 #0e1318);"
            "border-bottom: 1px solid #1a2535;"
        )
        logo_lay = QVBoxLayout(logo_frame)
        logo_lay.setContentsMargins(14, 14, 8, 8)
        logo_lay.setSpacing(2)

        name_row = QHBoxLayout()
        self._logo_lbl = QLabel("PhysioSkeptic")
        self._logo_lbl.setObjectName("SidebarLogo")
        lf = QFont("Segoe UI", 13, QFont.Bold)
        self._logo_lbl.setFont(lf)
        name_row.addWidget(self._logo_lbl)
        name_row.addStretch()

        # collapse toggle — small arrow, top-right of logo area
        self._collapse_btn = QPushButton("‹")
        self._collapse_btn.setObjectName("FlatButton")
        self._collapse_btn.setFixedSize(24, 24)
        self._collapse_btn.setToolTip("Collapse sidebar")
        self._collapse_btn.clicked.connect(self._toggle_collapse)
        name_row.addWidget(self._collapse_btn)
        logo_lay.addLayout(name_row)

        self._logo_tag = QLabel("SQI-Anchored Rhythm Diagnosis")
        self._logo_tag.setObjectName("SidebarTagline")
        logo_lay.addWidget(self._logo_tag)

        outer.addWidget(logo_frame)

        outer.addSpacing(6)

        # ── Nav items ──────────────────────────────────────────────────────
        # Section label
        sec_core = QLabel("WORKSPACE")
        sec_core.setObjectName("SidebarSection")
        outer.addWidget(sec_core)

        NAV_ITEMS = [
            ("Dashboard",     "⬡"),
            ("Signal Import", "↑"),
            ("Analysis",      "◎"),
            ("Debate Viewer", "≡"),
            ("Batch",         "⊟"),
        ]
        NAV_ITEMS_2 = [
            ("History",   "◷"),
            ("Settings",  "⚙"),
        ]

        for idx, (label, icon) in enumerate(NAV_ITEMS):
            btn = NavButton(f"  {icon}  {label}")
            btn.clicked.connect(lambda checked=False, i=idx: self.nav_clicked.emit(i))
            self._nav_buttons.append(btn)
            outer.addWidget(btn)

        outer.addSpacing(6)
        sec_data = QLabel("MANAGE")
        sec_data.setObjectName("SidebarSection")
        outer.addWidget(sec_data)

        for idx2, (label, icon) in enumerate(NAV_ITEMS_2):
            idx = len(NAV_ITEMS) + idx2
            btn = NavButton(f"  {icon}  {label}")
            btn.clicked.connect(lambda checked=False, i=idx: self.nav_clicked.emit(i))
            self._nav_buttons.append(btn)
            outer.addWidget(btn)

        outer.addStretch()

        # ── bottom: version ────────────────────────────────────────────────
        ver = QLabel("v 1.0.0  ·  Research only")
        ver.setObjectName("SidebarVersion")
        ver.setContentsMargins(14, 0, 0, 10)
        outer.addWidget(ver)

    def set_active_page(self, idx: int) -> None:
        for i, btn in enumerate(self._nav_buttons):
            btn.set_active(i == idx)

    def _toggle_collapse(self) -> None:
        self._collapsed = not self._collapsed
        w = self.COLLAPSED_WIDTH if self._collapsed else self.EXPANDED_WIDTH
        self.setFixedWidth(w)

        if self._collapsed:
            self._logo_lbl.setText("PS")
            self._logo_tag.setVisible(False)
            self._collapse_btn.setText("›")
            self._collapse_btn.setToolTip("Expand sidebar")
            for btn in self._nav_buttons:
                btn.set_collapsed(True)
        else:
            self._logo_lbl.setText("PhysioSkeptic")
            self._logo_tag.setVisible(True)
            self._collapse_btn.setText("‹")
            self._collapse_btn.setToolTip("Collapse sidebar")
            for btn in self._nav_buttons:
                btn.set_collapsed(False)

        self.collapse_toggled.emit(self._collapsed)


class MainWindow(QMainWindow):
    """PhysioSkeptic main application window."""

    def __init__(self) -> None:
        super().__init__()
        self._db = Database()
        # Seed demo data on first run
        if self._db.count_results() == 0:
            self._db.seed_demo_data(18)

        self._t_session_start = time.time()
        self._token_count = 0
        self._current_page = 0

        self._setup_window()
        self._build_ui()
        self._connect_signals()
        self._nav_to(0)   # show dashboard
        self._start_status_timer()

    # ── window setup ──────────────────────────────────────────────────────────

    def _setup_window(self) -> None:
        self.setWindowTitle("PhysioSkeptic — Multi-Agent Cardiac Rhythm Analysis")
        self.setMinimumSize(1200, 780)
        self.resize(1440, 900)

    # ── build UI ──────────────────────────────────────────────────────────────

    def _build_ui(self) -> None:
        # ── Toolbar ─────────────────────────────────────────────────────────
        self._toolbar = QToolBar("Main Toolbar")
        self._toolbar.setMovable(False)
        self._toolbar.setFloatable(False)
        self._toolbar.setIconSize(QSize(16, 16))
        self._toolbar.setFixedHeight(46)

        session_lbl = QLabel("  Session: ")
        session_lbl.setObjectName("SubLabel")
        self._session_edit = QLineEdit("Untitled Session")
        self._session_edit.setFixedWidth(180)
        self._session_edit.setToolTip("Current session name")

        model_lbl = QLabel("  Model: ")
        model_lbl.setObjectName("SubLabel")
        self._model_combo = QComboBox()
        self._model_combo.addItems(APIClientFactory.list_display_names())
        self._model_combo.setCurrentText("Mock / Demo")
        self._model_combo.setFixedWidth(175)

        self._api_dot = _StatusDot()
        api_lbl = QLabel("  API ")
        api_lbl.setObjectName("SubLabel")

        self._toolbar.addWidget(session_lbl)
        self._toolbar.addWidget(self._session_edit)
        self._toolbar.addSeparator()
        self._toolbar.addWidget(model_lbl)
        self._toolbar.addWidget(self._model_combo)
        self._toolbar.addSeparator()
        self._toolbar.addWidget(api_lbl)
        self._toolbar.addWidget(self._api_dot)

        spacer = QWidget()
        spacer.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        self._toolbar.addWidget(spacer)

        help_btn = QPushButton("? Help")
        help_btn.setObjectName("FlatButton")
        help_btn.setFixedHeight(30)
        help_btn.clicked.connect(self._show_help)
        self._toolbar.addWidget(help_btn)
        self._toolbar.addSeparator()

        new_analysis_btn = QPushButton("+ New Analysis")
        new_analysis_btn.setProperty("primary", "true")
        new_analysis_btn.setFixedHeight(30)
        new_analysis_btn.clicked.connect(lambda: self._nav_to(2))
        self._toolbar.addWidget(new_analysis_btn)
        self._toolbar.addWidget(QLabel("  "))

        self.addToolBar(self._toolbar)

        # ── Status bar ───────────────────────────────────────────────────────
        self._statusbar = QStatusBar()
        self._statusbar.setObjectName("statusBar")

        self._sb_operation = QLabel("Ready")
        self._sb_progress = QProgressBar()
        self._sb_progress.setRange(0, 100)
        self._sb_progress.setValue(0)
        self._sb_progress.setTextVisible(False)
        self._sb_progress.setFixedWidth(120)
        self._sb_progress.setFixedHeight(10)
        self._sb_progress.setVisible(False)

        self._sb_time = QLabel("Session: 00:00")
        self._sb_time.setObjectName("SubLabel")
        self._sb_tokens = QLabel("Tokens: 0")
        self._sb_tokens.setObjectName("SubLabel")

        self._statusbar.addWidget(self._sb_operation)
        self._statusbar.addWidget(self._sb_progress)
        self._statusbar.addPermanentWidget(self._sb_tokens)
        self._statusbar.addPermanentWidget(self._sb_time)
        self.setStatusBar(self._statusbar)

        # ── Central widget ───────────────────────────────────────────────────
        central = QWidget()
        central.setObjectName("CentralWidget")
        root = QHBoxLayout(central)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # Sidebar
        self._sidebar = Sidebar()
        root.addWidget(self._sidebar)

        # Vertical divider
        vdiv = QFrame()
        vdiv.setObjectName("Divider")
        vdiv.setFixedWidth(1)
        root.addWidget(vdiv)

        # Content stack
        self._stack = QStackedWidget()
        root.addWidget(self._stack)

        self.setCentralWidget(central)

        # ── Pages ────────────────────────────────────────────────────────────
        self._dashboard    = DashboardPage(self._db)
        self._import_page  = SignalImportPage()
        self._analysis     = AnalysisPage(self._db)
        self._debate       = DebateViewerPage()
        self._batch        = BatchPage(self._db)
        self._history      = HistoryPage(self._db)
        self._settings_pg  = SettingsPage()

        for page in [
            self._dashboard, self._import_page, self._analysis,
            self._debate, self._batch, self._history, self._settings_pg,
        ]:
            self._stack.addWidget(page)

    # ── signals ───────────────────────────────────────────────────────────────

    def _connect_signals(self) -> None:
        self._sidebar.nav_clicked.connect(self._nav_to)

        # Dashboard quick actions
        self._dashboard.request_new_analysis.connect(lambda: self._nav_to(2))
        self._dashboard.request_import.connect(lambda: self._nav_to(1))
        self._dashboard.request_batch.connect(lambda: self._nav_to(4))

        # Signal import → analysis
        self._import_page.signal_loaded.connect(self._on_signal_imported)

        # Analysis complete → debate viewer
        self._analysis.analysis_complete.connect(self._on_analysis_complete)
        self._analysis.status_message.connect(self._on_status_message)

        # Settings
        self._settings_pg.theme_changed.connect(self._on_theme_changed)
        self._settings_pg.font_size_changed.connect(self._on_font_size_changed)

        # Global model combo sync
        self._model_combo.currentTextChanged.connect(self._on_global_model_changed)

    # ── navigation ────────────────────────────────────────────────────────────

    def _nav_to(self, idx: int) -> None:
        self._current_page = idx
        self._stack.setCurrentIndex(idx)
        self._sidebar.set_active_page(idx)

        page_names = [
            "Dashboard", "Signal Import", "Analysis",
            "Debate Viewer", "Batch", "History", "Settings",
        ]
        self.setWindowTitle(
            f"PhysioSkeptic — {page_names[idx] if idx < len(page_names) else ''}"
        )

        # Refresh history when navigating to it
        if idx == 5:
            self._history.refresh()
        elif idx == 0:
            self._dashboard.refresh()

        self._sb_operation.setText(page_names[idx] if idx < len(page_names) else "")

    # ── cross-page signals ────────────────────────────────────────────────────

    def _on_signal_imported(self, signal_data) -> None:
        self._analysis.load_signal(signal_data)
        self._nav_to(2)

    def _on_analysis_complete(self, result) -> None:
        self._debate.load_result(result)
        self._token_count += result.total_input_tokens + result.total_output_tokens
        self._sb_tokens.setText(f"Tokens: {self._token_count:,}")
        self._sb_operation.setText(
            f"Analysis complete: {result.rhythm} ({result.confidence*100:.0f}%)"
        )
        self._sb_progress.setVisible(False)
        # Prompt to view debate
        self._show_analysis_done_banner(result)

    def _on_status_message(self, message: str, pct: int) -> None:
        self._sb_operation.setText(message)
        self._sb_progress.setVisible(pct < 100)
        self._sb_progress.setValue(pct)

    def _on_global_model_changed(self, model_name: str) -> None:
        # Sync to analysis page combo
        try:
            idx = self._analysis._model_combo.findText(model_name)
            if idx >= 0:
                self._analysis._model_combo.setCurrentIndex(idx)
        except Exception:
            pass

    # ── theme / appearance ────────────────────────────────────────────────────

    def _on_theme_changed(self, theme: str) -> None:
        from .theme import get_stylesheet, get_light_stylesheet
        if theme == "light":
            self.setStyleSheet(get_light_stylesheet())
        else:
            self.setStyleSheet(get_stylesheet())

    def _on_font_size_changed(self, size: int) -> None:
        from .theme import get_stylesheet
        self.setStyleSheet(get_stylesheet(font_size=size))

    # ── timer ─────────────────────────────────────────────────────────────────

    def _start_status_timer(self) -> None:
        self._status_timer = QTimer()
        self._status_timer.setInterval(1000)
        self._status_timer.timeout.connect(self._update_time)
        self._status_timer.start()

    def _update_time(self) -> None:
        elapsed = int(time.time() - self._t_session_start)
        m, s = divmod(elapsed, 60)
        self._sb_time.setText(f"Session: {m:02d}:{s:02d}")

    # ── help ──────────────────────────────────────────────────────────────────

    def _show_help(self) -> None:
        from PySide6.QtWidgets import QMessageBox
        msg = QMessageBox(self)
        msg.setWindowTitle("PhysioSkeptic Help")
        msg.setIcon(QMessageBox.Icon.Information)
        msg.setText(
            "<b>PhysioSkeptic — Quick Start</b><br/><br/>"
            "<b>1. Import Signal:</b> Go to Signal Import, drag a file or click 'Load Demo'.<br/>"
            "<b>2. Analysis:</b> Click 'Run Analysis' — use 'Mock / Demo' model for testing.<br/>"
            "<b>3. Debate Viewer:</b> View the multi-agent debate transcript after analysis.<br/>"
            "<b>4. Batch:</b> Queue multiple files for automated processing.<br/>"
            "<b>5. History:</b> Browse and export all previous results.<br/>"
            "<b>6. Settings:</b> Enter your API keys and configure defaults.<br/><br/>"
            "<i>No API key required for Mock / Demo mode.</i>"
        )
        msg.exec()

    def _show_analysis_done_banner(self, result) -> None:
        """Flash a non-intrusive status bar notification."""
        flag_str = " — ⚠ REVIEW FLAGGED" if result.review_flag else ""
        msg = (f"Analysis done: {result.rhythm}  Conf={result.confidence*100:.0f}%"
               f"  F1={result.macro_f1:.3f}{flag_str}"
               f"  → Debate Viewer shows full transcript")
        self._sb_operation.setText(msg)

    def closeEvent(self, event) -> None:
        self._db.close()
        event.accept()
