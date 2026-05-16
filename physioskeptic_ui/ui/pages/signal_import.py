"""
Signal Import Page — PhysioSkeptic
Drag-and-drop file import, channel assignment, preview, preprocessing options.
"""
from __future__ import annotations

import os
from typing import Optional, List

import numpy as np
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame, QPushButton,
    QFileDialog, QTableWidget, QTableWidgetItem, QHeaderView,
    QComboBox, QDoubleSpinBox, QSpinBox, QLineEdit, QGroupBox,
    QCheckBox, QGridLayout, QSplitter, QSizePolicy, QScrollArea,
)
from PySide6.QtCore import Qt, Signal, QThread, QObject, QRunnable, QThreadPool
from PySide6.QtGui import QFont, QDragEnterEvent, QDropEvent

from ..widgets.signal_plot import SignalPlotWidget
from ..theme import ACCENT, SUCCESS, WARNING, DANGER

from core.signal_loader import SignalLoader, SignalData, generate_demo_signal


class _LoadWorkerSignals(QObject):
    finished = Signal(object)   # SignalData or Exception
    progress = Signal(str)


class _LoadWorker(QRunnable):
    def __init__(self, path: str, fs_override: Optional[float]) -> None:
        super().__init__()
        self.signals = _LoadWorkerSignals()
        self._path = path
        self._fs = fs_override

    def run(self) -> None:
        try:
            loader = SignalLoader()
            data = loader.load(self._path, self._fs)
            self.signals.finished.emit(data)
        except Exception as e:
            self.signals.finished.emit(e)


class DropZone(QFrame):
    """Drag-and-drop file zone."""
    files_dropped = Signal(list)

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setObjectName("DropZone")
        self.setAcceptDrops(True)
        self.setMinimumHeight(140)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

        lay = QVBoxLayout(self)
        lay.setAlignment(Qt.AlignmentFlag.AlignCenter)

        icon = QLabel("⬆")
        icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        font = icon.font()
        font.setPointSize(28)
        icon.setFont(font)
        icon.setStyleSheet("color: #2563eb;")

        msg = QLabel("Drop signal files here or click to browse")
        msg.setAlignment(Qt.AlignmentFlag.AlignCenter)
        msg.setObjectName("SubLabel")

        sub = QLabel("EDF · CSV · NPZ · WFDB (.hea) · JSON · HDF5")
        sub.setAlignment(Qt.AlignmentFlag.AlignCenter)
        sub.setObjectName("SubLabel")

        lay.addWidget(icon)
        lay.addWidget(msg)
        lay.addWidget(sub)
        self.setCursor(Qt.CursorShape.PointingHandCursor)

    def dragEnterEvent(self, event: QDragEnterEvent) -> None:
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
            self.setStyleSheet(
                "QFrame#DropZone { background-color: rgba(37,99,235,0.2); "
                "border: 2px dashed #2563eb; border-radius: 12px; }"
            )

    def dragLeaveEvent(self, event) -> None:
        self.setStyleSheet("")

    def dropEvent(self, event: QDropEvent) -> None:
        self.setStyleSheet("")
        paths = [u.toLocalFile() for u in event.mimeData().urls()]
        if paths:
            self.files_dropped.emit(paths)

    def mousePressEvent(self, event) -> None:
        paths, _ = QFileDialog.getOpenFileNames(
            self, "Open Signal File", "",
            "Signal Files (*.edf *.csv *.txt *.npz *.npy *.json *.hea *.h5 *.hdf5);;"
            "All Files (*.*)"
        )
        if paths:
            self.files_dropped.emit(paths)


class SignalImportPage(QWidget):
    """Full signal import page with preview and metadata."""

    signal_loaded = Signal(object)   # SignalData

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self._current_signal: Optional[SignalData] = None
        self._pool = QThreadPool.globalInstance()
        self._build_ui()

    # ── build ─────────────────────────────────────────────────────────────────

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # Page header
        hdr_frame = QFrame()
        hdr_frame.setFixedHeight(56)
        hdr_lay = QHBoxLayout(hdr_frame)
        hdr_lay.setContentsMargins(24, 0, 24, 0)
        title = QLabel("Signal Import")
        f = title.font()
        f.setPointSize(14)
        f.setBold(True)
        title.setFont(f)
        hdr_lay.addWidget(title)
        hdr_lay.addStretch()

        btn_demo = QPushButton("Load Demo Signal")
        btn_demo.clicked.connect(self._load_demo)
        hdr_lay.addWidget(btn_demo)

        btn_load = QPushButton("+ Open File")
        btn_load.setProperty("primary", "true")
        btn_load.clicked.connect(self._browse_file)
        hdr_lay.addWidget(btn_load)
        root.addWidget(hdr_frame)

        # Divider
        div = QFrame()
        div.setObjectName("Divider")
        div.setFixedHeight(1)
        root.addWidget(div)

        # Main splitter: left = controls, right = preview
        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.setHandleWidth(2)

        # ── LEFT panel ──────────────────────────────────────────────────────
        left = QScrollArea()
        left.setWidgetResizable(True)
        left.setMinimumWidth(320)
        left.setMaximumWidth(420)
        left_container = QWidget()
        left_lay = QVBoxLayout(left_container)
        left_lay.setContentsMargins(16, 16, 16, 16)
        left_lay.setSpacing(14)
        left.setWidget(left_container)

        # Drop zone
        self._drop_zone = DropZone()
        self._drop_zone.files_dropped.connect(self._on_files_dropped)
        left_lay.addWidget(self._drop_zone)

        # File info
        self._file_info = QLabel("No file loaded")
        self._file_info.setObjectName("SubLabel")
        self._file_info.setWordWrap(True)
        left_lay.addWidget(self._file_info)

        # Sampling rate
        fs_group = QGroupBox("Sampling Rate")
        fs_lay = QGridLayout(fs_group)
        self._fs_auto_check = QCheckBox("Auto-detect")
        self._fs_auto_check.setChecked(True)
        self._fs_spin = QDoubleSpinBox()
        self._fs_spin.setRange(1, 10000)
        self._fs_spin.setValue(125)
        self._fs_spin.setSuffix(" Hz")
        self._fs_spin.setEnabled(False)
        self._fs_auto_check.toggled.connect(lambda c: self._fs_spin.setEnabled(not c))
        fs_lay.addWidget(self._fs_auto_check, 0, 0, 1, 2)
        fs_lay.addWidget(QLabel("Override:"), 1, 0)
        fs_lay.addWidget(self._fs_spin, 1, 1)
        left_lay.addWidget(fs_group)

        # Channel assignment
        ch_group = QGroupBox("Channel Assignment")
        ch_lay = QVBoxLayout(ch_group)
        self._channel_table = QTableWidget(0, 3)
        self._channel_table.setHorizontalHeaderLabels(["Channel", "Modality", "Include"])
        self._channel_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self._channel_table.verticalHeader().setVisible(False)
        self._channel_table.setMaximumHeight(180)
        ch_lay.addWidget(self._channel_table)
        left_lay.addWidget(ch_group)

        # Patient metadata
        meta_group = QGroupBox("Patient Metadata")
        meta_lay = QGridLayout(meta_group)
        self._pid_edit = QLineEdit()
        self._pid_edit.setPlaceholderText("PT-001")
        self._age_spin = QSpinBox()
        self._age_spin.setRange(0, 120)
        self._age_spin.setValue(0)
        self._sex_combo = QComboBox()
        self._sex_combo.addItems(["", "M", "F", "Other"])
        self._notes_edit = QLineEdit()
        self._notes_edit.setPlaceholderText("Optional notes...")
        meta_lay.addWidget(QLabel("Patient ID:"), 0, 0)
        meta_lay.addWidget(self._pid_edit, 0, 1)
        meta_lay.addWidget(QLabel("Age:"), 1, 0)
        meta_lay.addWidget(self._age_spin, 1, 1)
        meta_lay.addWidget(QLabel("Sex:"), 2, 0)
        meta_lay.addWidget(self._sex_combo, 2, 1)
        meta_lay.addWidget(QLabel("Notes:"), 3, 0)
        meta_lay.addWidget(self._notes_edit, 3, 1)
        left_lay.addWidget(meta_group)

        # Preprocessing
        pp_group = QGroupBox("Preprocessing")
        pp_lay = QVBoxLayout(pp_group)
        self._bp_check = QCheckBox("Bandpass filter (0.5–40 Hz for ECG)")
        self._bp_check.setChecked(True)
        self._norm_check = QCheckBox("Normalize channels (Z-score)")
        self._resample_check = QCheckBox("Resample to 125 Hz")
        self._resample_check.setChecked(True)
        for w in [self._bp_check, self._norm_check, self._resample_check]:
            pp_lay.addWidget(w)
        left_lay.addWidget(pp_group)

        # Load / Send to analysis
        btn_row = QHBoxLayout()
        self._btn_to_analysis = QPushButton("→ Send to Analysis")
        self._btn_to_analysis.setProperty("primary", "true")
        self._btn_to_analysis.setEnabled(False)
        self._btn_to_analysis.clicked.connect(self._send_to_analysis)
        btn_row.addWidget(self._btn_to_analysis)
        left_lay.addLayout(btn_row)

        left_lay.addStretch()
        splitter.addWidget(left)

        # ── RIGHT panel — signal preview ────────────────────────────────────
        right = QWidget()
        right_lay = QVBoxLayout(right)
        right_lay.setContentsMargins(8, 8, 16, 8)
        right_lay.setSpacing(8)

        preview_hdr = QLabel("Signal Preview")
        f3 = preview_hdr.font()
        f3.setBold(True)
        preview_hdr.setFont(f3)
        right_lay.addWidget(preview_hdr)

        self._plot = SignalPlotWidget()
        right_lay.addWidget(self._plot)
        splitter.addWidget(right)

        splitter.setSizes([360, 900])
        root.addWidget(splitter)

        # Status
        self._status = QLabel("Ready — drop a signal file to begin.")
        self._status.setObjectName("SubLabel")
        self._status.setContentsMargins(16, 4, 16, 6)
        root.addWidget(self._status)

    # ── event handlers ────────────────────────────────────────────────────────

    def _browse_file(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self, "Open Signal File", "",
            "Signal Files (*.edf *.csv *.txt *.npz *.npy *.json *.hea *.h5 *.hdf5);;"
            "All Files (*.*)"
        )
        if path:
            self._load_file(path)

    def _on_files_dropped(self, paths: List[str]) -> None:
        if paths:
            self._load_file(paths[0])

    def _load_file(self, path: str) -> None:
        self._status.setText(f"Loading {os.path.basename(path)}...")
        self._btn_to_analysis.setEnabled(False)

        fs_override = None
        if not self._fs_auto_check.isChecked():
            fs_override = self._fs_spin.value()

        worker = _LoadWorker(path, fs_override)
        worker.signals.finished.connect(self._on_load_finished)
        self._pool.start(worker)

    def _on_load_finished(self, result) -> None:
        if isinstance(result, Exception):
            self._status.setText(f"Error: {result}")
            return
        self._apply_preprocessing(result)
        self._display_signal(result)

    def _apply_preprocessing(self, data: SignalData) -> None:
        """Apply selected preprocessing to signal in-place."""
        try:
            if self._bp_check.isChecked() and data.ecg is not None:
                from scipy.signal import butter, filtfilt
                b, a = butter(4, [0.5, 40.0], btype="band", fs=data.fs)
                data.ecg = filtfilt(b, a, data.ecg).astype(np.float32)
                for i, name in enumerate(data.channel_names):
                    if "ecg" in name.lower() or "ekg" in name.lower():
                        data.channels[i] = filtfilt(b, a, data.channels[i]).astype(np.float32)
        except Exception:
            pass

        if self._norm_check.isChecked():
            for i in range(data.channels.shape[0]):
                ch = data.channels[i]
                std = np.std(ch)
                if std > 1e-9:
                    data.channels[i] = ((ch - np.mean(ch)) / std).astype(np.float32)

    def _display_signal(self, data: SignalData) -> None:
        self._current_signal = data

        # Update plot
        self._plot.load_signal(
            data.channels, data.channel_names, data.fs, data.duration_sec
        )

        # Update channel table
        self._channel_table.setRowCount(0)
        MODALITIES = ["ECG", "PPG", "Respiration", "ABP", "SpO2", "EEG", "Other"]
        for i, name in enumerate(data.channel_names):
            r = self._channel_table.rowCount()
            self._channel_table.insertRow(r)
            self._channel_table.setItem(r, 0, QTableWidgetItem(name))

            combo = QComboBox()
            combo.addItems(MODALITIES)
            # smart default
            nl = name.lower()
            if "ecg" in nl or "ekg" in nl:
                combo.setCurrentText("ECG")
            elif "ppg" in nl or "pleth" in nl:
                combo.setCurrentText("PPG")
            elif "resp" in nl or "rsp" in nl:
                combo.setCurrentText("Respiration")
            elif "abp" in nl or "bp" in nl:
                combo.setCurrentText("ABP")
            elif "spo2" in nl:
                combo.setCurrentText("SpO2")
            else:
                combo.setCurrentText("Other")
            self._channel_table.setCellWidget(r, 1, combo)

            chk = QCheckBox()
            chk.setChecked(True)
            chk.setStyleSheet("margin-left: 8px;")
            self._channel_table.setCellWidget(r, 2, chk)

        # Populate metadata
        self._pid_edit.setText(data.patient_id)
        if data.age:
            self._age_spin.setValue(data.age)
        if data.sex:
            idx = self._sex_combo.findText(data.sex)
            if idx >= 0:
                self._sex_combo.setCurrentIndex(idx)
        self._notes_edit.setText(data.notes)

        # File info
        self._file_info.setText(
            f"File: {data.source_file}  [{data.source_format}]\n"
            f"Channels: {len(data.channel_names)}  |  "
            f"Duration: {data.duration_sec:.1f} s  |  Fs: {data.fs:.0f} Hz  |  "
            f"Samples: {data.n_samples:,}"
        )

        self._status.setText(f"Loaded: {data.source_file}")
        self._btn_to_analysis.setEnabled(True)

    def _load_demo(self) -> None:
        data = generate_demo_signal(30.0, 125.0)
        self._display_signal(data)

    def _send_to_analysis(self) -> None:
        if self._current_signal is None:
            return
        # Update metadata from UI
        self._current_signal.patient_id = self._pid_edit.text()
        self._current_signal.age = self._age_spin.value() or None
        self._current_signal.sex = self._sex_combo.currentText()
        self._current_signal.notes = self._notes_edit.text()
        self.signal_loaded.emit(self._current_signal)

    def get_current_signal(self) -> Optional[SignalData]:
        return self._current_signal
