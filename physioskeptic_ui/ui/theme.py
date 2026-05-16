"""
Theme — PhysioSkeptic
Professional dark medical/scientific QSS stylesheet.
Palette inspired by Siemens Healthineers / GitHub dark.
"""
from __future__ import annotations

# ── color tokens ──────────────────────────────────────────────────────────────
BG_MAIN       = "#0b0f14"   # slightly warm black — less harsh than pure #0d1117
BG_SIDEBAR    = "#10161d"   # distinct from main, cooler tone
BG_CARD       = "#161d27"   # cards slightly lighter — perceptible depth
BG_INPUT      = "#0e1420"   # input sits behind card
BG_TOOLBAR    = "#0e1318"   # toolbar is darkest — grounds the top strip
BG_TABLE_ALT  = "#121922"

ACCENT        = "#1a6bdb"   # slightly muted blue — less neon, more professional
ACCENT_HOVER  = "#1558c0"
ACCENT_PRESS  = "#1048a0"

SUCCESS       = "#14a87a"   # desaturated emerald
WARNING       = "#d4900a"   # amber, not yellow
DANGER        = "#d94040"   # crimson — not alarm-red

INFO          = "#2fa8d4"

TEXT_PRIMARY  = "#dce6f0"   # slightly off-white — easier on dark bg
TEXT_SECONDARY= "#748494"
TEXT_DISABLED = "#3e4a56"
BORDER        = "#1f2b38"   # subtle, nearly invisible border
BORDER_MID    = "#263445"   # for hover states
BORDER_FOCUS  = "#1a6bdb"

SCROLLBAR     = "#1f2b38"
SCROLLBAR_HOVER = "#2e3f52"

ROLE_COLORS = {
    "proposer": "#2563eb",
    "checker":  "#f59e0b",
    "skeptic":  "#ef4444",
    "advocate": "#10b981",
    "arbiter":  "#a855f7",
}


def get_stylesheet(font_size: int = 10) -> str:
    """Return the complete QSS stylesheet."""
    fs   = font_size
    fs_s = font_size - 1
    fs_l = font_size + 2

    return f"""
/* ── Global ─────────────────────────────────────────────────────────────── */
* {{
    font-family: "Segoe UI", "SF Pro Display", "Helvetica Neue", Arial, sans-serif;
    font-size: {fs}pt;
    color: {TEXT_PRIMARY};
    outline: none;
    selection-background-color: {ACCENT};
    selection-color: {TEXT_PRIMARY};
}}

QMainWindow {{
    background-color: {BG_MAIN};
}}

QWidget {{
    background-color: {BG_MAIN};
    border: none;
}}

/* ── Sidebar ─────────────────────────────────────────────────────────────── */
#Sidebar {{
    background-color: {BG_SIDEBAR};
    border-right: 1px solid {BORDER};
    min-width: 200px;
}}

#SidebarLogo {{
    color: {TEXT_PRIMARY};
    font-size: {fs_l + 3}pt;
    font-weight: 700;
    padding: 4px 2px 0 2px;
    letter-spacing: -0.5px;
}}

#SidebarTagline {{
    color: {TEXT_SECONDARY};
    font-size: 7pt;
    letter-spacing: 0.3px;
    padding-bottom: 2px;
}}

#SidebarVersion {{
    color: {TEXT_DISABLED};
    font-size: 7pt;
    padding: 0 0 6px 0;
}}

#SidebarSection {{
    color: {TEXT_DISABLED};
    font-size: 7pt;
    font-weight: 700;
    letter-spacing: 1.2px;
    padding: 14px 14px 4px 14px;
}}

/* ── Nav Buttons ────────────────────────────────────────────────────────── */
#NavButton {{
    background-color: transparent;
    border: none;
    border-radius: 5px;
    color: {TEXT_SECONDARY};
    text-align: left;
    padding: 7px 12px 7px 14px;
    font-size: {fs}pt;
    font-weight: 400;
}}

#NavButton:hover {{
    background-color: rgba(255, 255, 255, 0.05);
    color: {TEXT_PRIMARY};
}}

#NavButton[active="true"] {{
    background-color: rgba(26, 107, 219, 0.18);
    color: #a8c8ff;
    border-left: 2px solid {ACCENT};
    padding-left: 12px;
    font-weight: 500;
}}

#NavButton[active="true"]:hover {{
    background-color: rgba(26, 107, 219, 0.22);
}}

/* ── Toolbar ────────────────────────────────────────────────────────────── */
QToolBar {{
    background-color: {BG_TOOLBAR};
    border-bottom: 1px solid {BORDER};
    padding: 4px 8px;
    spacing: 8px;
}}

QToolBar QLabel {{
    color: {TEXT_SECONDARY};
    font-size: {fs_s}pt;
}}

QToolBar QComboBox {{
    min-width: 160px;
}}

/* ── Status Bar ─────────────────────────────────────────────────────────── */
QStatusBar {{
    background-color: {BG_SIDEBAR};
    border-top: 1px solid {BORDER};
    color: {TEXT_SECONDARY};
    font-size: {fs_s}pt;
    padding: 2px 8px;
}}

QStatusBar::item {{
    border: none;
    padding: 0 8px;
}}

/* ── Buttons ────────────────────────────────────────────────────────────── */
QPushButton {{
    background-color: {BG_CARD};
    border: 1px solid {BORDER};
    border-radius: 6px;
    color: {TEXT_PRIMARY};
    padding: 6px 14px;
    font-size: {fs}pt;
    font-weight: 500;
    min-height: 28px;
}}

QPushButton:hover {{
    background-color: #263145;
    border-color: #4c5566;
}}

QPushButton:pressed {{
    background-color: #1a2332;
}}

QPushButton:disabled {{
    background-color: {BG_CARD};
    color: {TEXT_DISABLED};
    border-color: {BORDER};
}}

QPushButton#PrimaryButton, QPushButton[primary="true"] {{
    background-color: {ACCENT};
    border-color: {ACCENT};
    color: #ffffff;
    font-weight: 600;
}}

QPushButton#PrimaryButton:hover, QPushButton[primary="true"]:hover {{
    background-color: {ACCENT_HOVER};
    border-color: {ACCENT_HOVER};
}}

QPushButton#PrimaryButton:pressed, QPushButton[primary="true"]:pressed {{
    background-color: {ACCENT_PRESS};
}}

QPushButton#DangerButton {{
    background-color: {DANGER};
    border-color: {DANGER};
    color: #ffffff;
}}

QPushButton#DangerButton:hover {{
    background-color: #dc2626;
}}

QPushButton#FlatButton {{
    background-color: transparent;
    border: none;
    color: {TEXT_SECONDARY};
}}

QPushButton#FlatButton:hover {{
    color: {TEXT_PRIMARY};
    background-color: rgba(255,255,255,0.06);
}}

QPushButton#RunButton {{
    background-color: {ACCENT};
    border: none;
    border-radius: 8px;
    color: #ffffff;
    font-size: {fs_l}pt;
    font-weight: 700;
    padding: 12px 32px;
    min-height: 48px;
}}

QPushButton#RunButton:hover {{
    background-color: {ACCENT_HOVER};
}}

QPushButton#RunButton:pressed {{
    background-color: {ACCENT_PRESS};
}}

QPushButton#RunButton:disabled {{
    background-color: #1c3260;
    color: #4c5e8a;
}}

/* ── Line Edits / Inputs ─────────────────────────────────────────────────── */
QLineEdit, QTextEdit, QPlainTextEdit {{
    background-color: {BG_INPUT};
    border: 1px solid {BORDER};
    border-radius: 6px;
    color: {TEXT_PRIMARY};
    padding: 5px 10px;
    selection-background-color: {ACCENT};
}}

QLineEdit:focus, QTextEdit:focus, QPlainTextEdit:focus {{
    border-color: {BORDER_FOCUS};
    background-color: #0d1826;
}}

QLineEdit:disabled {{
    color: {TEXT_DISABLED};
    background-color: #111820;
}}

/* ── ComboBox ───────────────────────────────────────────────────────────── */
QComboBox {{
    background-color: {BG_INPUT};
    border: 1px solid {BORDER};
    border-radius: 6px;
    color: {TEXT_PRIMARY};
    padding: 5px 10px;
    min-height: 28px;
}}

QComboBox:focus, QComboBox:hover {{
    border-color: {BORDER_FOCUS};
}}

QComboBox::drop-down {{
    border: none;
    width: 24px;
}}

QComboBox::down-arrow {{
    image: none;
    width: 10px;
    height: 10px;
    border-left: 5px solid transparent;
    border-right: 5px solid transparent;
    border-top: 6px solid {TEXT_SECONDARY};
    margin-right: 6px;
}}

QComboBox QAbstractItemView {{
    background-color: {BG_CARD};
    border: 1px solid {BORDER};
    border-radius: 4px;
    color: {TEXT_PRIMARY};
    selection-background-color: {ACCENT};
    outline: none;
}}

/* ── SpinBox ────────────────────────────────────────────────────────────── */
QSpinBox, QDoubleSpinBox {{
    background-color: {BG_INPUT};
    border: 1px solid {BORDER};
    border-radius: 6px;
    color: {TEXT_PRIMARY};
    padding: 4px 8px;
    min-height: 28px;
}}

QSpinBox:focus, QDoubleSpinBox:focus {{
    border-color: {BORDER_FOCUS};
}}

QSpinBox::up-button, QDoubleSpinBox::up-button,
QSpinBox::down-button, QDoubleSpinBox::down-button {{
    background-color: transparent;
    border: none;
    width: 18px;
}}

/* ── Table ──────────────────────────────────────────────────────────────── */
QTableWidget, QTableView {{
    background-color: {BG_MAIN};
    border: 1px solid {BORDER};
    border-radius: 6px;
    gridline-color: {BORDER};
    color: {TEXT_PRIMARY};
    alternate-background-color: {BG_TABLE_ALT};
}}

QTableWidget::item, QTableView::item {{
    padding: 6px 10px;
    border: none;
}}

QTableWidget::item:selected, QTableView::item:selected {{
    background-color: rgba(37, 99, 235, 0.30);
    color: {TEXT_PRIMARY};
}}

QTableWidget::item:hover, QTableView::item:hover {{
    background-color: rgba(37, 99, 235, 0.12);
}}

QHeaderView::section {{
    background-color: {BG_SIDEBAR};
    border: none;
    border-right: 1px solid {BORDER};
    border-bottom: 1px solid {BORDER};
    color: {TEXT_SECONDARY};
    font-size: {fs_s}pt;
    font-weight: 600;
    letter-spacing: 0.5px;
    text-transform: uppercase;
    padding: 8px 10px;
}}

QHeaderView::section:hover {{
    background-color: #1d2736;
    color: {TEXT_PRIMARY};
}}

/* ── Tab Widget ─────────────────────────────────────────────────────────── */
QTabWidget::pane {{
    border: 1px solid {BORDER};
    border-radius: 6px;
    background-color: {BG_CARD};
    top: -1px;
}}

QTabBar::tab {{
    background-color: transparent;
    border: 1px solid transparent;
    border-bottom: none;
    border-top-left-radius: 6px;
    border-top-right-radius: 6px;
    color: {TEXT_SECONDARY};
    font-size: {fs}pt;
    padding: 8px 18px;
    margin-right: 2px;
}}

QTabBar::tab:selected {{
    background-color: {BG_CARD};
    border-color: {BORDER};
    color: {TEXT_PRIMARY};
    font-weight: 600;
}}

QTabBar::tab:hover:!selected {{
    background-color: rgba(255,255,255,0.05);
    color: {TEXT_PRIMARY};
}}

/* ── Progress Bar ───────────────────────────────────────────────────────── */
QProgressBar {{
    background-color: {BG_SIDEBAR};
    border: 1px solid {BORDER};
    border-radius: 4px;
    color: transparent;
    height: 8px;
    text-align: center;
}}

QProgressBar::chunk {{
    background-color: {ACCENT};
    border-radius: 4px;
}}

QProgressBar#SuccessBar::chunk {{
    background-color: {SUCCESS};
}}

QProgressBar#WarningBar::chunk {{
    background-color: {WARNING};
}}

/* ── Slider ─────────────────────────────────────────────────────────────── */
QSlider::groove:horizontal {{
    background-color: {BG_SIDEBAR};
    border: 1px solid {BORDER};
    border-radius: 3px;
    height: 6px;
}}

QSlider::handle:horizontal {{
    background-color: {ACCENT};
    border: 2px solid {ACCENT};
    border-radius: 8px;
    width: 16px;
    height: 16px;
    margin: -6px 0;
}}

QSlider::handle:horizontal:hover {{
    background-color: {ACCENT_HOVER};
    border-color: {ACCENT_HOVER};
}}

QSlider::sub-page:horizontal {{
    background-color: {ACCENT};
    border-radius: 3px;
}}

/* ── Scroll Bar ─────────────────────────────────────────────────────────── */
QScrollBar:vertical {{
    background-color: transparent;
    border: none;
    width: 8px;
    margin: 0;
}}

QScrollBar::handle:vertical {{
    background-color: {SCROLLBAR};
    border-radius: 4px;
    min-height: 30px;
}}

QScrollBar::handle:vertical:hover {{
    background-color: {SCROLLBAR_HOVER};
}}

QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
    height: 0;
    background: transparent;
}}

QScrollBar:horizontal {{
    background-color: transparent;
    border: none;
    height: 8px;
}}

QScrollBar::handle:horizontal {{
    background-color: {SCROLLBAR};
    border-radius: 4px;
    min-width: 30px;
}}

QScrollBar::handle:horizontal:hover {{
    background-color: {SCROLLBAR_HOVER};
}}

QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{
    width: 0;
    background: transparent;
}}

/* ── Group Box ──────────────────────────────────────────────────────────── */
QGroupBox {{
    background-color: {BG_CARD};
    border: 1px solid {BORDER};
    border-radius: 8px;
    font-size: {fs}pt;
    font-weight: 600;
    color: {TEXT_SECONDARY};
    margin-top: 14px;
    padding-top: 8px;
}}

QGroupBox::title {{
    subcontrol-origin: margin;
    subcontrol-position: top left;
    padding: 0 8px;
    color: {TEXT_SECONDARY};
    font-size: {fs_s}pt;
    font-weight: 600;
    letter-spacing: 0.8px;
    text-transform: uppercase;
    left: 10px;
    top: -2px;
}}

/* ── Labels ─────────────────────────────────────────────────────────────── */
QLabel {{
    background: transparent;
    color: {TEXT_PRIMARY};
    border: none;
}}

QLabel#SubLabel {{
    color: {TEXT_SECONDARY};
    font-size: {fs_s}pt;
}}

QLabel#SectionHeader {{
    color: {TEXT_PRIMARY};
    font-size: {fs_l}pt;
    font-weight: 700;
    padding: 8px 0 4px 0;
}}

QLabel#StatValue {{
    color: {TEXT_PRIMARY};
    font-size: 22pt;
    font-weight: 700;
}}

QLabel#StatLabel {{
    color: {TEXT_SECONDARY};
    font-size: {fs_s}pt;
    font-weight: 500;
    text-transform: uppercase;
    letter-spacing: 0.8px;
}}

QLabel#BadgeReview {{
    background-color: rgba(239, 68, 68, 0.20);
    border: 1px solid {DANGER};
    border-radius: 4px;
    color: {DANGER};
    font-size: {fs_s}pt;
    font-weight: 700;
    padding: 3px 10px;
}}

QLabel#BadgeClear {{
    background-color: rgba(16, 185, 129, 0.20);
    border: 1px solid {SUCCESS};
    border-radius: 4px;
    color: {SUCCESS};
    font-size: {fs_s}pt;
    font-weight: 700;
    padding: 3px 10px;
}}

/* ── Splitter ───────────────────────────────────────────────────────────── */
QSplitter::handle {{
    background-color: {BORDER};
}}

QSplitter::handle:horizontal {{
    width: 1px;
}}

QSplitter::handle:vertical {{
    height: 1px;
}}

/* ── Menu ───────────────────────────────────────────────────────────────── */
QMenuBar {{
    background-color: {BG_TOOLBAR};
    border-bottom: 1px solid {BORDER};
    color: {TEXT_SECONDARY};
}}

QMenuBar::item:selected {{
    background-color: rgba(37, 99, 235, 0.20);
    color: {TEXT_PRIMARY};
}}

QMenu {{
    background-color: {BG_CARD};
    border: 1px solid {BORDER};
    border-radius: 6px;
    color: {TEXT_PRIMARY};
    padding: 4px;
}}

QMenu::item {{
    border-radius: 4px;
    padding: 6px 14px;
}}

QMenu::item:selected {{
    background-color: rgba(37, 99, 235, 0.30);
}}

QMenu::separator {{
    background-color: {BORDER};
    height: 1px;
    margin: 4px 8px;
}}

/* ── Check Box ──────────────────────────────────────────────────────────── */
QCheckBox {{
    spacing: 8px;
    color: {TEXT_PRIMARY};
}}

QCheckBox::indicator {{
    width: 16px;
    height: 16px;
    border: 1px solid {BORDER};
    border-radius: 4px;
    background-color: {BG_INPUT};
}}

QCheckBox::indicator:checked {{
    background-color: {ACCENT};
    border-color: {ACCENT};
}}

QCheckBox::indicator:hover {{
    border-color: {BORDER_FOCUS};
}}

/* ── Radio Button ───────────────────────────────────────────────────────── */
QRadioButton {{
    spacing: 8px;
    color: {TEXT_PRIMARY};
}}

QRadioButton::indicator {{
    width: 16px;
    height: 16px;
    border: 1px solid {BORDER};
    border-radius: 8px;
    background-color: {BG_INPUT};
}}

QRadioButton::indicator:checked {{
    background-color: {ACCENT};
    border-color: {ACCENT};
}}

/* ── Frame/Cards ────────────────────────────────────────────────────────── */
QFrame#Card {{
    background-color: {BG_CARD};
    border: 1px solid {BORDER};
    border-top: 1px solid {BORDER_MID};
    border-radius: 8px;
}}

QFrame#CardAccent {{
    background-color: {BG_CARD};
    border: 1px solid rgba(26,107,219,0.45);
    border-top: 2px solid {ACCENT};
    border-radius: 8px;
}}

QFrame#CardSuccess {{
    background-color: {BG_CARD};
    border: 1px solid rgba(20,168,122,0.35);
    border-top: 2px solid {SUCCESS};
    border-radius: 8px;
}}

QFrame#CardWarning {{
    background-color: {BG_CARD};
    border: 1px solid rgba(212,144,10,0.35);
    border-top: 2px solid {WARNING};
    border-radius: 8px;
}}

QFrame#CardDanger {{
    background-color: {BG_CARD};
    border: 1px solid rgba(217,64,64,0.35);
    border-top: 2px solid {DANGER};
    border-radius: 8px;
}}

/* stat card with left accent bar */
QFrame#StatCard {{
    background-color: {BG_CARD};
    border: 1px solid {BORDER};
    border-radius: 7px;
}}

QLabel#StatValue {{
    color: {TEXT_PRIMARY};
    font-size: 26pt;
    font-weight: 300;
    letter-spacing: -1px;
}}

QLabel#StatLabel {{
    color: {TEXT_SECONDARY};
    font-size: 8pt;
    font-weight: 400;
    letter-spacing: 0.4px;
}}

QFrame#Divider {{
    background-color: {BORDER};
    max-height: 1px;
    border: none;
}}

/* ── Drag-Drop Zone ─────────────────────────────────────────────────────── */
QFrame#DropZone {{
    background-color: rgba(37, 99, 235, 0.05);
    border: 2px dashed {BORDER};
    border-radius: 12px;
}}

QFrame#DropZone:hover {{
    background-color: rgba(37, 99, 235, 0.10);
    border-color: {ACCENT};
}}

/* ── Scroll Area ────────────────────────────────────────────────────────── */
QScrollArea {{
    border: none;
    background-color: transparent;
}}

QScrollArea > QWidget > QWidget {{
    background-color: transparent;
}}

/* ── Tool Tips ──────────────────────────────────────────────────────────── */
QToolTip {{
    background-color: {BG_CARD};
    border: 1px solid {BORDER};
    border-radius: 4px;
    color: {TEXT_PRIMARY};
    font-size: {fs_s}pt;
    padding: 4px 8px;
}}

/* ── Chat bubbles (Debate Viewer) ───────────────────────────────────────── */
QFrame#BubbleProposer {{
    background-color: rgba(37, 99, 235, 0.15);
    border: 1px solid rgba(37, 99, 235, 0.4);
    border-radius: 8px;
}}
QFrame#BubbleChecker {{
    background-color: rgba(245, 158, 11, 0.12);
    border: 1px solid rgba(245, 158, 11, 0.35);
    border-radius: 8px;
}}
QFrame#BubbleSkeptic {{
    background-color: rgba(239, 68, 68, 0.12);
    border: 1px solid rgba(239, 68, 68, 0.35);
    border-radius: 8px;
}}
QFrame#BubbleAdvocate {{
    background-color: rgba(16, 185, 129, 0.12);
    border: 1px solid rgba(16, 185, 129, 0.35);
    border-radius: 8px;
}}
QFrame#BubbleArbiter {{
    background-color: rgba(168, 85, 247, 0.15);
    border: 1px solid rgba(168, 85, 247, 0.4);
    border-radius: 8px;
}}
"""


# Light theme variant (minimal)
def get_light_stylesheet(font_size: int = 10) -> str:
    fs = font_size
    return f"""
* {{ font-size: {fs}pt; font-family: "Segoe UI", Arial, sans-serif; }}
QMainWindow, QWidget {{ background-color: #f3f4f6; color: #111827; }}
QGroupBox {{ background-color: #ffffff; border: 1px solid #d1d5db; border-radius: 8px; color: #374151; margin-top: 12px; padding-top: 6px; }}
QPushButton {{ background-color: #ffffff; border: 1px solid #d1d5db; border-radius: 6px; color: #111827; padding: 5px 12px; }}
QPushButton:hover {{ background-color: #f9fafb; }}
QPushButton[primary="true"] {{ background-color: #2563eb; color: #ffffff; border-color: #2563eb; }}
QLineEdit, QComboBox {{ background-color: #ffffff; border: 1px solid #d1d5db; border-radius: 5px; color: #111827; padding: 4px 8px; }}
QTableWidget, QTableView {{ background-color: #ffffff; border: 1px solid #d1d5db; color: #111827; }}
QHeaderView::section {{ background-color: #f9fafb; color: #374151; border-bottom: 1px solid #d1d5db; padding: 6px; }}
QProgressBar {{ background-color: #e5e7eb; border: none; border-radius: 4px; height: 8px; }}
QProgressBar::chunk {{ background-color: #2563eb; border-radius: 4px; }}
"""
