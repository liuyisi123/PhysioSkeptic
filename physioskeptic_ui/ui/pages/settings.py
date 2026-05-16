"""
Settings Page — PhysioSkeptic
Tabbed settings: API Keys, Model Defaults, Data Paths, Preprocessing, Appearance, About.
"""
from __future__ import annotations

import os
from typing import Optional

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame, QPushButton,
    QTabWidget, QLineEdit, QComboBox, QSpinBox, QDoubleSpinBox,
    QSlider, QCheckBox, QGroupBox, QGridLayout, QFileDialog,
    QScrollArea, QSizePolicy, QTextBrowser,
)
from PySide6.QtCore import Qt, Signal, QSettings
from PySide6.QtGui import QFont, QDesktopServices
from PySide6.QtCore import QUrl

from ..theme import ACCENT, SUCCESS, DANGER, TEXT_SECONDARY


ORG = "PhysioSkeptic"
APP = "PhysioSkeptic"


class SettingsPage(QWidget):
    """Full settings page with tabbed layout."""

    theme_changed = Signal(str)       # "dark" | "light" | "medical"
    font_size_changed = Signal(int)

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self._settings = QSettings(ORG, APP)
        self._build_ui()
        self._load_settings()

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
        title = QLabel("Settings")
        f = title.font()
        f.setPointSize(14)
        f.setBold(True)
        title.setFont(f)
        hdr_lay.addWidget(title)
        hdr_lay.addStretch()

        save_btn = QPushButton("Save Settings")
        save_btn.setProperty("primary", "true")
        save_btn.clicked.connect(self._save_settings)
        hdr_lay.addWidget(save_btn)

        reset_btn = QPushButton("Reset to Defaults")
        reset_btn.clicked.connect(self._reset_defaults)
        hdr_lay.addWidget(reset_btn)
        root.addWidget(hdr)

        div = QFrame()
        div.setObjectName("Divider")
        div.setFixedHeight(1)
        root.addWidget(div)

        # Tabs
        tabs = QTabWidget()
        tabs.addTab(self._build_api_tab(), "API Keys")
        tabs.addTab(self._build_model_tab(), "Model Defaults")
        tabs.addTab(self._build_paths_tab(), "Data Paths")
        tabs.addTab(self._build_preproc_tab(), "Preprocessing")
        tabs.addTab(self._build_appearance_tab(), "Appearance")
        tabs.addTab(self._build_about_tab(), "About")
        root.addWidget(tabs)

        # Status
        self._status_lbl = QLabel("")
        self._status_lbl.setObjectName("SubLabel")
        self._status_lbl.setContentsMargins(16, 4, 16, 6)
        root.addWidget(self._status_lbl)

    # ── API Keys tab ──────────────────────────────────────────────────────────

    def _build_api_tab(self) -> QWidget:
        w = QScrollArea()
        w.setWidgetResizable(True)
        container = QWidget()
        lay = QVBoxLayout(container)
        lay.setContentsMargins(24, 20, 24, 20)
        lay.setSpacing(16)

        def _key_group(title: str, fields: list) -> QGroupBox:
            g = QGroupBox(title)
            gl = QGridLayout(g)
            gl.setSpacing(8)
            widgets = {}
            for row, (name, placeholder, is_url) in enumerate(fields):
                lbl = QLabel(name + ":")
                le = QLineEdit()
                le.setPlaceholderText(placeholder)
                if not is_url:
                    le.setEchoMode(QLineEdit.EchoMode.Password)
                show_btn = QPushButton("Show")
                show_btn.setFixedWidth(50)
                show_btn.setObjectName("FlatButton")
                show_btn.setCheckable(True)

                def _toggle(checked, field=le):
                    field.setEchoMode(
                        QLineEdit.EchoMode.Normal if checked else QLineEdit.EchoMode.Password
                    )
                show_btn.toggled.connect(_toggle)

                gl.addWidget(lbl, row, 0)
                gl.addWidget(le, row, 1)
                if not is_url:
                    gl.addWidget(show_btn, row, 2)
                widgets[name] = le
            return g, widgets

        openai_g, openai_w = _key_group("OpenAI", [
            ("API Key", "sk-...", False),
            ("Organization", "org-...", True),
        ])
        self._openai_key = openai_w["API Key"]
        self._openai_org = openai_w["Organization"]

        anthropic_g, anthropic_w = _key_group("Anthropic", [
            ("API Key", "sk-ant-...", False),
        ])
        self._anthropic_key = anthropic_w["API Key"]

        deepseek_g, deepseek_w = _key_group("DeepSeek", [
            ("API Key", "deepseek-...", False),
        ])
        self._deepseek_key = deepseek_w["API Key"]

        qwen_g, qwen_w = _key_group("Qwen (DashScope)", [
            ("API Key", "sk-...", False),
        ])
        self._qwen_key = qwen_w["API Key"]

        ollama_g, ollama_w = _key_group("Ollama (Local)", [
            ("Base URL", "http://localhost:11434", True),
        ])
        self._ollama_url = ollama_w["Base URL"]

        azure_g, azure_w = _key_group("Azure OpenAI", [
            ("Endpoint", "https://your-resource.openai.azure.com/", True),
            ("API Key", "...", False),
            ("API Version", "2024-02-15-preview", True),
        ])
        self._azure_endpoint = azure_w["Endpoint"]
        self._azure_key = azure_w["API Key"]
        self._azure_version = azure_w["API Version"]

        for g in [openai_g, anthropic_g, deepseek_g, qwen_g, ollama_g, azure_g]:
            lay.addWidget(g)
        lay.addStretch()

        w.setWidget(container)
        return w

    # ── Model Defaults tab ────────────────────────────────────────────────────

    def _build_model_tab(self) -> QWidget:
        w = QWidget()
        lay = QVBoxLayout(w)
        lay.setContentsMargins(24, 20, 24, 20)
        lay.setSpacing(14)

        from core.api_client import APIClientFactory

        g = QGroupBox("Default Model Settings")
        gl = QGridLayout(g)
        gl.setSpacing(10)

        self._default_model = QComboBox()
        self._default_model.addItems(APIClientFactory.list_display_names())
        self._default_model.setCurrentText("Mock / Demo")

        self._default_routing = QComboBox()
        self._default_routing.addItems(["Auto", "Force Fast", "Force Standard", "Force Deep"])

        self._default_temp = QDoubleSpinBox()
        self._default_temp.setRange(0.0, 2.0)
        self._default_temp.setSingleStep(0.05)
        self._default_temp.setValue(0.70)
        self._default_temp.setDecimals(2)

        self._default_tau = QDoubleSpinBox()
        self._default_tau.setRange(0.0, 1.0)
        self._default_tau.setSingleStep(0.05)
        self._default_tau.setValue(0.70)
        self._default_tau.setDecimals(2)

        self._default_max_tokens = QSpinBox()
        self._default_max_tokens.setRange(256, 8192)
        self._default_max_tokens.setValue(2048)
        self._default_max_tokens.setSingleStep(256)

        for row, (lbl, widget) in enumerate([
            ("Default Model:", self._default_model),
            ("Default Routing:", self._default_routing),
            ("Default Temperature:", self._default_temp),
            ("Default τ_rev:", self._default_tau),
            ("Default Max Tokens:", self._default_max_tokens),
        ]):
            gl.addWidget(QLabel(lbl), row, 0)
            gl.addWidget(widget, row, 1)

        lay.addWidget(g)
        lay.addStretch()
        return w

    # ── Data Paths tab ────────────────────────────────────────────────────────

    def _build_paths_tab(self) -> QWidget:
        w = QWidget()
        lay = QVBoxLayout(w)
        lay.setContentsMargins(24, 20, 24, 20)
        lay.setSpacing(14)

        g = QGroupBox("Data Paths")
        gl = QGridLayout(g)
        gl.setSpacing(10)

        def _path_row(label: str, row: int, default: str) -> QLineEdit:
            le = QLineEdit(default)
            btn = QPushButton("Browse")
            btn.setFixedWidth(70)
            def _browse(checked=False, field=le):
                d = QFileDialog.getExistingDirectory(w, "Select Folder", field.text())
                if d:
                    field.setText(d)
            btn.clicked.connect(_browse)
            gl.addWidget(QLabel(label), row, 0)
            gl.addWidget(le, row, 1)
            gl.addWidget(btn, row, 2)
            return le

        home = os.path.expanduser("~")
        self._import_path = _path_row("Import Folder:", 0, os.path.join(home, "Documents"))
        self._export_path = _path_row("Export Folder:", 1, os.path.join(home, "Documents"))
        self._db_path = _path_row(
            "Database Path:", 2,
            os.path.join(home, ".physioskeptic", "history.db")
        )

        lay.addWidget(g)
        lay.addStretch()
        return w

    # ── Preprocessing tab ─────────────────────────────────────────────────────

    def _build_preproc_tab(self) -> QWidget:
        w = QWidget()
        lay = QVBoxLayout(w)
        lay.setContentsMargins(24, 20, 24, 20)
        lay.setSpacing(14)

        g = QGroupBox("Default Preprocessing")
        gl = QGridLayout(g)
        gl.setSpacing(10)

        self._pp_bp = QCheckBox("Apply bandpass filter by default")
        self._pp_bp.setChecked(True)
        self._pp_bp_lo = QDoubleSpinBox()
        self._pp_bp_lo.setRange(0.01, 10.0)
        self._pp_bp_lo.setValue(0.5)
        self._pp_bp_lo.setSuffix(" Hz")
        self._pp_bp_hi = QDoubleSpinBox()
        self._pp_bp_hi.setRange(5.0, 500.0)
        self._pp_bp_hi.setValue(40.0)
        self._pp_bp_hi.setSuffix(" Hz")

        self._pp_norm = QCheckBox("Normalize channels by default")
        self._pp_resample = QCheckBox("Resample to target Hz by default")
        self._pp_resample.setChecked(True)

        self._pp_target_fs = QSpinBox()
        self._pp_target_fs.setRange(50, 1000)
        self._pp_target_fs.setValue(125)
        self._pp_target_fs.setSuffix(" Hz")

        gl.addWidget(self._pp_bp, 0, 0, 1, 2)
        gl.addWidget(QLabel("Low cutoff:"), 1, 0)
        gl.addWidget(self._pp_bp_lo, 1, 1)
        gl.addWidget(QLabel("High cutoff:"), 2, 0)
        gl.addWidget(self._pp_bp_hi, 2, 1)
        gl.addWidget(self._pp_norm, 3, 0, 1, 2)
        gl.addWidget(self._pp_resample, 4, 0, 1, 2)
        gl.addWidget(QLabel("Target sample rate:"), 5, 0)
        gl.addWidget(self._pp_target_fs, 5, 1)

        lay.addWidget(g)
        lay.addStretch()
        return w

    # ── Appearance tab ────────────────────────────────────────────────────────

    def _build_appearance_tab(self) -> QWidget:
        w = QWidget()
        lay = QVBoxLayout(w)
        lay.setContentsMargins(24, 20, 24, 20)
        lay.setSpacing(14)

        g = QGroupBox("Appearance")
        gl = QGridLayout(g)
        gl.setSpacing(10)

        self._theme_combo = QComboBox()
        self._theme_combo.addItems(["Dark (Default)", "Light", "Medical Blue"])
        self._theme_combo.currentTextChanged.connect(self._on_theme_changed)

        self._font_size_spin = QSpinBox()
        self._font_size_spin.setRange(8, 18)
        self._font_size_spin.setValue(10)
        self._font_size_spin.setSuffix(" pt")
        self._font_size_spin.valueChanged.connect(self.font_size_changed.emit)

        self._sidebar_collapsed = QCheckBox("Sidebar collapsed by default")

        gl.addWidget(QLabel("Theme:"), 0, 0)
        gl.addWidget(self._theme_combo, 0, 1)
        gl.addWidget(QLabel("Font Size:"), 1, 0)
        gl.addWidget(self._font_size_spin, 1, 1)
        gl.addWidget(self._sidebar_collapsed, 2, 0, 1, 2)

        lay.addWidget(g)
        lay.addStretch()
        return w

    # ── About tab ─────────────────────────────────────────────────────────────

    def _build_about_tab(self) -> QWidget:
        w = QWidget()
        lay = QVBoxLayout(w)
        lay.setContentsMargins(24, 20, 24, 20)
        lay.setSpacing(14)

        logo_lbl = QLabel("PhysioSkeptic")
        lf = logo_lbl.font()
        lf.setPointSize(22)
        lf.setBold(True)
        logo_lbl.setFont(lf)
        logo_lbl.setStyleSheet(f"color: {ACCENT};")
        lay.addWidget(logo_lbl)

        version_lbl = QLabel("Version 1.0.0  ·  2026")
        version_lbl.setObjectName("SubLabel")
        lay.addWidget(version_lbl)

        desc = QTextBrowser()
        desc.setReadOnly(True)
        desc.setHtml("""
        <p><b>PhysioSkeptic</b> is a multi-agent debate framework for robust cardiac
        rhythm classification from physiological signals (ECG, PPG, EEG, Respiration, ABP).</p>
        <p>The pipeline employs five specialized AI agents — Proposer, Checker, Skeptic,
        Advocate, and Arbiter — to reduce overconfidence and improve calibration in
        automated arrhythmia detection.</p>
        <h4>Citation</h4>
        <p>If you use PhysioSkeptic in your research, please cite:<br/>
        <code>[Anonymous, "PhysioSkeptic: Signal-Quality-Anchored Skeptical Reasoning
        for Robust ECG–PPG Rhythm Diagnosis", AAAI 2027]</code></p>
        <h4>License</h4>
        <p>MIT License — see GitHub repository for details.</p>
        """)
        desc.setMaximumHeight(280)
        desc.setStyleSheet(f"background-color: #1f2937; border: 1px solid #30363d; "
                           "border-radius: 6px; color: #f0f6fc; font-size: 10pt;")
        lay.addWidget(desc)

        links_row = QHBoxLayout()
        btn_gh = QPushButton("GitHub Repository")
        btn_gh.clicked.connect(
            lambda: QDesktopServices.openUrl(QUrl("https://github.com/physioskeptic"))
        )
        btn_paper = QPushButton("Paper (NeurIPS 2026)")
        btn_paper.clicked.connect(
            lambda: QDesktopServices.openUrl(QUrl("https://arxiv.org/abs/2026.00000"))
        )
        links_row.addWidget(btn_gh)
        links_row.addWidget(btn_paper)
        links_row.addStretch()
        lay.addLayout(links_row)
        lay.addStretch()

        return w

    # ── persistence ───────────────────────────────────────────────────────────

    def _save_settings(self) -> None:
        s = self._settings

        # API keys
        s.setValue("api/openai_key", self._openai_key.text())
        s.setValue("api/openai_org", self._openai_org.text())
        s.setValue("api/anthropic_key", self._anthropic_key.text())
        s.setValue("api/deepseek_key", self._deepseek_key.text())
        s.setValue("api/qwen_key", self._qwen_key.text())
        s.setValue("api/ollama_url", self._ollama_url.text())
        s.setValue("api/azure_endpoint", self._azure_endpoint.text())
        s.setValue("api/azure_key", self._azure_key.text())
        s.setValue("api/azure_version", self._azure_version.text())

        # Model defaults
        s.setValue("model/default", self._default_model.currentText())
        s.setValue("model/routing", self._default_routing.currentText())
        s.setValue("model/temperature", self._default_temp.value())
        s.setValue("model/tau_rev", self._default_tau.value())
        s.setValue("model/max_tokens", self._default_max_tokens.value())

        # Paths
        s.setValue("paths/import", self._import_path.text())
        s.setValue("paths/export", self._export_path.text())
        s.setValue("paths/database", self._db_path.text())

        # Preprocessing
        s.setValue("preproc/bandpass", self._pp_bp.isChecked())
        s.setValue("preproc/bp_lo", self._pp_bp_lo.value())
        s.setValue("preproc/bp_hi", self._pp_bp_hi.value())
        s.setValue("preproc/normalize", self._pp_norm.isChecked())
        s.setValue("preproc/resample", self._pp_resample.isChecked())
        s.setValue("preproc/target_fs", self._pp_target_fs.value())

        # Appearance
        s.setValue("appearance/theme", self._theme_combo.currentText())
        s.setValue("appearance/font_size", self._font_size_spin.value())
        s.setValue("appearance/sidebar_collapsed", self._sidebar_collapsed.isChecked())

        s.sync()
        self._status_lbl.setText("Settings saved.")
        self._status_lbl.setStyleSheet(f"color: {SUCCESS};")

    def _load_settings(self) -> None:
        s = self._settings

        self._openai_key.setText(s.value("api/openai_key", ""))
        self._openai_org.setText(s.value("api/openai_org", ""))
        self._anthropic_key.setText(s.value("api/anthropic_key", ""))
        self._deepseek_key.setText(s.value("api/deepseek_key", ""))
        self._qwen_key.setText(s.value("api/qwen_key", ""))
        self._ollama_url.setText(s.value("api/ollama_url", "http://localhost:11434"))
        self._azure_endpoint.setText(s.value("api/azure_endpoint", ""))
        self._azure_key.setText(s.value("api/azure_key", ""))
        self._azure_version.setText(s.value("api/azure_version", "2024-02-15-preview"))

        self._default_model.setCurrentText(s.value("model/default", "Mock / Demo"))
        self._default_routing.setCurrentText(s.value("model/routing", "Auto"))
        self._default_temp.setValue(float(s.value("model/temperature", 0.70)))
        self._default_tau.setValue(float(s.value("model/tau_rev", 0.70)))
        self._default_max_tokens.setValue(int(s.value("model/max_tokens", 2048)))

        home = os.path.expanduser("~")
        self._import_path.setText(s.value("paths/import", os.path.join(home, "Documents")))
        self._export_path.setText(s.value("paths/export", os.path.join(home, "Documents")))
        self._db_path.setText(s.value("paths/database",
                                       os.path.join(home, ".physioskeptic", "history.db")))

        self._pp_bp.setChecked(s.value("preproc/bandpass", True, type=bool))
        self._pp_bp_lo.setValue(float(s.value("preproc/bp_lo", 0.5)))
        self._pp_bp_hi.setValue(float(s.value("preproc/bp_hi", 40.0)))
        self._pp_norm.setChecked(s.value("preproc/normalize", False, type=bool))
        self._pp_resample.setChecked(s.value("preproc/resample", True, type=bool))
        self._pp_target_fs.setValue(int(s.value("preproc/target_fs", 125)))

        self._theme_combo.setCurrentText(s.value("appearance/theme", "Dark (Default)"))
        self._font_size_spin.setValue(int(s.value("appearance/font_size", 10)))
        self._sidebar_collapsed.setChecked(s.value("appearance/sidebar_collapsed", False, type=bool))

    def _reset_defaults(self) -> None:
        self._settings.clear()
        self._load_settings()
        self._status_lbl.setText("Settings reset to defaults.")

    def _on_theme_changed(self, text: str) -> None:
        mapping = {
            "Dark (Default)": "dark",
            "Light": "light",
            "Medical Blue": "medical",
        }
        self.theme_changed.emit(mapping.get(text, "dark"))

    def get_api_key(self, provider: str) -> str:
        """Retrieve a stored API key."""
        mapping = {
            "openai": self._openai_key.text(),
            "anthropic": self._anthropic_key.text(),
            "deepseek": self._deepseek_key.text(),
            "qwen": self._qwen_key.text(),
            "azure": self._azure_key.text(),
        }
        return mapping.get(provider.lower(), "")
