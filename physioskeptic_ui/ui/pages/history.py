"""
History Page — PhysioSkeptic
Searchable, sortable results history with detail panel.
"""
from __future__ import annotations

import json
from datetime import datetime
from typing import Optional, List, TYPE_CHECKING

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame, QPushButton,
    QTableWidget, QTableWidgetItem, QHeaderView, QLineEdit, QComboBox,
    QCheckBox, QSplitter, QFileDialog, QDateEdit, QScrollArea,
    QAbstractItemView, QSizePolicy, QGroupBox, QGridLayout,
)
from PySide6.QtCore import Qt, Signal, QDate
from PySide6.QtGui import QColor, QFont

from ..theme import ACCENT, SUCCESS, WARNING, DANGER, TEXT_SECONDARY
from core.pipeline import RHYTHM_CLASSES

if TYPE_CHECKING:
    from core.database import Database


class HistoryPage(QWidget):
    """History browser with filters and detail side panel."""

    open_in_viewer = Signal(dict)   # row dict from DB

    def __init__(self, db: "Database", parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self._db = db
        self._row_ids: List[int] = []
        self._build_ui()
        self.refresh()

    # ── build ─────────────────────────────────────────────────────────────────

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # Header
        hdr = QFrame()
        hdr.setFixedHeight(56)
        hdr_lay = QHBoxLayout(hdr)
        hdr_lay.setContentsMargins(24, 0, 24, 0)
        title = QLabel("Result History")
        f = title.font()
        f.setPointSize(14)
        f.setBold(True)
        title.setFont(f)
        hdr_lay.addWidget(title)
        hdr_lay.addStretch()

        self._export_btn = QPushButton("Export CSV")
        self._export_btn.clicked.connect(self._export_csv)

        self._delete_btn = QPushButton("Delete Selected")
        self._delete_btn.setObjectName("DangerButton")
        self._delete_btn.clicked.connect(self._delete_selected)

        self._refresh_btn = QPushButton("⟳ Refresh")
        self._refresh_btn.setObjectName("FlatButton")
        self._refresh_btn.clicked.connect(self.refresh)

        for b in [self._refresh_btn, self._export_btn, self._delete_btn]:
            hdr_lay.addWidget(b)
        root.addWidget(hdr)

        div = QFrame()
        div.setObjectName("Divider")
        div.setFixedHeight(1)
        root.addWidget(div)

        # Filter bar
        filter_frame = QFrame()
        filter_frame.setFixedHeight(52)
        ff_lay = QHBoxLayout(filter_frame)
        ff_lay.setContentsMargins(16, 8, 16, 8)
        ff_lay.setSpacing(10)

        self._search_edit = QLineEdit()
        self._search_edit.setPlaceholderText("Search by file, patient, rhythm...")
        self._search_edit.setMaximumWidth(280)
        self._search_edit.textChanged.connect(self.refresh)

        self._rhythm_filter = QComboBox()
        self._rhythm_filter.addItem("All Rhythms", None)
        for r in RHYTHM_CLASSES:
            self._rhythm_filter.addItem(r, r)
        self._rhythm_filter.currentIndexChanged.connect(self.refresh)
        self._rhythm_filter.setMaximumWidth(220)

        self._model_filter = QComboBox()
        self._model_filter.addItems(["All Models", "Mock / Demo", "GPT-4o",
                                     "Claude-3.7", "DeepSeek-V3.2"])
        self._model_filter.currentIndexChanged.connect(self.refresh)
        self._model_filter.setMaximumWidth(160)

        self._flagged_only = QCheckBox("Flagged only")
        self._flagged_only.stateChanged.connect(self.refresh)

        ff_lay.addWidget(QLabel("🔍"))
        ff_lay.addWidget(self._search_edit)
        ff_lay.addWidget(self._rhythm_filter)
        ff_lay.addWidget(self._model_filter)
        ff_lay.addWidget(self._flagged_only)
        ff_lay.addStretch()

        self._count_lbl = QLabel("0 records")
        self._count_lbl.setObjectName("SubLabel")
        ff_lay.addWidget(self._count_lbl)
        root.addWidget(filter_frame)

        div2 = QFrame()
        div2.setObjectName("Divider")
        div2.setFixedHeight(1)
        root.addWidget(div2)

        # Splitter: table + detail
        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.setHandleWidth(2)

        # ── Table ─────────────────────────────────────────────────────────
        self._table = QTableWidget(0, 8)
        self._table.setHorizontalHeaderLabels(
            ["Date", "Signal", "Model", "Rhythm", "Conf.", "F1", "Flagged", "Duration"]
        )
        hh = self._table.horizontalHeader()
        hh.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        hh.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        hh.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        hh.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        hh.setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)
        hh.setSectionResizeMode(5, QHeaderView.ResizeMode.ResizeToContents)
        hh.setSectionResizeMode(6, QHeaderView.ResizeMode.ResizeToContents)
        hh.setSectionResizeMode(7, QHeaderView.ResizeMode.ResizeToContents)
        hh.setSortIndicatorShown(True)
        self._table.setSortingEnabled(True)
        self._table.verticalHeader().setVisible(False)
        self._table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self._table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self._table.setAlternatingRowColors(True)
        self._table.selectionModel().selectionChanged.connect(self._on_selection_changed)
        splitter.addWidget(self._table)

        # ── Detail Panel ──────────────────────────────────────────────────
        detail_scroll = QScrollArea()
        detail_scroll.setWidgetResizable(True)
        detail_scroll.setMinimumWidth(300)
        detail_scroll.setMaximumWidth(400)
        detail_widget = QWidget()
        self._detail_lay = QVBoxLayout(detail_widget)
        self._detail_lay.setContentsMargins(12, 12, 12, 12)
        self._detail_lay.setSpacing(10)
        detail_scroll.setWidget(detail_widget)

        self._detail_placeholder = QLabel("Select a row to view details.")
        self._detail_placeholder.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._detail_placeholder.setObjectName("SubLabel")
        self._detail_lay.addWidget(self._detail_placeholder)

        # Detail cards (hidden initially)
        self._detail_result_card = self._make_detail_group("Analysis Result")
        self._detail_signal_card = self._make_detail_group("Signal Info")
        self._detail_tokens_card = self._make_detail_group("API Usage")
        for c in [self._detail_result_card, self._detail_signal_card, self._detail_tokens_card]:
            c.setVisible(False)
            self._detail_lay.addWidget(c)

        self._detail_lay.addStretch()
        splitter.addWidget(detail_scroll)

        splitter.setSizes([900, 350])
        root.addWidget(splitter)

    def _make_detail_group(self, title: str) -> QGroupBox:
        g = QGroupBox(title)
        lay = QGridLayout(g)
        lay.setSpacing(6)
        return g

    # ── public ────────────────────────────────────────────────────────────────

    def refresh(self) -> None:
        search = self._search_edit.text().strip() or None
        rhythm = self._rhythm_filter.currentData()
        model = self._model_filter.currentText()
        if model == "All Models":
            model = None
        flagged = self._flagged_only.isChecked()

        rows = self._db.get_results(
            limit=500,
            rhythm_filter=rhythm,
            model_filter=model,
            flagged_only=flagged,
            search=search,
        )

        self._table.setSortingEnabled(False)
        self._table.setRowCount(0)
        self._row_ids = []

        for row in rows:
            r = self._table.rowCount()
            self._table.insertRow(r)
            self._row_ids.append(row["id"])

            ts = datetime.fromtimestamp(row["created_at"]).strftime("%Y-%m-%d %H:%M")
            sig = (row.get("signal_file") or "—")[:28]
            model_s = (row.get("model_name") or "—")[:16]
            rhythm_s = row.get("rhythm") or "—"
            conf_s = f"{row.get('confidence', 0)*100:.0f}%"
            f1_s = f"{row.get('macro_f1', 0):.3f}"
            flagged_s = "⚠ Yes" if row.get("review_flag") else "No"
            dur_s = f"{row.get('analysis_duration', 0):.1f}s"

            values = [ts, sig, model_s, rhythm_s, conf_s, f1_s, flagged_s, dur_s]
            for col, val in enumerate(values):
                item = QTableWidgetItem(val)
                item.setTextAlignment(Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft)
                if col == 6 and row.get("review_flag"):
                    item.setForeground(QColor(DANGER))
                self._table.setItem(r, col, item)

        self._table.setSortingEnabled(True)
        self._count_lbl.setText(f"{len(rows)} records")

    def _on_selection_changed(self, selected, deselected) -> None:
        rows = self._table.selectionModel().selectedRows()
        if not rows:
            self._show_detail(None)
            return
        row_idx = rows[0].row()
        if row_idx < len(self._row_ids):
            db_row = self._db.get_result_by_id(self._row_ids[row_idx])
            self._show_detail(db_row)

    def _show_detail(self, row) -> None:
        if row is None:
            self._detail_placeholder.setVisible(True)
            for c in [self._detail_result_card, self._detail_signal_card, self._detail_tokens_card]:
                c.setVisible(False)
            return

        self._detail_placeholder.setVisible(False)

        def _populate(group: QGroupBox, data: dict) -> None:
            lay = group.layout()
            # clear old widgets
            while lay.count():
                item = lay.takeAt(0)
                if item.widget():
                    item.widget().deleteLater()
            for r, (k, v) in enumerate(data.items()):
                k_lbl = QLabel(str(k) + ":")
                k_lbl.setObjectName("SubLabel")
                v_lbl = QLabel(str(v))
                v_lbl.setWordWrap(True)
                lay.addWidget(k_lbl, r, 0)
                lay.addWidget(v_lbl, r, 1)

        flag_str = "YES ⚠" if row.get("review_flag") else "No"
        _populate(self._detail_result_card, {
            "Rhythm": row.get("rhythm", "—"),
            "Confidence": f"{row.get('confidence',0)*100:.1f}%",
            "Review Flag": flag_str,
            "Reason": row.get("review_reason") or "—",
            "ECE": f"{row.get('ece',0):.4f}",
            "Macro-F1": f"{row.get('macro_f1',0):.3f}",
            "Model": row.get("model_name", "—"),
            "Routing": row.get("routing", "—"),
            "Duration": f"{row.get('analysis_duration',0):.2f}s",
        })

        ts = datetime.fromtimestamp(row["created_at"]).strftime("%Y-%m-%d %H:%M:%S")
        _populate(self._detail_signal_card, {
            "File": row.get("signal_file", "—"),
            "Format": row.get("signal_format", "—"),
            "Patient ID": row.get("patient_id") or "—",
            "Duration": f"{row.get('duration_sec',0):.1f}s",
            "Fs": f"{row.get('fs',125):.0f} Hz",
            "Timestamp": ts,
        })

        cost = row.get("total_cost_usd", 0)
        _populate(self._detail_tokens_card, {
            "Input Tokens": f"{row.get('total_input_tokens',0):,}",
            "Output Tokens": f"{row.get('total_output_tokens',0):,}",
            "Est. Cost": f"${cost:.4f}" if cost > 0 else "—",
        })

        for c in [self._detail_result_card, self._detail_signal_card, self._detail_tokens_card]:
            c.setVisible(True)

    def _delete_selected(self) -> None:
        rows = sorted(set(i.row() for i in self._table.selectedItems()), reverse=True)
        ids = [self._row_ids[r] for r in rows if r < len(self._row_ids)]
        if not ids:
            return
        self._db.delete_results(ids)
        self.refresh()

    def _export_csv(self) -> None:
        path, _ = QFileDialog.getSaveFileName(
            self, "Export History", "history.csv", "CSV Files (*.csv)"
        )
        if not path:
            return
        rows = self._table.selectionModel().selectedRows()
        if rows:
            ids = [self._row_ids[r.row()] for r in rows if r.row() < len(self._row_ids)]
        else:
            ids = None
        n = self._db.export_csv(path, ids)
        self._count_lbl.setText(f"Exported {n} records → {path}")
