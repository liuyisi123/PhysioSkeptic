"""
SignalPlotWidget — multi-channel pyqtgraph viewer.
Supports zoom, pan, ruler, per-channel color, and auto-scaling.
"""
from __future__ import annotations

from typing import List, Optional

import numpy as np
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QCheckBox, QScrollArea, QFrame, QSizePolicy,
)
from PySide6.QtCore import Qt, Signal

try:
    import pyqtgraph as pg
    _HAS_PG = True
    pg.setConfigOptions(antialias=True, background="#0d1117", foreground="#8b949e")
except ImportError:
    _HAS_PG = False

CHANNEL_COLORS = [
    "#2563eb", "#10b981", "#f59e0b",
    "#ef4444", "#a855f7", "#38bdf8",
    "#fb923c", "#f472b6",
]


class SignalPlotWidget(QWidget):
    """Multi-channel signal viewer with pyqtgraph.
    Falls back to a placeholder if pyqtgraph not installed."""

    region_selected = Signal(float, float)  # time_start, time_end

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self._signal_data = None
        self._plots: List = []
        self._curves: List = []
        self._layout = QVBoxLayout(self)
        self._layout.setContentsMargins(0, 0, 0, 0)
        self._layout.setSpacing(0)

        if _HAS_PG:
            self._build_pg_ui()
        else:
            self._build_fallback_ui()

    # ── build ─────────────────────────────────────────────────────────────────

    def _build_pg_ui(self) -> None:
        # Toolbar
        tb = QHBoxLayout()
        tb.setContentsMargins(4, 4, 4, 4)
        tb.setSpacing(8)

        self._btn_reset = QPushButton("⟳ Reset")
        self._btn_reset.setObjectName("FlatButton")
        self._btn_reset.setFixedHeight(26)
        self._btn_reset.clicked.connect(self._reset_view)

        self._btn_ruler = QPushButton("📏 Ruler")
        self._btn_ruler.setObjectName("FlatButton")
        self._btn_ruler.setFixedHeight(26)
        self._btn_ruler.setCheckable(True)
        self._btn_ruler.clicked.connect(self._toggle_ruler)

        self._time_label = QLabel("Duration: — s")
        self._time_label.setObjectName("SubLabel")

        tb.addWidget(self._btn_reset)
        tb.addWidget(self._btn_ruler)
        tb.addStretch()
        tb.addWidget(self._time_label)
        self._layout.addLayout(tb)

        # Graphics layout widget
        self._glw = pg.GraphicsLayoutWidget()
        self._glw.setBackground("#0d1117")
        self._layout.addWidget(self._glw)

        self._linked_x_axis = None
        self._region: Optional[pg.LinearRegionItem] = None

    def _build_fallback_ui(self) -> None:
        lbl = QLabel("pyqtgraph not installed\npip install pyqtgraph")
        lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lbl.setObjectName("SubLabel")
        self._layout.addWidget(lbl)

    # ── public API ────────────────────────────────────────────────────────────

    def load_signal(self, channels: np.ndarray, channel_names: List[str],
                    fs: float, duration_sec: float) -> None:
        if not _HAS_PG:
            return

        self._signal_data = (channels, channel_names, fs, duration_sec)
        self._clear_plots()

        n_ch = channels.shape[0]
        t = np.linspace(0, duration_sec, channels.shape[1])

        self._linked_x_axis = None

        for i in range(n_ch):
            p = self._glw.addPlot(row=i, col=0)
            p.setMenuEnabled(False)
            p.showGrid(x=False, y=True, alpha=0.15)
            p.setLabel("left", channel_names[i] if i < len(channel_names) else f"Ch{i}",
                       color="#8b949e", size="8pt")

            if self._linked_x_axis is not None:
                p.setXLink(self._linked_x_axis)
            else:
                self._linked_x_axis = p

            color = CHANNEL_COLORS[i % len(CHANNEL_COLORS)]
            pen = pg.mkPen(color=color, width=1.2)
            curve = p.plot(t, channels[i], pen=pen)
            self._curves.append(curve)
            self._plots.append(p)

            # Add axis only on bottom plot
            if i < n_ch - 1:
                p.getAxis("bottom").setStyle(showValues=False)
            else:
                p.setLabel("bottom", "Time (s)", color="#8b949e", size="8pt")

        self._time_label.setText(f"Duration: {duration_sec:.1f} s | {n_ch} channels | {fs:.0f} Hz")

    def clear(self) -> None:
        self._clear_plots()

    def _clear_plots(self) -> None:
        if not _HAS_PG:
            return
        self._glw.clear()
        self._plots.clear()
        self._curves.clear()
        self._region = None
        self._linked_x_axis = None

    def _reset_view(self) -> None:
        for p in self._plots:
            p.autoRange()

    def _toggle_ruler(self, checked: bool) -> None:
        if not self._plots:
            return
        p = self._plots[0]
        if checked:
            if self._region is None:
                data = self._signal_data
                dur = data[3] if data else 30.0
                self._region = pg.LinearRegionItem(
                    values=[dur * 0.2, dur * 0.8],
                    brush=pg.mkBrush(37, 99, 235, 40),
                    pen=pg.mkPen("#2563eb", width=1),
                )
                self._region.sigRegionChanged.connect(self._on_region_changed)
                for plot in self._plots:
                    plot.addItem(self._region)
        else:
            if self._region is not None:
                for plot in self._plots:
                    plot.removeItem(self._region)
                self._region = None

    def _on_region_changed(self) -> None:
        if self._region:
            lo, hi = self._region.getRegion()
            self.region_selected.emit(float(lo), float(hi))
