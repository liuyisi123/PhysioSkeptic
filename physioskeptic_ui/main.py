"""
PhysioSkeptic — Entry Point
Run with: python main.py
"""
from __future__ import annotations

import os
import sys

_root = os.path.dirname(os.path.abspath(__file__))
if _root not in sys.path:
    sys.path.insert(0, _root)

from PySide6.QtWidgets import QApplication
from PySide6.QtCore import Qt, QCoreApplication, QTimer
from PySide6.QtGui import QFont

from ui.theme import get_stylesheet
from ui.splash import SplashScreen
from ui.main_window import MainWindow


def main() -> None:
    QCoreApplication.setAttribute(Qt.ApplicationAttribute.AA_ShareOpenGLContexts)

    app = QApplication(sys.argv)
    app.setApplicationName("PhysioSkeptic")
    app.setApplicationDisplayName("PhysioSkeptic")
    app.setOrganizationName("PhysioSkeptic")
    app.setOrganizationDomain("physioskeptic.ai")
    app.setApplicationVersion("1.0.0")

    app.setStyleSheet(get_stylesheet())

    font = QFont("Segoe UI", 10)
    font.setStyleHint(QFont.StyleHint.SansSerif)
    app.setFont(font)

    # ── splash screen ──────────────────────────────────────────────────────────
    splash = SplashScreen()
    splash.show()
    app.processEvents()

    # ── load main window after splash ──────────────────────────────────────────
    window = MainWindow()

    # Show main window after splash finishes (~1.9 s)
    QTimer.singleShot(1900, lambda: _reveal(splash, window))

    sys.exit(app.exec())


def _reveal(splash: SplashScreen, window: MainWindow) -> None:
    splash.finish_and_show(window)
    window.show()
    window.raise_()
    window.activateWindow()


if __name__ == "__main__":
    main()
