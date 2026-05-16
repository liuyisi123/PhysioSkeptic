"""
PatchReportWidget — displays the signal quality patch report in a compact grid.
"""
from __future__ import annotations

from typing import Optional

from PySide6.QtWidgets import (
    QFrame, QGridLayout, QVBoxLayout, QLabel, QProgressBar, QSizePolicy,
)
from PySide6.QtCore import Qt

from ..theme import SUCCESS, WARNING, DANGER, ACCENT


class _MetricRow:
    def __init__(self, grid: QGridLayout, row: int, label: str, unit: str = "") -> None:
        self._lbl_name = QLabel(label)
        self._lbl_name.setObjectName("SubLabel")
        self._lbl_val = QLabel("—")
        self._lbl_val.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        self._unit = QLabel(unit)
        self._unit.setObjectName("SubLabel")
        grid.addWidget(self._lbl_name, row, 0)
        grid.addWidget(self._lbl_val, row, 1)
        grid.addWidget(self._unit, row, 2)

    def set_value(self, val: str, color: str = "#f0f6fc") -> None:
        self._lbl_val.setText(val)
        self._lbl_val.setStyleSheet(f"color: {color};")


class PatchReportWidget(QFrame):
    """Compact patch report panel."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setObjectName("Card")
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(12, 10, 12, 10)
        outer.setSpacing(6)

        title = QLabel("Signal Quality Report")
        title.setObjectName("SectionHeader")
        from PySide6.QtGui import QFont
        f = title.font()
        f.setPointSize(10)
        f.setBold(True)
        title.setFont(f)
        outer.addWidget(title)

        # SQI bar
        sqi_row = QFrame()
        sqi_layout = QGridLayout(sqi_row)
        sqi_layout.setContentsMargins(0, 0, 0, 0)
        sqi_layout.setSpacing(6)

        sqi_label = QLabel("SQI")
        sqi_label.setObjectName("SubLabel")
        self._sqi_bar = QProgressBar()
        self._sqi_bar.setRange(0, 100)
        self._sqi_bar.setValue(0)
        self._sqi_bar.setTextVisible(True)
        self._sqi_bar.setFixedHeight(14)
        sqi_layout.addWidget(sqi_label, 0, 0)
        sqi_layout.addWidget(self._sqi_bar, 0, 1)
        outer.addWidget(sqi_row)

        # metrics grid
        grid = QGridLayout()
        grid.setHorizontalSpacing(16)
        grid.setVerticalSpacing(4)
        grid.setColumnStretch(1, 1)

        self._hr       = _MetricRow(grid, 0, "Heart Rate", "bpm")
        self._rr_std   = _MetricRow(grid, 1, "RR Std Dev", "ms")
        self._qrs      = _MetricRow(grid, 2, "QRS Duration", "ms")
        self._pr       = _MetricRow(grid, 3, "PR Interval", "ms")
        self._qt       = _MetricRow(grid, 4, "QT Interval", "ms")
        self._n_beats  = _MetricRow(grid, 5, "Beat Count", "")
        self._artifact = _MetricRow(grid, 6, "Artifact Fraction", "%")

        outer.addLayout(grid)

    def update_report(self, patch) -> None:
        """Update from a PatchReport instance."""
        sqi_pct = int(patch.sqi * 100)
        self._sqi_bar.setValue(sqi_pct)
        self._sqi_bar.setFormat(f"{sqi_pct}%")
        color_sqi = SUCCESS if patch.sqi >= 0.8 else (WARNING if patch.sqi >= 0.5 else DANGER)
        self._sqi_bar.setStyleSheet(
            f"QProgressBar::chunk {{ background-color: {color_sqi}; border-radius: 3px; }}"
        )

        self._hr.set_value(f"{patch.hr_bpm:.1f}")
        color_hr = SUCCESS if 60 <= patch.hr_bpm <= 100 else WARNING
        self._hr.set_value(f"{patch.hr_bpm:.1f}", color_hr)

        self._rr_std.set_value(f"{patch.rr_std_ms:.1f}")
        self._qrs.set_value(f"{patch.qrs_duration_ms:.0f}")
        self._pr.set_value(
            f"{patch.pr_interval_ms:.0f}",
            WARNING if patch.pr_interval_ms > 200 else "#f0f6fc"
        )
        self._qt.set_value(f"{patch.qt_interval_ms:.0f}")
        self._n_beats.set_value(str(patch.n_beats))
        art_pct = patch.artifact_fraction * 100
        self._artifact.set_value(
            f"{art_pct:.1f}",
            DANGER if art_pct > 20 else (WARNING if art_pct > 10 else SUCCESS)
        )

    def clear(self) -> None:
        self._sqi_bar.setValue(0)
        for row in [self._hr, self._rr_std, self._qrs, self._pr,
                    self._qt, self._n_beats, self._artifact]:
            row.set_value("—")
