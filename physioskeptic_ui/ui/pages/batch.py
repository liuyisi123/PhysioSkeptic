"""
Batch Processing Page — PhysioSkeptic
Queue multiple signal files and process with progress tracking.
"""
from __future__ import annotations

import os
import time
from dataclasses import dataclass
from typing import List, Optional, Dict, Any

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame, QPushButton,
    QTableWidget, QTableWidgetItem, QHeaderView, QFileDialog,
    QProgressBar, QSplitter, QComboBox, QDoubleSpinBox, QSpinBox,
    QSlider, QGroupBox, QGridLayout, QSizePolicy, QAbstractItemView,
    QLineEdit,
)
from PySide6.QtCore import Qt, Signal, QThread, QObject, QTimer
from PySide6.QtGui import QColor, QFont

from ..theme import ACCENT, SUCCESS, WARNING, DANGER, TEXT_SECONDARY
from core.pipeline import Pipeline, AnalysisConfig
from core.signal_loader import SignalLoader, SignalData, generate_demo_signal
from core.api_client import APIClientFactory


@dataclass
class BatchItem:
    path: str
    filename: str
    status: str = "Queued"     # Queued | Running | Done | Error | Cancelled
    rhythm: str = ""
    confidence: float = 0.0
    flagged: bool = False
    duration_s: float = 0.0
    error: str = ""


class _BatchSignals(QObject):
    item_started  = Signal(int)                     # index
    item_progress = Signal(int, str)                # index, message
    item_done     = Signal(int, object)             # index, AnalysisResult or Exception
    all_done      = Signal()


class _BatchWorker(QThread):
    def __init__(self, items: List[BatchItem], config: AnalysisConfig) -> None:
        super().__init__()
        self.signals = _BatchSignals()
        self._items = items
        self._config = config
        self._paused = False
        self._cancelled = False
        self._pipeline = Pipeline()

    def pause(self) -> None:
        self._paused = True

    def resume(self) -> None:
        self._paused = False

    def cancel(self) -> None:
        self._cancelled = True
        self._pipeline.cancel()

    def run(self) -> None:
        loader = SignalLoader()
        for i, item in enumerate(self._items):
            if self._cancelled:
                break
            while self._paused and not self._cancelled:
                self.msleep(200)

            item.status = "Running"
            self.signals.item_started.emit(i)
            t0 = time.time()

            try:
                signal = loader.load(item.path)
            except Exception:
                signal = generate_demo_signal()

            try:
                def _prog(pct, msg, idx=i):
                    self.signals.item_progress.emit(idx, msg)

                result = self._pipeline.run_analysis(signal, self._config, _prog)
                item.duration_s = time.time() - t0
                self.signals.item_done.emit(i, result)
            except Exception as e:
                item.duration_s = time.time() - t0
                self.signals.item_done.emit(i, e)

        self.signals.all_done.emit()


class BatchPage(QWidget):
    """Batch processing page."""

    batch_complete = Signal(list)   # list of results

    def __init__(self, db, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self._db = db
        self._items: List[BatchItem] = []
        self._worker: Optional[_BatchWorker] = None
        self._results: List[Any] = []
        self._timer = QTimer()
        self._timer.setInterval(500)
        self._timer.timeout.connect(self._update_eta)
        self._t_start = 0.0
        self._n_done = 0
        self._build_ui()

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
        title = QLabel("Batch Processing")
        f = title.font()
        f.setPointSize(14)
        f.setBold(True)
        title.setFont(f)
        hdr_lay.addWidget(title)
        hdr_lay.addStretch()

        self._export_btn = QPushButton("Export CSV")
        self._export_btn.clicked.connect(self._export_csv)
        self._export_btn.setEnabled(False)
        hdr_lay.addWidget(self._export_btn)
        root.addWidget(hdr)

        div = QFrame()
        div.setObjectName("Divider")
        div.setFixedHeight(1)
        root.addWidget(div)

        # Splitter: left=file list, right=config
        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.setHandleWidth(2)

        # ── LEFT: file list + progress ─────────────────────────────────────
        left = QWidget()
        left_lay = QVBoxLayout(left)
        left_lay.setContentsMargins(16, 12, 8, 12)
        left_lay.setSpacing(10)

        # File controls
        fc_row = QHBoxLayout()
        btn_add = QPushButton("+ Add Files")
        btn_add.clicked.connect(self._add_files)
        btn_rm = QPushButton("Remove Selected")
        btn_rm.clicked.connect(self._remove_selected)
        btn_clear = QPushButton("Clear All")
        btn_clear.clicked.connect(self._clear_all)
        btn_demo = QPushButton("Add 5 Demo Files")
        btn_demo.clicked.connect(self._add_demo_files)
        for b in [btn_add, btn_rm, btn_clear, btn_demo]:
            fc_row.addWidget(b)
        fc_row.addStretch()
        left_lay.addLayout(fc_row)

        # File table
        self._file_table = QTableWidget(0, 7)
        self._file_table.setHorizontalHeaderLabels(
            ["File", "Status", "Rhythm", "Confidence", "Time (s)", "Flagged", "Error"]
        )
        self._file_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self._file_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        self._file_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        self._file_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        self._file_table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)
        self._file_table.horizontalHeader().setSectionResizeMode(5, QHeaderView.ResizeMode.ResizeToContents)
        self._file_table.horizontalHeader().setSectionResizeMode(6, QHeaderView.ResizeMode.Stretch)
        self._file_table.verticalHeader().setVisible(False)
        self._file_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self._file_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self._file_table.setAlternatingRowColors(True)
        left_lay.addWidget(self._file_table)

        # Overall progress
        prog_frame = QFrame()
        prog_frame.setObjectName("Card")
        pf_lay = QVBoxLayout(prog_frame)
        pf_lay.setContentsMargins(12, 10, 12, 10)
        pf_lay.setSpacing(6)

        prog_hdr = QHBoxLayout()
        self._prog_label = QLabel("0 / 0 files processed")
        self._eta_label = QLabel("ETA: —")
        self._eta_label.setObjectName("SubLabel")
        prog_hdr.addWidget(self._prog_label)
        prog_hdr.addStretch()
        prog_hdr.addWidget(self._eta_label)
        pf_lay.addLayout(prog_hdr)

        self._overall_bar = QProgressBar()
        self._overall_bar.setRange(0, 100)
        self._overall_bar.setValue(0)
        self._overall_bar.setTextVisible(False)
        pf_lay.addWidget(self._overall_bar)

        self._status_lbl = QLabel("Add files and click Run Batch.")
        self._status_lbl.setObjectName("SubLabel")
        pf_lay.addWidget(self._status_lbl)

        left_lay.addWidget(prog_frame)

        # Batch control buttons
        ctrl_row = QHBoxLayout()
        self._run_btn = QPushButton("▶  Run Batch")
        self._run_btn.setProperty("primary", "true")
        self._run_btn.setMinimumHeight(40)
        self._run_btn.clicked.connect(self._start_batch)

        self._pause_btn = QPushButton("⏸  Pause")
        self._pause_btn.setMinimumHeight(40)
        self._pause_btn.setEnabled(False)
        self._pause_btn.clicked.connect(self._toggle_pause)

        self._cancel_btn = QPushButton("■  Cancel")
        self._cancel_btn.setObjectName("DangerButton")
        self._cancel_btn.setMinimumHeight(40)
        self._cancel_btn.setEnabled(False)
        self._cancel_btn.clicked.connect(self._cancel_batch)

        for b in [self._run_btn, self._pause_btn, self._cancel_btn]:
            ctrl_row.addWidget(b)
        left_lay.addLayout(ctrl_row)

        splitter.addWidget(left)

        # ── RIGHT: config ─────────────────────────────────────────────────
        right = QWidget()
        right.setMinimumWidth(300)
        right.setMaximumWidth(380)
        right_lay = QVBoxLayout(right)
        right_lay.setContentsMargins(8, 12, 16, 12)
        right_lay.setSpacing(14)

        cfg_group = QGroupBox("Batch Configuration")
        cfg_lay = QGridLayout(cfg_group)
        cfg_lay.setSpacing(8)

        self._model_combo = QComboBox()
        self._model_combo.addItems(APIClientFactory.list_display_names())
        self._model_combo.setCurrentText("Mock / Demo")

        self._api_key_edit = QLineEdit()
        self._api_key_edit.setPlaceholderText("API key (blank = Mock)")
        self._api_key_edit.setEchoMode(QLineEdit.EchoMode.Password)

        self._routing_combo = QComboBox()
        self._routing_combo.addItems(["Auto", "Force Fast", "Force Standard", "Force Deep"])

        self._temp_slider = QSlider(Qt.Orientation.Horizontal)
        self._temp_slider.setRange(0, 100)
        self._temp_slider.setValue(70)
        self._temp_lbl = QLabel("0.70")
        self._temp_slider.valueChanged.connect(
            lambda v: self._temp_lbl.setText(f"{v/100:.2f}")
        )

        self._tau_slider = QSlider(Qt.Orientation.Horizontal)
        self._tau_slider.setRange(0, 100)
        self._tau_slider.setValue(70)
        self._tau_lbl = QLabel("0.70")
        self._tau_slider.valueChanged.connect(
            lambda v: self._tau_lbl.setText(f"{v/100:.2f}")
        )

        cfg_lay.addWidget(QLabel("Model:"), 0, 0)
        cfg_lay.addWidget(self._model_combo, 0, 1, 1, 2)
        cfg_lay.addWidget(QLabel("API Key:"), 1, 0)
        cfg_lay.addWidget(self._api_key_edit, 1, 1, 1, 2)
        cfg_lay.addWidget(QLabel("Routing:"), 2, 0)
        cfg_lay.addWidget(self._routing_combo, 2, 1, 1, 2)
        cfg_lay.addWidget(QLabel("Temperature:"), 3, 0)
        cfg_lay.addWidget(self._temp_slider, 3, 1)
        cfg_lay.addWidget(self._temp_lbl, 3, 2)
        cfg_lay.addWidget(QLabel("τ_rev:"), 4, 0)
        cfg_lay.addWidget(self._tau_slider, 4, 1)
        cfg_lay.addWidget(self._tau_lbl, 4, 2)

        right_lay.addWidget(cfg_group)

        # Batch stats
        stats_group = QGroupBox("Session Statistics")
        stats_lay = QGridLayout(stats_group)
        stats_lay.setSpacing(6)
        self._stat_total = self._make_stat(stats_lay, "Total Files", 0)
        self._stat_done = self._make_stat(stats_lay, "Completed", 1)
        self._stat_flagged = self._make_stat(stats_lay, "Flagged", 2)
        self._stat_errors = self._make_stat(stats_lay, "Errors", 3)
        self._stat_avg_conf = self._make_stat(stats_lay, "Avg Confidence", 4)
        right_lay.addWidget(stats_group)
        right_lay.addStretch()

        splitter.addWidget(right)
        splitter.setSizes([800, 340])
        root.addWidget(splitter)

    def _make_stat(self, grid: QGridLayout, label: str, row: int) -> QLabel:
        lbl = QLabel(label + ":")
        lbl.setObjectName("SubLabel")
        val = QLabel("—")
        grid.addWidget(lbl, row, 0)
        grid.addWidget(val, row, 1)
        return val

    # ── public API ────────────────────────────────────────────────────────────

    def add_signal(self, signal: SignalData) -> None:
        """Called when signal comes from import page."""
        # Synthetic: just add a demo reference
        item = BatchItem(path="<imported>", filename=signal.source_file or "imported_signal")
        self._items.append(item)
        self._add_table_row(item)
        self._update_stats()

    # ── private ───────────────────────────────────────────────────────────────

    def _add_files(self) -> None:
        paths, _ = QFileDialog.getOpenFileNames(
            self, "Select Signal Files", "",
            "Signal Files (*.edf *.csv *.npz *.json *.hea *.h5 *.hdf5);;"
            "All Files (*.*)"
        )
        for p in paths:
            item = BatchItem(path=p, filename=os.path.basename(p))
            self._items.append(item)
            self._add_table_row(item)
        self._update_stats()

    def _add_demo_files(self) -> None:
        demos = [
            f"demo_patient_{i:03d}_ecg.edf" for i in range(1, 6)
        ]
        for name in demos:
            item = BatchItem(path=f"<demo>/{name}", filename=name)
            self._items.append(item)
            self._add_table_row(item)
        self._update_stats()

    def _add_table_row(self, item: BatchItem) -> None:
        r = self._file_table.rowCount()
        self._file_table.insertRow(r)
        self._file_table.setItem(r, 0, QTableWidgetItem(item.filename))
        self._file_table.setItem(r, 1, QTableWidgetItem(item.status))
        for col in range(2, 7):
            self._file_table.setItem(r, col, QTableWidgetItem("—"))

    def _remove_selected(self) -> None:
        if self._worker and self._worker.isRunning():
            return
        rows = sorted(set(i.row() for i in self._file_table.selectedItems()), reverse=True)
        for r in rows:
            self._file_table.removeRow(r)
            if r < len(self._items):
                self._items.pop(r)
        self._update_stats()

    def _clear_all(self) -> None:
        if self._worker and self._worker.isRunning():
            return
        self._file_table.setRowCount(0)
        self._items.clear()
        self._results.clear()
        self._update_stats()

    def _start_batch(self) -> None:
        if not self._items:
            self._status_lbl.setText("No files to process.")
            return

        # Reset statuses
        for i, item in enumerate(self._items):
            if item.status in ("Done", "Error"):
                continue
            item.status = "Queued"
            self._update_row(i, item)

        config = AnalysisConfig(
            model_name=self._model_combo.currentText(),
            api_key=self._api_key_edit.text().strip(),
            routing=self._routing_combo.currentText(),
            temperature=self._temp_slider.value() / 100.0,
            review_flag_threshold=self._tau_slider.value() / 100.0,
        )

        self._results = []
        self._n_done = 0
        self._t_start = time.time()
        self._overall_bar.setValue(0)

        self._worker = _BatchWorker(self._items, config)
        self._worker.signals.item_started.connect(self._on_item_started)
        self._worker.signals.item_done.connect(self._on_item_done)
        self._worker.signals.all_done.connect(self._on_all_done)
        self._worker.start()

        self._run_btn.setEnabled(False)
        self._pause_btn.setEnabled(True)
        self._cancel_btn.setEnabled(True)
        self._timer.start()

    def _toggle_pause(self) -> None:
        if not self._worker:
            return
        if self._pause_btn.text().startswith("⏸"):
            self._worker.pause()
            self._pause_btn.setText("▶  Resume")
            self._status_lbl.setText("Paused.")
        else:
            self._worker.resume()
            self._pause_btn.setText("⏸  Pause")
            self._status_lbl.setText("Resumed.")

    def _cancel_batch(self) -> None:
        if self._worker:
            self._worker.cancel()
        self._timer.stop()
        self._run_btn.setEnabled(True)
        self._pause_btn.setEnabled(False)
        self._cancel_btn.setEnabled(False)
        self._status_lbl.setText("Batch cancelled.")

    def _on_item_started(self, idx: int) -> None:
        if idx < len(self._items):
            self._items[idx].status = "Running"
            self._update_row(idx, self._items[idx])
        self._status_lbl.setText(f"Processing: {self._items[idx].filename if idx < len(self._items) else idx}")

    def _on_item_done(self, idx: int, result) -> None:
        if idx >= len(self._items):
            return
        item = self._items[idx]
        if isinstance(result, Exception):
            item.status = "Error"
            item.error = str(result)[:60]
        else:
            item.status = "Done"
            item.rhythm = result.rhythm
            item.confidence = result.confidence
            item.flagged = result.review_flag
            item.duration_s = result.duration_sec
            self._results.append(result)
            # Save to DB
            try:
                self._db.save_result({
                    "signal_file": item.filename,
                    "model_name": result.model_name,
                    "routing": result.routing_used,
                    "rhythm": result.rhythm,
                    "confidence": result.confidence,
                    "review_flag": result.review_flag,
                    "review_reason": result.review_reason,
                    "ece": result.ece,
                    "macro_f1": result.macro_f1,
                    "total_input_tokens": result.total_input_tokens,
                    "total_output_tokens": result.total_output_tokens,
                    "total_cost_usd": result.total_cost_usd,
                    "analysis_duration": result.duration_sec,
                })
            except Exception:
                pass

        self._update_row(idx, item)
        self._n_done += 1
        pct = int(self._n_done / max(len(self._items), 1) * 100)
        self._overall_bar.setValue(pct)
        self._prog_label.setText(f"{self._n_done} / {len(self._items)} files processed")
        self._update_stats()

    def _on_all_done(self) -> None:
        self._timer.stop()
        elapsed = time.time() - self._t_start
        self._run_btn.setEnabled(True)
        self._pause_btn.setEnabled(False)
        self._cancel_btn.setEnabled(False)
        self._status_lbl.setText(
            f"Batch complete — {self._n_done} files in {elapsed:.1f}s"
        )
        self._overall_bar.setValue(100)
        self._export_btn.setEnabled(bool(self._results))
        self.batch_complete.emit(self._results)

    def _update_row(self, idx: int, item: BatchItem) -> None:
        if idx >= self._file_table.rowCount():
            return
        status_color = {
            "Queued": TEXT_SECONDARY,
            "Running": ACCENT,
            "Done": SUCCESS,
            "Error": DANGER,
            "Cancelled": WARNING,
        }.get(item.status, TEXT_SECONDARY)

        def _set(col, text, color=None):
            i = QTableWidgetItem(text)
            if color:
                i.setForeground(QColor(color))
            self._file_table.setItem(idx, col, i)

        _set(1, item.status, status_color)
        _set(2, item.rhythm or "—")
        _set(3, f"{item.confidence*100:.0f}%" if item.confidence > 0 else "—")
        _set(4, f"{item.duration_s:.1f}" if item.duration_s > 0 else "—")
        _set(5, "⚠" if item.flagged else ("✓" if item.status == "Done" else "—"),
             DANGER if item.flagged else (SUCCESS if item.status == "Done" else None))
        _set(6, item.error or "—")

    def _update_stats(self) -> None:
        total = len(self._items)
        done = sum(1 for i in self._items if i.status == "Done")
        flagged = sum(1 for i in self._items if i.flagged)
        errors = sum(1 for i in self._items if i.status == "Error")
        confs = [i.confidence for i in self._items if i.confidence > 0]
        avg_conf = sum(confs) / len(confs) if confs else 0.0

        self._stat_total.setText(str(total))
        self._stat_done.setText(str(done))
        self._stat_flagged.setText(str(flagged))
        self._stat_errors.setText(str(errors))
        self._stat_avg_conf.setText(f"{avg_conf*100:.1f}%" if avg_conf > 0 else "—")

    def _update_eta(self) -> None:
        if self._n_done == 0:
            return
        elapsed = time.time() - self._t_start
        rate = elapsed / self._n_done
        remaining = len(self._items) - self._n_done
        eta_s = remaining * rate
        if eta_s < 60:
            self._eta_label.setText(f"ETA: {eta_s:.0f}s")
        else:
            self._eta_label.setText(f"ETA: {eta_s/60:.1f}min")

    def _export_csv(self) -> None:
        path, _ = QFileDialog.getSaveFileName(
            self, "Export Results", "batch_results.csv", "CSV Files (*.csv)"
        )
        if not path:
            return
        import csv
        with open(path, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(["File", "Status", "Rhythm", "Confidence", "Flagged",
                             "Duration(s)", "Error"])
            for item in self._items:
                writer.writerow([
                    item.filename, item.status, item.rhythm,
                    f"{item.confidence:.3f}", item.flagged,
                    f"{item.duration_s:.2f}", item.error,
                ])
