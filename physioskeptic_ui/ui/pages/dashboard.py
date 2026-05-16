"""
Dashboard Page — PhysioSkeptic
Home screen with KPI stat cards, recent results table, rhythm distribution chart.
"""
from __future__ import annotations

from datetime import datetime
from typing import Optional, TYPE_CHECKING

import numpy as np
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame,
    QPushButton, QTableWidget, QTableWidgetItem, QHeaderView,
    QSizePolicy, QScrollArea,
)
from PySide6.QtCore import Qt, Signal, QTimer
from PySide6.QtGui import QFont

from ..widgets.result_card import StatCard
from ..theme import ACCENT, SUCCESS, WARNING, DANGER, TEXT_SECONDARY

if TYPE_CHECKING:
    from ...core.database import Database

try:
    import pyqtgraph as pg
    _HAS_PG = True
except ImportError:
    _HAS_PG = False


class DashboardPage(QWidget):
    """Home dashboard with KPI cards, recent results, and rhythm chart."""

    # signals to request navigation
    request_new_analysis = Signal()
    request_import = Signal()
    request_batch = Signal()
    request_open_result = Signal(int)

    def __init__(self, db: "Database", parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self._db = db
        self._build_ui()
        self.refresh()

    # ── build ─────────────────────────────────────────────────────────────────

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(24, 20, 24, 20)
        root.setSpacing(20)

        # Page header
        hdr = QHBoxLayout()
        title = QLabel("Dashboard")
        font = title.font()
        font.setPointSize(16)
        font.setWeight(QFont.Weight.Bold)
        title.setFont(font)
        self._last_refresh = QLabel()
        self._last_refresh.setObjectName("SubLabel")
        hdr.addWidget(title)
        hdr.addStretch()
        hdr.addWidget(self._last_refresh)

        refresh_btn = QPushButton("⟳ Refresh")
        refresh_btn.setObjectName("FlatButton")
        refresh_btn.clicked.connect(self.refresh)
        hdr.addWidget(refresh_btn)
        root.addLayout(hdr)

        # ── KPI cards row ──────────────────────────────────────────────────────
        cards_row = QHBoxLayout()
        cards_row.setSpacing(14)

        self._card_total    = StatCard("Total Analyses", "—", accent_color=ACCENT)
        self._card_f1       = StatCard("Avg Macro-F1", "—", accent_color=SUCCESS)
        self._card_flagged  = StatCard("Flagged Today", "—", accent_color=WARNING)
        self._card_api      = StatCard("API Calls Today", "—", accent_color="#a855f7")

        for c in [self._card_total, self._card_f1, self._card_flagged, self._card_api]:
            cards_row.addWidget(c)
        root.addLayout(cards_row)

        # ── Quick actions ──────────────────────────────────────────────────────
        qa_row = QHBoxLayout()
        qa_row.setSpacing(10)

        btn_new = QPushButton("+ New Analysis")
        btn_new.setProperty("primary", "true")
        btn_new.setMinimumHeight(36)
        btn_new.clicked.connect(self.request_new_analysis.emit)

        btn_import = QPushButton("↑ Import Signal")
        btn_import.setMinimumHeight(36)
        btn_import.clicked.connect(self.request_import.emit)

        btn_batch = QPushButton("⋮ Batch Run")
        btn_batch.setMinimumHeight(36)
        btn_batch.clicked.connect(self.request_batch.emit)

        qa_row.addWidget(btn_new)
        qa_row.addWidget(btn_import)
        qa_row.addWidget(btn_batch)
        qa_row.addStretch()
        root.addLayout(qa_row)

        # ── Middle section: table + chart ──────────────────────────────────────
        mid = QHBoxLayout()
        mid.setSpacing(16)

        # Recent results table
        table_frame = QFrame()
        table_frame.setObjectName("Card")
        tf_lay = QVBoxLayout(table_frame)
        tf_lay.setContentsMargins(12, 10, 12, 10)
        tf_lay.setSpacing(8)

        tbl_hdr = QLabel("Recent Results")
        f = tbl_hdr.font()
        f.setWeight(QFont.Weight.Bold)
        tbl_hdr.setFont(f)
        tf_lay.addWidget(tbl_hdr)

        self._table = QTableWidget(0, 6)
        self._table.setHorizontalHeaderLabels(
            ["Date", "Signal", "Model", "Rhythm", "Conf.", "Flag"]
        )
        self._table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self._table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self._table.verticalHeader().setVisible(False)
        self._table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self._table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self._table.setAlternatingRowColors(True)
        self._table.doubleClicked.connect(self._on_row_double_click)
        tf_lay.addWidget(self._table)
        mid.addWidget(table_frame, 3)

        # Rhythm distribution chart
        chart_frame = QFrame()
        chart_frame.setObjectName("Card")
        chart_frame.setMinimumWidth(260)
        chart_frame.setMaximumWidth(360)
        cf_lay = QVBoxLayout(chart_frame)
        cf_lay.setContentsMargins(12, 10, 12, 10)
        cf_lay.setSpacing(8)

        chart_lbl = QLabel("Rhythm Distribution")
        f2 = chart_lbl.font()
        f2.setWeight(QFont.Weight.Bold)
        chart_lbl.setFont(f2)
        cf_lay.addWidget(chart_lbl)

        if _HAS_PG:
            self._pie_widget = pg.PlotWidget()
            self._pie_widget.setBackground("#1f2937")
            self._pie_widget.setAspectLocked(True)
            self._pie_widget.getAxis("left").hide()
            self._pie_widget.getAxis("bottom").hide()
            self._pie_widget.setMenuEnabled(False)
            cf_lay.addWidget(self._pie_widget)
        else:
            self._pie_widget = None
            no_chart = QLabel("Chart requires pyqtgraph")
            no_chart.setObjectName("SubLabel")
            no_chart.setAlignment(Qt.AlignmentFlag.AlignCenter)
            cf_lay.addWidget(no_chart)

        # Legend placeholder
        self._legend_layout = QVBoxLayout()
        self._legend_layout.setSpacing(3)
        cf_lay.addLayout(self._legend_layout)
        cf_lay.addStretch()

        mid.addWidget(chart_frame, 2)
        root.addLayout(mid)

        root.addStretch()

    # ── refresh ───────────────────────────────────────────────────────────────

    def refresh(self) -> None:
        self._last_refresh.setText(
            f"Last updated: {datetime.now().strftime('%H:%M:%S')}"
        )
        self._update_kpis()
        self._update_table()
        self._update_chart()

    def _update_kpis(self) -> None:
        total = self._db.count_results()
        avg_f1 = self._db.avg_macro_f1()
        flagged = self._db.count_flagged_today()
        api_calls = self._db.api_calls_today()

        self._card_total.update_value(str(total))
        self._card_f1.update_value(f"{avg_f1:.3f}" if avg_f1 > 0 else "—")
        self._card_flagged.update_value(str(flagged))
        self._card_api.update_value(str(api_calls))

    def _update_table(self) -> None:
        rows = self._db.get_results(limit=10)
        self._table.setRowCount(0)
        self._row_ids: list = []

        for row in rows:
            r = self._table.rowCount()
            self._table.insertRow(r)
            self._row_ids.append(row["id"])

            ts = datetime.fromtimestamp(row["created_at"]).strftime("%m/%d %H:%M")
            sig = row.get("signal_file", "—")[:24]
            model = row.get("model_name", "—")[:18]
            rhythm = row.get("rhythm", "—")
            conf_pct = f"{row.get('confidence', 0) * 100:.0f}%"
            flagged = "⚠" if row.get("review_flag") else "✓"

            for col, text in enumerate([ts, sig, model, rhythm, conf_pct, flagged]):
                item = QTableWidgetItem(text)
                item.setTextAlignment(Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft)
                if col == 5:
                    color = DANGER if row.get("review_flag") else SUCCESS
                    item.setForeground(__import__("PySide6.QtGui", fromlist=["QColor"]).QColor(color))
                self._table.setItem(r, col, item)

    def _update_chart(self) -> None:
        dist = self._db.rhythm_distribution()
        if not dist:
            return

        # Clear legend
        while self._legend_layout.count():
            item = self._legend_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        COLORS = [
            "#2563eb", "#10b981", "#f59e0b", "#ef4444",
            "#a855f7", "#38bdf8", "#fb923c", "#f472b6",
        ]

        if _HAS_PG and self._pie_widget is not None:
            self._pie_widget.clear()
            total = sum(dist.values()) or 1
            items = list(dist.items())[:8]
            angle = 0.0
            for i, (rhythm, count) in enumerate(items):
                frac = count / total
                span = frac * 360
                color = COLORS[i % len(COLORS)]
                pie = pg.QtWidgets.QGraphicsEllipseItem(-1, -1, 2, 2)
                pie.setStartAngle(int(angle * 16))
                pie.setSpanAngle(int(span * 16))
                pie.setBrush(__import__("PySide6.QtGui", fromlist=["QBrush"]).QBrush(
                    __import__("PySide6.QtGui", fromlist=["QColor"]).QColor(color)))
                pie.setPen(__import__("PySide6.QtGui", fromlist=["QPen"]).QPen(
                    __import__("PySide6.QtGui", fromlist=["QColor"]).QColor("#0d1117"), 0.02))
                self._pie_widget.addItem(pie)
                angle += span

                # Legend row
                lrow = QHBoxLayout()
                dot = QLabel("●")
                dot.setStyleSheet(f"color: {color}; font-size: 14pt;")
                dot.setFixedWidth(20)
                name = QLabel(f"{rhythm[:22]}  ({count})")
                name.setObjectName("SubLabel")
                lrow.addWidget(dot)
                lrow.addWidget(name)
                lrow.addStretch()
                container = QWidget()
                container.setLayout(lrow)
                self._legend_layout.addWidget(container)
        else:
            # Text fallback
            for i, (rhythm, count) in enumerate(list(dist.items())[:8]):
                color = COLORS[i % len(COLORS)]
                lbl = QLabel(f"  {rhythm}: {count}")
                lbl.setStyleSheet(f"color: {color};")
                lbl.setObjectName("SubLabel")
                self._legend_layout.addWidget(lbl)

    def _on_row_double_click(self, index) -> None:
        row = index.row()
        if 0 <= row < len(self._row_ids):
            self.request_open_result.emit(self._row_ids[row])
