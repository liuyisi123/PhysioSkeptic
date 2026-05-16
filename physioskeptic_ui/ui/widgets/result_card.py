"""
ResultCard and StatCard — PhysioSkeptic
Polished stat and result display widgets.
"""
from __future__ import annotations

from PySide6.QtWidgets import QFrame, QVBoxLayout, QHBoxLayout, QLabel, QSizePolicy
from PySide6.QtCore import Qt, QPropertyAnimation, QEasingCurve, QRect
from PySide6.QtGui import QFont, QColor, QPainter, QPen, QBrush, QLinearGradient

from ..theme import ACCENT, SUCCESS, WARNING, DANGER, TEXT_SECONDARY, BG_CARD, BORDER


# ── rhythm icon glyphs (unicode, no images needed) ────────────────────────────
_RHYTHM_GLYPHS = {
    "SR":        "♥",
    "STACH":     "⚡",
    "SBRAD":     "🔵",
    "AF_FAMILY": "〜",
    "PACE":      "⬡",
}


class _AccentBar(QFrame):
    """Vertical left accent bar painted with QPainter for precise sizing."""

    def __init__(self, color: str, parent=None) -> None:
        super().__init__(parent)
        self._color = QColor(color)
        self.setFixedWidth(4)

    def paintEvent(self, event) -> None:  # noqa: N802
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setPen(Qt.NoPen)
        painter.setBrush(self._color)
        painter.drawRoundedRect(self.rect(), 2, 2)

    def set_color(self, color: str) -> None:
        self._color = QColor(color)
        self.update()


class StatCard(QFrame):
    """
    KPI stat card.
    Left accent bar + large light-weight value + small label below.
    """

    def __init__(
        self,
        title: str,
        value: str = "—",
        subtitle: str = "",
        accent_color: str = ACCENT,
        parent=None,
    ) -> None:
        super().__init__(parent)
        self.setObjectName("StatCard")
        self.setMinimumWidth(130)
        self.setMinimumHeight(100)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

        outer = QHBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        # left accent bar
        self._accent_bar = _AccentBar(accent_color)
        outer.addWidget(self._accent_bar)

        # content
        inner = QVBoxLayout()
        inner.setContentsMargins(14, 14, 14, 14)
        inner.setSpacing(1)

        self._value_label = QLabel(value)
        self._value_label.setObjectName("StatValue")
        vf = QFont("Segoe UI", 26)
        vf.setWeight(QFont.Weight.Light)  # light weight — more premium feel
        self._value_label.setFont(vf)
        inner.addWidget(self._value_label)

        self._title_label = QLabel(title)
        self._title_label.setObjectName("StatLabel")
        tf = QFont("Segoe UI", 8)
        self._title_label.setFont(tf)
        inner.addWidget(self._title_label)

        if subtitle:
            self._sub_label = QLabel(subtitle)
            sub_f = QFont("Segoe UI", 7)
            self._sub_label.setFont(sub_f)
            self._sub_label.setStyleSheet(f"color: {TEXT_SECONDARY};")
            inner.addWidget(self._sub_label)
        else:
            self._sub_label = None

        inner.addStretch()
        outer.addLayout(inner)

        # store accent color
        self._accent_color = accent_color

    def update_value(self, value: str, subtitle: str = "") -> None:
        self._value_label.setText(value)
        if self._sub_label and subtitle:
            self._sub_label.setText(subtitle)

    def set_accent(self, color: str) -> None:
        self._accent_color = color
        self._accent_bar.set_color(color)


class _ConfidenceArc(QFrame):
    """Circular arc confidence gauge drawn with QPainter."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._pct: int = 0
        self._color = QColor(SUCCESS)
        self.setFixedSize(80, 80)

    def set_value(self, pct: int, color: str) -> None:
        self._pct = max(0, min(100, pct))
        self._color = QColor(color)
        self.update()

    def paintEvent(self, event) -> None:  # noqa: N802
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)

        W = self.width()
        H = self.height()
        m = 8  # margin
        rect = QRect(m, m, W - 2 * m, H - 2 * m)

        # track ring
        p.setPen(QPen(QColor(BORDER), 6, Qt.SolidLine, Qt.RoundCap))
        p.setBrush(Qt.NoBrush)
        p.drawEllipse(rect)

        # filled arc
        if self._pct > 0:
            p.setPen(QPen(self._color, 6, Qt.SolidLine, Qt.RoundCap))
            p.drawArc(rect, 90 * 16, -int(self._pct * 3.6) * 16)

        # percentage text
        p.setPen(QColor("#dce6f0"))
        f = QFont("Segoe UI", 12, QFont.Bold)
        p.setFont(f)
        p.drawText(rect, Qt.AlignCenter, f"{self._pct}%")


class ResultCard(QFrame):
    """
    Analysis result summary — rhythm label, confidence arc, metrics row.
    Richer than a plain bar; drawn to look like a medical report widget.
    """

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setObjectName("CardAccent")
        self.setMinimumHeight(130)

        root = QVBoxLayout(self)
        root.setContentsMargins(18, 14, 18, 14)
        root.setSpacing(10)

        # ── top row: rhythm + arc ──────────────────────────────────────────────
        top = QHBoxLayout()
        top.setSpacing(14)

        left = QVBoxLayout()
        left.setSpacing(3)

        self._glyph = QLabel("—")
        gf = QFont("Segoe UI", 24)
        self._glyph.setFont(gf)
        left.addWidget(self._glyph)

        self._rhythm_label = QLabel("Awaiting analysis")
        rf = QFont("Segoe UI", 13, QFont.Bold)
        self._rhythm_label.setFont(rf)
        left.addWidget(self._rhythm_label)

        self._badge = QLabel()
        self._badge.setFixedHeight(20)
        left.addWidget(self._badge)
        left.addStretch()

        top.addLayout(left)
        top.addStretch()

        right = QVBoxLayout()
        right.setAlignment(Qt.AlignRight | Qt.AlignTop)
        self._arc = _ConfidenceArc()
        right.addWidget(self._arc)
        self._model_label = QLabel("")
        mf = QFont("Segoe UI", 7)
        self._model_label.setFont(mf)
        self._model_label.setStyleSheet(f"color: {TEXT_SECONDARY};")
        self._model_label.setAlignment(Qt.AlignCenter)
        right.addWidget(self._model_label)
        top.addLayout(right)

        root.addLayout(top)

        # ── metrics row ────────────────────────────────────────────────────────
        sep = QFrame()
        sep.setObjectName("Divider")
        sep.setFixedHeight(1)
        root.addWidget(sep)

        mrow = QHBoxLayout()
        mrow.setSpacing(20)
        self._ece_label  = self._mini_label("ECE", "—")
        self._f1_label   = self._mini_label("Macro-F1", "—")
        self._route_label = self._mini_label("Route", "—")
        for w in [self._ece_label, self._f1_label, self._route_label]:
            mrow.addWidget(w)
        mrow.addStretch()
        root.addLayout(mrow)

    @staticmethod
    def _mini_label(title: str, value: str) -> QFrame:
        f = QFrame()
        lay = QVBoxLayout(f)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(1)
        v = QLabel(value)
        v.setObjectName("_metric_value")
        vf = QFont("Segoe UI", 11, QFont.Bold)
        v.setFont(vf)
        t = QLabel(title.upper())
        tf = QFont("Segoe UI", 7)
        t.setFont(tf)
        t.setStyleSheet(f"color: {TEXT_SECONDARY}; letter-spacing: 0.5px;")
        lay.addWidget(v)
        lay.addWidget(t)
        return f

    def _set_mini(self, frame: QFrame, value: str) -> None:
        for child in frame.findChildren(QLabel):
            if child.objectName() == "_metric_value":
                child.setText(value)
                break

    def update_result(
        self,
        rhythm: str,
        confidence: float,
        review_flag: bool,
        ece: float,
        macro_f1: float,
        model_name: str = "",
        route: str = "",
    ) -> None:
        self._rhythm_label.setText(rhythm)
        glyph = _RHYTHM_GLYPHS.get(rhythm, "◆")
        self._glyph.setText(glyph)

        pct = int(confidence * 100)
        if confidence >= 0.85:
            color = SUCCESS
        elif confidence >= 0.70:
            color = WARNING
        else:
            color = DANGER

        self._arc.set_value(pct, color)

        if review_flag:
            self._badge.setObjectName("BadgeReview")
            self._badge.setText("⚠  Expert review recommended")
        else:
            self._badge.setObjectName("BadgeClear")
            self._badge.setText("✓  Cleared")
        self._badge.style().unpolish(self._badge)
        self._badge.style().polish(self._badge)

        self._model_label.setText(model_name)
        self._set_mini(self._ece_label, f"{ece:.3f}")
        self._set_mini(self._f1_label, f"{macro_f1:.3f}")
        self._set_mini(self._route_label, route or "—")

    def clear(self) -> None:
        self._rhythm_label.setText("Awaiting analysis")
        self._glyph.setText("—")
        self._arc.set_value(0, SUCCESS)
        self._badge.setText("")
        self._model_label.setText("")
        for frame in [self._ece_label, self._f1_label, self._route_label]:
            self._set_mini(frame, "—")
