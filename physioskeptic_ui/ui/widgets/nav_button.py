"""
NavButton — collapsible sidebar navigation item.
"""
from __future__ import annotations

from PySide6.QtWidgets import QPushButton, QSizePolicy
from PySide6.QtCore import Qt, QSize
from PySide6.QtGui import QIcon


class NavButton(QPushButton):
    """Styled sidebar navigation button with active state tracking."""

    def __init__(
        self,
        label: str,
        icon_name: str = "",
        parent=None,
    ) -> None:
        super().__init__(parent)
        self._label = label
        self._icon_name = icon_name
        self._collapsed = False
        self._active = False

        self.setObjectName("NavButton")
        self.setCheckable(False)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.setMinimumHeight(40)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self._set_expanded_style()

    # ── public API ────────────────────────────────────────────────────────────

    def set_active(self, active: bool) -> None:
        self._active = active
        self.setProperty("active", "true" if active else "false")
        self.style().unpolish(self)
        self.style().polish(self)

    def set_collapsed(self, collapsed: bool) -> None:
        self._collapsed = collapsed
        if collapsed:
            self._set_collapsed_style()
        else:
            self._set_expanded_style()

    # ── private ───────────────────────────────────────────────────────────────

    def _set_expanded_style(self) -> None:
        self.setText(f"  {self._label}")
        self.setFixedHeight(40)

    def _set_collapsed_style(self) -> None:
        # Show only first letter as pseudo-icon
        abbrev = self._label[0].upper() if self._label else "?"
        self.setText(abbrev)
        self.setFixedHeight(40)
