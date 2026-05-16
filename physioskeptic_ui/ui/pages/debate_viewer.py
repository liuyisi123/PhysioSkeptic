"""
Debate Viewer Page — PhysioSkeptic
Chat-like transcript with colored role bubbles, mini signal view, export.
"""
from __future__ import annotations

import json
import os
from typing import Optional, List, TYPE_CHECKING

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame, QPushButton,
    QScrollArea, QTextEdit, QSplitter, QFileDialog, QSizePolicy,
    QApplication,
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont, QTextCursor

from ..theme import ROLE_COLORS, TEXT_SECONDARY, BG_CARD, BG_MAIN, BORDER
from ..widgets.signal_plot import SignalPlotWidget

if TYPE_CHECKING:
    from core.pipeline import AnalysisResult, DebateTurn


ROLE_DISPLAY = {
    "proposer": ("Proposer", "🩺"),
    "checker":  ("Checker",  "🔍"),
    "skeptic":  ("Skeptic",  "⚠"),
    "advocate": ("Advocate", "⚖"),
    "arbiter":  ("Arbiter",  "⚡"),
}


class BubbleWidget(QFrame):
    """Single debate turn bubble."""

    def __init__(self, role: str, content: str, parent=None) -> None:
        super().__init__(parent)
        color = ROLE_COLORS.get(role.lower(), "#8b949e")
        display_name, icon = ROLE_DISPLAY.get(role.lower(), (role.capitalize(), "●"))
        obj_name = f"Bubble{role.capitalize()}"
        self.setObjectName(obj_name)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        lay = QVBoxLayout(self)
        lay.setContentsMargins(14, 10, 14, 10)
        lay.setSpacing(6)

        # Role header
        hdr = QHBoxLayout()
        role_lbl = QLabel(f"{icon}  {display_name}")
        role_font = role_lbl.font()
        role_font.setWeight(QFont.Weight.Bold)
        role_font.setPointSize(9)
        role_lbl.setFont(role_font)
        role_lbl.setStyleSheet(f"color: {color};")

        hdr.addWidget(role_lbl)
        hdr.addStretch()
        lay.addLayout(hdr)

        # Content
        content_lbl = QLabel(content)
        content_lbl.setWordWrap(True)
        content_lbl.setTextInteractionFlags(
            Qt.TextInteractionFlag.TextSelectableByMouse
        )
        content_lbl.setStyleSheet(f"color: #f0f6fc; font-size: 10pt;")
        content_lbl.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)
        lay.addWidget(content_lbl)


class DebateViewerPage(QWidget):
    """Debate transcript viewer with export functionality."""

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self._current_result = None
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
        title = QLabel("Debate Viewer")
        f = title.font()
        f.setPointSize(14)
        f.setBold(True)
        title.setFont(f)
        hdr_lay.addWidget(title)
        hdr_lay.addStretch()

        self._export_pdf_btn = QPushButton("Export PDF")
        self._export_pdf_btn.clicked.connect(self._export_pdf)
        self._export_pdf_btn.setEnabled(False)

        self._copy_json_btn = QPushButton("Copy JSON")
        self._copy_json_btn.clicked.connect(self._copy_json)
        self._copy_json_btn.setEnabled(False)

        hdr_lay.addWidget(self._export_pdf_btn)
        hdr_lay.addWidget(self._copy_json_btn)
        root.addWidget(hdr)

        div = QFrame()
        div.setObjectName("Divider")
        div.setFixedHeight(1)
        root.addWidget(div)

        # Splitter: left = transcript, right = mini signal
        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.setHandleWidth(2)

        # ── Left: transcript scroll area ───────────────────────────────────
        transcript_scroll = QScrollArea()
        transcript_scroll.setWidgetResizable(True)
        self._transcript_container = QWidget()
        self._transcript_layout = QVBoxLayout(self._transcript_container)
        self._transcript_layout.setContentsMargins(16, 16, 16, 16)
        self._transcript_layout.setSpacing(12)
        self._transcript_layout.addStretch()
        transcript_scroll.setWidget(self._transcript_container)
        splitter.addWidget(transcript_scroll)

        # ── Right: summary + mini signal ──────────────────────────────────
        right = QWidget()
        right.setMinimumWidth(280)
        right.setMaximumWidth(380)
        right_lay = QVBoxLayout(right)
        right_lay.setContentsMargins(8, 16, 16, 16)
        right_lay.setSpacing(12)

        # Result summary card
        summary_frame = QFrame()
        summary_frame.setObjectName("Card")
        sf_lay = QVBoxLayout(summary_frame)
        sf_lay.setContentsMargins(14, 12, 14, 12)
        sf_lay.setSpacing(6)

        sf_title = QLabel("Analysis Summary")
        sf_title_f = sf_title.font()
        sf_title_f.setBold(True)
        sf_title.setFont(sf_title_f)
        sf_lay.addWidget(sf_title)

        self._rhythm_lbl = QLabel("Rhythm: —")
        self._conf_lbl = QLabel("Confidence: —")
        self._flag_lbl = QLabel("Review Flag: —")
        self._ece_lbl = QLabel("ECE: —")
        self._model_lbl = QLabel("Model: —")
        self._tokens_lbl = QLabel("Tokens: —")

        for lbl in [self._rhythm_lbl, self._conf_lbl, self._flag_lbl,
                    self._ece_lbl, self._model_lbl, self._tokens_lbl]:
            lbl.setObjectName("SubLabel")
            lbl.setWordWrap(True)
            sf_lay.addWidget(lbl)

        right_lay.addWidget(summary_frame)

        # Role legend
        legend_frame = QFrame()
        legend_frame.setObjectName("Card")
        lf_lay = QVBoxLayout(legend_frame)
        lf_lay.setContentsMargins(14, 12, 14, 12)
        lf_lay.setSpacing(4)
        lf_title = QLabel("Agent Roles")
        lf_title_f = lf_title.font()
        lf_title_f.setBold(True)
        lf_title.setFont(lf_title_f)
        lf_lay.addWidget(lf_title)

        for role, (name, icon) in ROLE_DISPLAY.items():
            color = ROLE_COLORS.get(role, "#8b949e")
            row = QHBoxLayout()
            dot = QLabel("●")
            dot.setStyleSheet(f"color: {color}; font-size: 14pt;")
            dot.setFixedWidth(24)
            lbl = QLabel(f"{icon} {name}")
            lbl.setObjectName("SubLabel")
            row.addWidget(dot)
            row.addWidget(lbl)
            row.addStretch()
            lf_lay.addLayout(row)

        right_lay.addWidget(legend_frame)
        right_lay.addStretch()

        splitter.addWidget(right)
        splitter.setSizes([700, 320])
        root.addWidget(splitter)

    # ── public API ────────────────────────────────────────────────────────────

    def load_result(self, result) -> None:
        """Load an AnalysisResult and render its debate transcript."""
        self._current_result = result
        self._clear_transcript()

        if not result or not result.debate_transcript:
            placeholder = QLabel("No debate transcript available.\nRun an analysis first.")
            placeholder.setAlignment(Qt.AlignmentFlag.AlignCenter)
            placeholder.setObjectName("SubLabel")
            self._transcript_layout.insertWidget(
                self._transcript_layout.count() - 1, placeholder
            )
            return

        for turn in result.debate_transcript:
            bubble = BubbleWidget(turn.role, turn.content)
            self._transcript_layout.insertWidget(
                self._transcript_layout.count() - 1, bubble
            )

        # Update summary
        self._rhythm_lbl.setText(f"Rhythm: {result.rhythm}")
        self._conf_lbl.setText(f"Confidence: {result.confidence*100:.1f}%")
        flag_str = "YES ⚠" if result.review_flag else "No ✓"
        self._flag_lbl.setText(f"Review Flag: {flag_str}")
        self._ece_lbl.setText(f"ECE: {result.ece:.4f}  |  F1: {result.macro_f1:.3f}")
        self._model_lbl.setText(f"Model: {result.model_name}")
        self._tokens_lbl.setText(
            f"Tokens: {result.total_input_tokens:,} in / {result.total_output_tokens:,} out"
            + (f"  (${result.total_cost_usd:.4f})" if result.total_cost_usd > 0 else "")
        )

        self._export_pdf_btn.setEnabled(True)
        self._copy_json_btn.setEnabled(True)

    # ── private ───────────────────────────────────────────────────────────────

    def _clear_transcript(self) -> None:
        while self._transcript_layout.count() > 1:
            item = self._transcript_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

    def _copy_json(self) -> None:
        if not self._current_result:
            return
        data = {
            "rhythm": self._current_result.rhythm,
            "confidence": self._current_result.confidence,
            "review_flag": self._current_result.review_flag,
            "ece": self._current_result.ece,
            "macro_f1": self._current_result.macro_f1,
            "model": self._current_result.model_name,
            "debate": [
                {"role": t.role, "content": t.content}
                for t in self._current_result.debate_transcript
            ],
        }
        QApplication.clipboard().setText(json.dumps(data, indent=2))

    def _export_pdf(self) -> None:
        if not self._current_result:
            return
        path, _ = QFileDialog.getSaveFileName(
            self, "Export Debate as PDF", "debate_report.pdf",
            "PDF Files (*.pdf)"
        )
        if not path:
            return
        self._write_pdf(path)

    def _write_pdf(self, path: str) -> None:
        """Generate a PDF report using Qt's printing support."""
        try:
            from PySide6.QtPrintSupport import QPrinter
            from PySide6.QtGui import QTextDocument

            printer = QPrinter(QPrinter.PrinterMode.HighResolution)
            printer.setOutputFormat(QPrinter.OutputFormat.PdfFormat)
            printer.setOutputFileName(path)
            printer.setPageSize(__import__("PySide6.QtGui", fromlist=["QPageSize"]).QPageSize.A4)

            doc = QTextDocument()
            result = self._current_result
            html = f"""
            <html><body style="font-family: Arial; font-size: 11pt; color: #111;">
            <h2>PhysioSkeptic Debate Report</h2>
            <p><b>Rhythm:</b> {result.rhythm} &nbsp;
               <b>Confidence:</b> {result.confidence*100:.1f}% &nbsp;
               <b>Review Flag:</b> {"YES" if result.review_flag else "No"}</p>
            <p><b>ECE:</b> {result.ece:.4f} &nbsp; <b>Macro-F1:</b> {result.macro_f1:.3f} &nbsp;
               <b>Model:</b> {result.model_name}</p>
            <hr/>
            """
            for turn in result.debate_transcript:
                color_map = {
                    "proposer": "#1d4ed8", "checker": "#b45309",
                    "skeptic": "#dc2626", "advocate": "#059669", "arbiter": "#7c3aed",
                }
                c = color_map.get(turn.role.lower(), "#444")
                disp, icon = ROLE_DISPLAY.get(turn.role.lower(), (turn.role, ""))
                html += (f'<p style="color:{c};font-weight:bold;">{icon} {disp}</p>'
                         f'<p style="margin-left:16px;">{turn.content.replace(chr(10),"<br/>")}</p>'
                         f'<hr style="border:none;border-top:1px solid #ddd;"/>')
            html += "</body></html>"

            doc.setHtml(html)
            doc.print_(printer)
        except Exception as e:
            print(f"PDF export error: {e}")
