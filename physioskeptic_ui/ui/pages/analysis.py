"""
Analysis Page — PhysioSkeptic
Run PhysioSkeptic multi-agent analysis with full configuration panel.
"""
from __future__ import annotations

import time
from typing import Optional, TYPE_CHECKING

import numpy as np
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame, QPushButton,
    QComboBox, QLineEdit, QDoubleSpinBox, QSpinBox, QSlider,
    QGroupBox, QGridLayout, QProgressBar, QSplitter, QSizePolicy,
    QScrollArea,
)
from PySide6.QtCore import Qt, Signal, QThread, QObject
from PySide6.QtGui import QFont

from ..widgets.signal_plot import SignalPlotWidget
from ..widgets.result_card import ResultCard
from ..widgets.patch_report_widget import PatchReportWidget
from ..theme import ACCENT, SUCCESS, WARNING, DANGER, TEXT_SECONDARY

from core.pipeline import Pipeline, AnalysisConfig, AnalysisResult, ROUTING_MODES
from core.api_client import APIClientFactory
from core.signal_loader import SignalData, generate_demo_signal

if TYPE_CHECKING:
    from ...core.database import Database


# ── Worker thread ─────────────────────────────────────────────────────────────

class _AnalysisSignals(QObject):
    progress = Signal(int, str)
    finished = Signal(object)   # AnalysisResult or Exception


class _AnalysisWorker(QThread):
    def __init__(self, signal_data: SignalData, config: AnalysisConfig) -> None:
        super().__init__()
        self.signals = _AnalysisSignals()
        self._signal_data = signal_data
        self._config = config
        self._pipeline = Pipeline()
        self._running = True

    def run(self) -> None:
        try:
            result = self._pipeline.run_analysis(
                self._signal_data,
                self._config,
                progress_callback=self.signals.progress.emit,
            )
            self.signals.finished.emit(result)
        except Exception as e:
            self.signals.finished.emit(e)

    def cancel(self) -> None:
        self._running = False
        self._pipeline.cancel()


# ── Page ──────────────────────────────────────────────────────────────────────

class AnalysisPage(QWidget):
    """Full analysis configuration and execution page."""

    analysis_complete = Signal(object)   # AnalysisResult
    status_message = Signal(str, int)    # message, pct

    def __init__(self, db, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self._db = db
        self._current_signal: Optional[SignalData] = None
        self._is_demo: bool = False
        self._worker: Optional[_AnalysisWorker] = None
        self._result: Optional[AnalysisResult] = None
        self._t_start: float = 0.0
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
        title = QLabel("Analysis")
        f = title.font()
        f.setPointSize(14)
        f.setBold(True)
        title.setFont(f)
        hdr_lay.addWidget(title)
        hdr_lay.addStretch()

        self._session_label = QLabel("No signal loaded")
        self._session_label.setObjectName("SubLabel")
        hdr_lay.addWidget(self._session_label)
        root.addWidget(hdr)

        div = QFrame()
        div.setObjectName("Divider")
        div.setFixedHeight(1)
        root.addWidget(div)

        # Main splitter
        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.setHandleWidth(2)

        # ── LEFT: signal preview ───────────────────────────────────────────
        left = QWidget()
        left_lay = QVBoxLayout(left)
        left_lay.setContentsMargins(16, 12, 8, 12)
        left_lay.setSpacing(8)

        lhdr = QHBoxLayout()
        lhdr_lbl = QLabel("Signal Preview")
        lf = lhdr_lbl.font()
        lf.setBold(True)
        lhdr_lbl.setFont(lf)
        lhdr.addWidget(lhdr_lbl)
        lhdr.addStretch()

        # demo badge — visible when demo data is active
        self._demo_badge = QLabel("  DEMO  ")
        self._demo_badge.setStyleSheet(
            "background: rgba(26,107,219,0.22); color: #7ab4ff;"
            "border: 1px solid rgba(26,107,219,0.5); border-radius: 4px;"
            "font-size: 8pt; font-weight: 700; letter-spacing: 0.8px; padding: 2px 6px;"
        )
        self._demo_badge.setVisible(False)
        lhdr.addWidget(self._demo_badge)

        btn_demo = QPushButton("⬡ Load Demo Signal")
        btn_demo.setObjectName("FlatButton")
        btn_demo.setToolTip("Load synthetic 30-second ECG + PPG demo signal")
        btn_demo.clicked.connect(self._load_demo)
        lhdr.addWidget(btn_demo)
        left_lay.addLayout(lhdr)

        # no-data placeholder shown when nothing is loaded
        self._no_data_frame = QFrame()
        self._no_data_frame.setObjectName("Card")
        self._no_data_frame.setMinimumHeight(180)
        nd_lay = QVBoxLayout(self._no_data_frame)
        nd_lay.setAlignment(Qt.AlignCenter)
        nd_icon = QLabel("⬡")
        nd_icon.setAlignment(Qt.AlignCenter)
        nd_icon.setStyleSheet(f"font-size: 36pt; color: #2a3a52;")
        nd_title = QLabel("No Signal Loaded")
        nd_title.setAlignment(Qt.AlignCenter)
        nd_title.setStyleSheet("font-size: 13pt; font-weight: 600; color: #3a4d64;")
        nd_hint = QLabel(
            "Import a real ECG/PPG file from the Signal Import page,\n"
            "or click  ⬡ Load Demo Signal  to run with synthetic data."
        )
        nd_hint.setAlignment(Qt.AlignCenter)
        nd_hint.setStyleSheet(f"color: #3d5269; font-size: 9pt;")
        nd_btn = QPushButton("⬡  Load Demo Signal Now")
        nd_btn.setProperty("primary", "true")
        nd_btn.setMaximumWidth(230)
        nd_btn.clicked.connect(self._load_demo)
        nd_lay.addStretch()
        nd_lay.addWidget(nd_icon)
        nd_lay.addWidget(nd_title)
        nd_lay.addSpacing(6)
        nd_lay.addWidget(nd_hint)
        nd_lay.addSpacing(12)
        nd_lay.addWidget(nd_btn, alignment=Qt.AlignCenter)
        nd_lay.addStretch()
        left_lay.addWidget(self._no_data_frame)

        self._plot = SignalPlotWidget()
        self._plot.setVisible(False)
        left_lay.addWidget(self._plot)

        self._patch_report = PatchReportWidget()
        left_lay.addWidget(self._patch_report)

        splitter.addWidget(left)

        # ── RIGHT: config panel ────────────────────────────────────────────
        right_scroll = QScrollArea()
        right_scroll.setWidgetResizable(True)
        right_scroll.setMinimumWidth(340)
        right_scroll.setMaximumWidth(440)
        right_container = QWidget()
        right_lay = QVBoxLayout(right_container)
        right_lay.setContentsMargins(8, 12, 16, 12)
        right_lay.setSpacing(14)
        right_scroll.setWidget(right_container)

        # Model config group
        model_group = QGroupBox("Model Configuration")
        model_lay = QGridLayout(model_group)
        model_lay.setSpacing(8)

        self._model_combo = QComboBox()
        self._model_combo.addItems(APIClientFactory.list_display_names())
        self._model_combo.setCurrentText("Mock / Demo")

        self._api_key_edit = QLineEdit()
        self._api_key_edit.setPlaceholderText("sk-... (leave blank for Mock)")
        self._api_key_edit.setEchoMode(QLineEdit.EchoMode.Password)

        self._test_btn = QPushButton("Test Connection")
        self._test_btn.clicked.connect(self._test_connection)

        model_lay.addWidget(QLabel("Model:"), 0, 0)
        model_lay.addWidget(self._model_combo, 0, 1)
        model_lay.addWidget(QLabel("API Key:"), 1, 0)
        model_lay.addWidget(self._api_key_edit, 1, 1)
        model_lay.addWidget(self._test_btn, 2, 1)
        right_lay.addWidget(model_group)

        # Routing group
        routing_group = QGroupBox("Routing & Parameters")
        routing_lay = QGridLayout(routing_group)
        routing_lay.setSpacing(8)

        self._routing_combo = QComboBox()
        self._routing_combo.addItems(ROUTING_MODES)

        self._temp_slider = QSlider(Qt.Orientation.Horizontal)
        self._temp_slider.setRange(0, 100)
        self._temp_slider.setValue(70)
        self._temp_label = QLabel("0.70")
        self._temp_slider.valueChanged.connect(
            lambda v: self._temp_label.setText(f"{v/100:.2f}")
        )

        self._max_tokens_spin = QSpinBox()
        self._max_tokens_spin.setRange(256, 8192)
        self._max_tokens_spin.setValue(2048)
        self._max_tokens_spin.setSingleStep(256)

        self._sqi_slider = QSlider(Qt.Orientation.Horizontal)
        self._sqi_slider.setRange(0, 100)
        self._sqi_slider.setValue(50)
        self._sqi_label = QLabel("0.50")
        self._sqi_slider.valueChanged.connect(
            lambda v: self._sqi_label.setText(f"{v/100:.2f}")
        )

        self._tau_slider = QSlider(Qt.Orientation.Horizontal)
        self._tau_slider.setRange(0, 100)
        self._tau_slider.setValue(70)
        self._tau_label = QLabel("0.70")
        self._tau_slider.valueChanged.connect(
            lambda v: self._tau_label.setText(f"{v/100:.2f}")
        )

        routing_lay.addWidget(QLabel("Routing:"), 0, 0)
        routing_lay.addWidget(self._routing_combo, 0, 1, 1, 2)
        routing_lay.addWidget(QLabel("Temperature:"), 1, 0)
        routing_lay.addWidget(self._temp_slider, 1, 1)
        routing_lay.addWidget(self._temp_label, 1, 2)
        routing_lay.addWidget(QLabel("Max Tokens:"), 2, 0)
        routing_lay.addWidget(self._max_tokens_spin, 2, 1, 1, 2)
        routing_lay.addWidget(QLabel("SQI Threshold:"), 3, 0)
        routing_lay.addWidget(self._sqi_slider, 3, 1)
        routing_lay.addWidget(self._sqi_label, 3, 2)
        routing_lay.addWidget(QLabel("τ_rev:"), 4, 0)
        routing_lay.addWidget(self._tau_slider, 4, 1)
        routing_lay.addWidget(self._tau_label, 4, 2)
        right_lay.addWidget(routing_group)

        # Run button
        self._run_btn = QPushButton("▶  Run Analysis")
        self._run_btn.setObjectName("RunButton")
        self._run_btn.clicked.connect(self._toggle_run)
        right_lay.addWidget(self._run_btn)

        # Progress section
        prog_group = QGroupBox("Pipeline Progress")
        prog_lay = QVBoxLayout(prog_group)
        prog_lay.setSpacing(4)

        self._progress_bar = QProgressBar()
        self._progress_bar.setRange(0, 100)
        self._progress_bar.setValue(0)
        self._progress_bar.setTextVisible(False)
        self._progress_bar.setFixedHeight(10)
        prog_lay.addWidget(self._progress_bar)

        self._stage_labels: list = []
        stages = ["Encoding", "Proposer", "Checker", "Skeptic", "Advocate", "Arbiter"]
        for stage in stages:
            row = QHBoxLayout()
            dot = QLabel("○")
            dot.setFixedWidth(20)
            dot.setStyleSheet(f"color: {TEXT_SECONDARY};")
            lbl = QLabel(stage)
            lbl.setObjectName("SubLabel")
            row.addWidget(dot)
            row.addWidget(lbl)
            row.addStretch()
            self._stage_labels.append((dot, lbl))
            prog_lay.addLayout(row)

        right_lay.addWidget(prog_group)

        # Result panel
        result_group = QGroupBox("Result")
        result_lay = QVBoxLayout(result_group)
        self._result_card = ResultCard()
        result_lay.addWidget(self._result_card)
        right_lay.addWidget(result_group)

        right_lay.addStretch()
        splitter.addWidget(right_scroll)

        splitter.setSizes([700, 380])
        root.addWidget(splitter)

        # Bottom status
        self._status_lbl = QLabel("Load a signal and click Run Analysis.")
        self._status_lbl.setObjectName("SubLabel")
        self._status_lbl.setContentsMargins(16, 4, 16, 6)
        root.addWidget(self._status_lbl)

    # ── public API ────────────────────────────────────────────────────────────

    def load_signal(self, signal: SignalData, is_demo: bool = False) -> None:
        self._current_signal = signal
        self._is_demo = is_demo

        # toggle placeholder vs plot
        self._no_data_frame.setVisible(False)
        self._plot.setVisible(True)
        self._demo_badge.setVisible(is_demo)

        self._plot.load_signal(
            signal.channels, signal.channel_names, signal.fs, signal.duration_sec
        )
        src = signal.source_file
        label = f"Demo signal  |  {signal.duration_sec:.1f} s  |  {len(signal.channel_names)} ch" \
            if is_demo else \
            f"{src}  |  {signal.duration_sec:.1f} s  |  {len(signal.channel_names)} ch"
        self._session_label.setText(label)
        self._status_lbl.setText("Signal loaded. Configure options and click Run Analysis.")
        self._run_btn.setEnabled(True)

    # ── private ───────────────────────────────────────────────────────────────

    def _load_demo(self) -> None:
        self.load_signal(generate_demo_signal(), is_demo=True)

    def _toggle_run(self) -> None:
        if self._worker and self._worker.isRunning():
            self._cancel_analysis()
        else:
            self._start_analysis()

    def _start_analysis(self) -> None:
        if self._current_signal is None:
            self._status_lbl.setText("No signal loaded. Use 'Load Demo' or import a file.")
            return

        config = AnalysisConfig(
            model_name=self._model_combo.currentText(),
            api_key=self._api_key_edit.text().strip(),
            routing=self._routing_combo.currentText(),
            temperature=self._temp_slider.value() / 100.0,
            max_tokens=self._max_tokens_spin.value(),
            sqi_threshold=self._sqi_slider.value() / 100.0,
            review_flag_threshold=self._tau_slider.value() / 100.0,
        )

        self._reset_stages()
        self._result_card.clear()
        self._progress_bar.setValue(0)
        self._run_btn.setText("■  Cancel")
        self._run_btn.setStyleSheet(f"background-color: {DANGER}; color: white; border: none; "
                                     "border-radius: 8px; font-size: 13pt; font-weight: 700; "
                                     "padding: 12px 32px; min-height: 48px;")
        self._t_start = time.time()

        self._worker = _AnalysisWorker(self._current_signal, config)
        self._worker.signals.progress.connect(self._on_progress)
        self._worker.signals.finished.connect(self._on_finished)
        self._worker.start()

    def _cancel_analysis(self) -> None:
        if self._worker:
            self._worker.cancel()
        self._run_btn.setText("▶  Run Analysis")
        self._run_btn.setStyleSheet("")
        self._status_lbl.setText("Analysis cancelled.")

    def _reset_stages(self) -> None:
        for dot, lbl in self._stage_labels:
            dot.setText("○")
            dot.setStyleSheet(f"color: {TEXT_SECONDARY};")
            lbl.setStyleSheet(f"color: {TEXT_SECONDARY};")

    def _on_progress(self, pct: int, message: str) -> None:
        self._progress_bar.setValue(pct)
        elapsed = time.time() - self._t_start
        self._status_lbl.setText(f"{message}  ({elapsed:.1f}s)")
        self.status_message.emit(message, pct)

        # Light up stages
        stage_idx = pct // (100 // len(self._stage_labels))
        stage_idx = min(stage_idx, len(self._stage_labels) - 1)
        for i, (dot, lbl) in enumerate(self._stage_labels):
            if i < stage_idx:
                dot.setText("✓")
                dot.setStyleSheet(f"color: {SUCCESS};")
                lbl.setStyleSheet(f"color: {SUCCESS};")
            elif i == stage_idx:
                dot.setText("●")
                dot.setStyleSheet(f"color: {ACCENT};")
                lbl.setStyleSheet(f"color: {ACCENT};")

    def _on_finished(self, result) -> None:
        self._run_btn.setText("▶  Run Analysis")
        self._run_btn.setStyleSheet("")
        self._progress_bar.setValue(100)

        # Mark all stages done
        for dot, lbl in self._stage_labels:
            dot.setText("✓")
            dot.setStyleSheet(f"color: {SUCCESS};")
            lbl.setStyleSheet(f"color: {SUCCESS};")

        if isinstance(result, Exception):
            self._status_lbl.setText(f"Error: {result}")
            return

        if result.error:
            self._status_lbl.setText(f"Error: {result.error}")
            return

        self._result = result

        # Update result card
        self._result_card.update_result(
            result.rhythm, result.confidence, result.review_flag,
            result.ece, result.macro_f1, result.model_name,
        )

        # Update patch report
        if result.patch_report:
            self._patch_report.update_report(result.patch_report)

        elapsed = time.time() - self._t_start
        flag_str = " | ⚠ REVIEW FLAG" if result.review_flag else ""
        self._status_lbl.setText(
            f"Complete: {result.rhythm}  ({result.confidence*100:.0f}% conf)  "
            f"ECE={result.ece:.3f}  F1={result.macro_f1:.3f}  "
            f"[{elapsed:.1f}s]{flag_str}"
        )

        # Save to DB
        self._save_result(result)

        self.analysis_complete.emit(result)

    def _save_result(self, result: AnalysisResult) -> None:
        sig = self._current_signal
        import json

        def _turn_to_dict(t):
            return {"role": t.role, "content": t.content,
                    "input_tokens": t.input_tokens, "output_tokens": t.output_tokens}

        self._db.save_result({
            "signal_file": sig.source_file if sig else "",
            "signal_format": sig.source_format if sig else "",
            "patient_id": sig.patient_id if sig else "",
            "duration_sec": sig.duration_sec if sig else 0,
            "fs": sig.fs if sig else 125,
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
            "debate_transcript": [_turn_to_dict(t) for t in result.debate_transcript],
        })

    def _test_connection(self) -> None:
        model = self._model_combo.currentText()
        key = self._api_key_edit.text().strip()
        self._test_btn.setText("Testing...")
        self._test_btn.setEnabled(False)

        import threading
        from PySide6.QtCore import QTimer

        def _do_test():
            client = APIClientFactory.create(model, api_key=key)
            ok = client.test_connection()
            # Use single-shot timer to marshal back to GUI thread
            QTimer.singleShot(0, lambda: self._test_result(ok))

        threading.Thread(target=_do_test, daemon=True).start()

    def _test_result(self, ok: bool) -> None:
        self._test_btn.setEnabled(True)
        if ok:
            self._test_btn.setText("✓ Connected")
            self._test_btn.setStyleSheet(f"color: {SUCCESS};")
        else:
            self._test_btn.setText("✗ Failed")
            self._test_btn.setStyleSheet(f"color: {DANGER};")

    def get_last_result(self) -> Optional[AnalysisResult]:
        return self._result
