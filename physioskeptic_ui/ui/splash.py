"""
SplashScreen — PhysioSkeptic
Professional startup screen with animated loading.
"""
from __future__ import annotations

from PySide6.QtWidgets import QSplashScreen, QWidget, QLabel, QVBoxLayout, QProgressBar
from PySide6.QtCore import Qt, QTimer, QSize, QRect
from PySide6.QtGui import QPainter, QColor, QFont, QLinearGradient, QGradient, QPen, QPixmap


_STEPS = [
    "Initializing signal processing engine…",
    "Loading encoder weights…",
    "Connecting to database…",
    "Preparing debate pipeline…",
    "Ready.",
]


class SplashScreen(QSplashScreen):
    """Animated startup splash screen drawn entirely with QPainter."""

    W, H = 620, 340

    def __init__(self) -> None:
        px = QPixmap(self.W, self.H)
        px.fill(QColor("#0a0f16"))
        super().__init__(px, Qt.WindowStaysOnTopHint)
        self.setWindowFlag(Qt.FramelessWindowHint)

        self._progress = 0
        self._step_idx = 0
        self._msg = _STEPS[0]

        # Advance progress every 380 ms
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._advance)
        self._timer.start(380)

    # ── drawing ───────────────────────────────────────────────────────────────

    def drawContents(self, painter: QPainter) -> None:
        W, H = self.W, self.H
        painter.setRenderHint(QPainter.Antialiasing)

        # ── background gradient ──
        grad = QLinearGradient(0, 0, W, H)
        grad.setColorAt(0.0, QColor("#0d1117"))
        grad.setColorAt(1.0, QColor("#080d12"))
        painter.fillRect(0, 0, W, H, grad)

        # ── subtle accent strip top ──
        accent_grad = QLinearGradient(0, 0, W, 0)
        accent_grad.setColorAt(0.0, QColor("#1e40af"))
        accent_grad.setColorAt(0.5, QColor("#2563eb"))
        accent_grad.setColorAt(1.0, QColor("#1e40af"))
        painter.fillRect(0, 0, W, 3, accent_grad)

        # ── logo mark — circle + cross ──
        cx, cy = 56, H // 2 - 20
        r = 22
        painter.setPen(QPen(QColor("#2563eb"), 2.5))
        painter.setBrush(QColor(0, 0, 0, 0))
        painter.drawEllipse(cx - r, cy - r, r * 2, r * 2)
        # inner "pulse" line
        painter.setPen(QPen(QColor("#2563eb"), 2))
        pts = [
            (cx - 14, cy), (cx - 7, cy),
            (cx - 4, cy - 8), (cx, cy + 8),
            (cx + 4, cy - 8), (cx + 7, cy),
            (cx + 14, cy),
        ]
        for i in range(len(pts) - 1):
            painter.drawLine(pts[i][0], pts[i][1], pts[i + 1][0], pts[i + 1][1])

        # ── product name ──
        painter.setPen(QColor("#f0f6fc"))
        f = QFont("Segoe UI", 28, QFont.Bold)
        f.setLetterSpacing(QFont.AbsoluteSpacing, 1)
        painter.setFont(f)
        painter.drawText(QRect(96, H // 2 - 52, W - 112, 46), Qt.AlignLeft | Qt.AlignVCenter, "PhysioSkeptic")

        # ── tag line ──
        painter.setPen(QColor("#8b949e"))
        f2 = QFont("Segoe UI", 10)
        painter.setFont(f2)
        painter.drawText(
            QRect(98, H // 2 - 6, W - 120, 22),
            Qt.AlignLeft | Qt.AlignVCenter,
            "Signal-Quality-Anchored Skeptical Reasoning for Rhythm Diagnosis",
        )

        # ── version badge ──
        badge_rect = QRect(W - 88, 14, 72, 20)
        painter.setPen(QColor("#30363d"))
        painter.setBrush(QColor("#161b22"))
        painter.drawRoundedRect(badge_rect, 4, 4)
        painter.setPen(QColor("#8b949e"))
        f3 = QFont("Segoe UI", 8)
        painter.setFont(f3)
        painter.drawText(badge_rect, Qt.AlignCenter, "v 1.0.0")

        # ── progress track ──
        track_y = H - 56
        track_rect = QRect(40, track_y, W - 80, 4)
        painter.setPen(Qt.NoPen)
        painter.setBrush(QColor("#21262d"))
        painter.drawRoundedRect(track_rect, 2, 2)

        fill_w = int((W - 80) * self._progress / 100)
        if fill_w > 0:
            pg = QLinearGradient(40, 0, 40 + fill_w, 0)
            pg.setColorAt(0, QColor("#1d4ed8"))
            pg.setColorAt(1, QColor("#3b82f6"))
            painter.setBrush(pg)
            painter.drawRoundedRect(QRect(40, track_y, fill_w, 4), 2, 2)

        # ── status message ──
        painter.setPen(QColor("#6e7681"))
        f4 = QFont("Segoe UI", 8)
        painter.setFont(f4)
        painter.drawText(QRect(40, track_y + 10, W - 80, 20), Qt.AlignLeft, self._msg)

        # ── copyright ──
        painter.setPen(QColor("#3d444d"))
        f5 = QFont("Segoe UI", 7)
        painter.setFont(f5)
        painter.drawText(
            QRect(0, H - 18, W, 16),
            Qt.AlignCenter,
            "© 2026 PhysioSkeptic Research. For research use only.",
        )

    # ── logic ─────────────────────────────────────────────────────────────────

    def _advance(self) -> None:
        self._step_idx = min(self._step_idx + 1, len(_STEPS) - 1)
        self._msg = _STEPS[self._step_idx]
        self._progress = min(self._progress + 22, 100)
        self.repaint()

    def finish_and_show(self, window) -> None:  # type: ignore[override]
        """Complete progress then reveal main window."""
        self._progress = 100
        self._msg = _STEPS[-1]
        self.repaint()
        QTimer.singleShot(350, lambda: super(SplashScreen, self).finish(window))
