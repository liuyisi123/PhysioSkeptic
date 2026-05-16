"""
Database — PhysioSkeptic
SQLite persistence layer using stdlib sqlite3 only.
Tables: sessions, results, api_usage
"""
from __future__ import annotations

import csv
import json
import os
import sqlite3
import time
from dataclasses import asdict
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple


_DEFAULT_DB_PATH = os.path.join(os.path.expanduser("~"), ".physioskeptic", "history.db")


def _ensure_dir(path: str) -> None:
    d = os.path.dirname(path)
    if d:
        os.makedirs(d, exist_ok=True)


class Database:
    """SQLite-backed persistence for PhysioSkeptic sessions and results."""

    def __init__(self, db_path: Optional[str] = None) -> None:
        self.db_path = db_path or _DEFAULT_DB_PATH
        _ensure_dir(self.db_path)
        self._conn = sqlite3.connect(self.db_path, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._conn.execute("PRAGMA journal_mode=WAL")
        self._init_schema()

    def _init_schema(self) -> None:
        cur = self._conn.cursor()

        cur.executescript("""
        CREATE TABLE IF NOT EXISTS sessions (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            name        TEXT NOT NULL DEFAULT 'Session',
            created_at  REAL NOT NULL,
            notes       TEXT DEFAULT ''
        );

        CREATE TABLE IF NOT EXISTS results (
            id                  INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id          INTEGER REFERENCES sessions(id),
            created_at          REAL NOT NULL,
            signal_file         TEXT DEFAULT '',
            signal_format       TEXT DEFAULT '',
            patient_id          TEXT DEFAULT '',
            duration_sec        REAL DEFAULT 0,
            fs                  REAL DEFAULT 125,
            model_name          TEXT DEFAULT '',
            routing             TEXT DEFAULT '',
            rhythm              TEXT DEFAULT '',
            confidence          REAL DEFAULT 0,
            review_flag         INTEGER DEFAULT 0,
            review_reason       TEXT DEFAULT '',
            ece                 REAL DEFAULT 0,
            macro_f1            REAL DEFAULT 0,
            total_input_tokens  INTEGER DEFAULT 0,
            total_output_tokens INTEGER DEFAULT 0,
            total_cost_usd      REAL DEFAULT 0,
            analysis_duration   REAL DEFAULT 0,
            debate_json         TEXT DEFAULT '[]',
            patch_json          TEXT DEFAULT '{}'
        );

        CREATE TABLE IF NOT EXISTS api_usage (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            ts           REAL NOT NULL,
            provider     TEXT DEFAULT '',
            model        TEXT DEFAULT '',
            input_tokens INTEGER DEFAULT 0,
            output_tokens INTEGER DEFAULT 0,
            cost_usd     REAL DEFAULT 0,
            latency_ms   REAL DEFAULT 0
        );

        CREATE INDEX IF NOT EXISTS idx_results_created ON results(created_at DESC);
        CREATE INDEX IF NOT EXISTS idx_results_rhythm  ON results(rhythm);
        CREATE INDEX IF NOT EXISTS idx_api_usage_ts    ON api_usage(ts DESC);
        """)
        self._conn.commit()

    # ── sessions ──────────────────────────────────────────────────────────────

    def create_session(self, name: str = "Session", notes: str = "") -> int:
        cur = self._conn.execute(
            "INSERT INTO sessions (name, created_at, notes) VALUES (?,?,?)",
            (name, time.time(), notes)
        )
        self._conn.commit()
        return cur.lastrowid

    def get_sessions(self) -> List[Dict]:
        rows = self._conn.execute(
            "SELECT * FROM sessions ORDER BY created_at DESC"
        ).fetchall()
        return [dict(r) for r in rows]

    def update_session(self, session_id: int, name: str) -> None:
        self._conn.execute(
            "UPDATE sessions SET name=? WHERE id=?", (name, session_id)
        )
        self._conn.commit()

    # ── results ───────────────────────────────────────────────────────────────

    def save_result(self, result_dict: Dict[str, Any], session_id: Optional[int] = None) -> int:
        cur = self._conn.execute("""
            INSERT INTO results (
                session_id, created_at, signal_file, signal_format,
                patient_id, duration_sec, fs, model_name, routing,
                rhythm, confidence, review_flag, review_reason,
                ece, macro_f1, total_input_tokens, total_output_tokens,
                total_cost_usd, analysis_duration, debate_json, patch_json
            ) VALUES (
                :session_id, :created_at, :signal_file, :signal_format,
                :patient_id, :duration_sec, :fs, :model_name, :routing,
                :rhythm, :confidence, :review_flag, :review_reason,
                :ece, :macro_f1, :total_input_tokens, :total_output_tokens,
                :total_cost_usd, :analysis_duration, :debate_json, :patch_json
            )
        """, {
            "session_id": session_id,
            "created_at": result_dict.get("created_at", time.time()),
            "signal_file": result_dict.get("signal_file", ""),
            "signal_format": result_dict.get("signal_format", ""),
            "patient_id": result_dict.get("patient_id", ""),
            "duration_sec": result_dict.get("duration_sec", 0),
            "fs": result_dict.get("fs", 125),
            "model_name": result_dict.get("model_name", ""),
            "routing": result_dict.get("routing", ""),
            "rhythm": result_dict.get("rhythm", ""),
            "confidence": result_dict.get("confidence", 0),
            "review_flag": int(result_dict.get("review_flag", False)),
            "review_reason": result_dict.get("review_reason", ""),
            "ece": result_dict.get("ece", 0),
            "macro_f1": result_dict.get("macro_f1", 0),
            "total_input_tokens": result_dict.get("total_input_tokens", 0),
            "total_output_tokens": result_dict.get("total_output_tokens", 0),
            "total_cost_usd": result_dict.get("total_cost_usd", 0),
            "analysis_duration": result_dict.get("analysis_duration", 0),
            "debate_json": json.dumps(result_dict.get("debate_transcript", [])),
            "patch_json": json.dumps(result_dict.get("patch_report", {})),
        })
        self._conn.commit()
        return cur.lastrowid

    def get_results(
        self,
        limit: int = 100,
        offset: int = 0,
        rhythm_filter: Optional[str] = None,
        model_filter: Optional[str] = None,
        flagged_only: bool = False,
        search: Optional[str] = None,
        date_from: Optional[float] = None,
        date_to: Optional[float] = None,
    ) -> List[Dict]:
        conditions = []
        params: List[Any] = []

        if rhythm_filter:
            conditions.append("rhythm = ?")
            params.append(rhythm_filter)
        if model_filter:
            conditions.append("model_name = ?")
            params.append(model_filter)
        if flagged_only:
            conditions.append("review_flag = 1")
        if search:
            conditions.append("(signal_file LIKE ? OR patient_id LIKE ? OR rhythm LIKE ?)")
            s = f"%{search}%"
            params.extend([s, s, s])
        if date_from:
            conditions.append("created_at >= ?")
            params.append(date_from)
        if date_to:
            conditions.append("created_at <= ?")
            params.append(date_to)

        where = ("WHERE " + " AND ".join(conditions)) if conditions else ""
        sql = f"SELECT * FROM results {where} ORDER BY created_at DESC LIMIT ? OFFSET ?"
        params.extend([limit, offset])
        rows = self._conn.execute(sql, params).fetchall()
        return [dict(r) for r in rows]

    def get_result_by_id(self, result_id: int) -> Optional[Dict]:
        row = self._conn.execute(
            "SELECT * FROM results WHERE id=?", (result_id,)
        ).fetchone()
        return dict(row) if row else None

    def delete_results(self, ids: List[int]) -> None:
        placeholders = ",".join("?" for _ in ids)
        self._conn.execute(f"DELETE FROM results WHERE id IN ({placeholders})", ids)
        self._conn.commit()

    def count_results(self) -> int:
        return self._conn.execute("SELECT COUNT(*) FROM results").fetchone()[0]

    def avg_macro_f1(self) -> float:
        row = self._conn.execute("SELECT AVG(macro_f1) FROM results WHERE macro_f1 > 0").fetchone()
        return float(row[0] or 0.0)

    def count_flagged_today(self) -> int:
        today_start = datetime.now().replace(hour=0, minute=0, second=0).timestamp()
        return self._conn.execute(
            "SELECT COUNT(*) FROM results WHERE review_flag=1 AND created_at>=?",
            (today_start,)
        ).fetchone()[0]

    def api_calls_today(self) -> int:
        today_start = datetime.now().replace(hour=0, minute=0, second=0).timestamp()
        return self._conn.execute(
            "SELECT COUNT(*) FROM api_usage WHERE ts>=?", (today_start,)
        ).fetchone()[0]

    def rhythm_distribution(self) -> Dict[str, int]:
        rows = self._conn.execute(
            "SELECT rhythm, COUNT(*) as cnt FROM results GROUP BY rhythm ORDER BY cnt DESC"
        ).fetchall()
        return {r["rhythm"]: r["cnt"] for r in rows}

    # ── api_usage ─────────────────────────────────────────────────────────────

    def log_api_call(
        self, provider: str, model: str,
        input_tokens: int, output_tokens: int,
        cost_usd: float, latency_ms: float,
    ) -> None:
        self._conn.execute("""
            INSERT INTO api_usage (ts, provider, model, input_tokens, output_tokens, cost_usd, latency_ms)
            VALUES (?,?,?,?,?,?,?)
        """, (time.time(), provider, model, input_tokens, output_tokens, cost_usd, latency_ms))
        self._conn.commit()

    # ── export ────────────────────────────────────────────────────────────────

    def export_csv(self, path: str, result_ids: Optional[List[int]] = None) -> int:
        if result_ids:
            rows = [self.get_result_by_id(i) for i in result_ids if i]
            rows = [r for r in rows if r]
        else:
            rows = self.get_results(limit=10000)

        if not rows:
            return 0

        fieldnames = [
            "id", "created_at", "signal_file", "patient_id",
            "model_name", "rhythm", "confidence",
            "review_flag", "macro_f1", "ece",
            "total_input_tokens", "total_output_tokens",
            "total_cost_usd", "analysis_duration",
        ]

        with open(path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
            writer.writeheader()
            for row in rows:
                # format timestamp
                if "created_at" in row:
                    row = dict(row)
                    row["created_at"] = datetime.fromtimestamp(row["created_at"]).strftime(
                        "%Y-%m-%d %H:%M:%S"
                    )
                writer.writerow(row)
        return len(rows)

    def seed_demo_data(self, n: int = 15) -> None:
        """Insert realistic demo rows so the app is usable immediately."""
        from .pipeline import RHYTHM_CLASSES
        import random

        rhythms = ["Sinus Rhythm"] * 8 + [
            "Atrial Fibrillation", "Sinus Bradycardia",
            "First-Degree AV Block", "Sinus Tachycardia",
            "Premature Ventricular Contractions",
        ]
        models = ["Mock / Demo", "GPT-4o", "Claude-3.7", "DeepSeek-V3.2"]
        t_base = time.time() - 7 * 86400

        for i in range(n):
            rhythm = random.choice(rhythms)
            conf = round(random.uniform(0.71, 0.97), 3)
            flag = conf < 0.75
            self.save_result({
                "created_at": t_base + i * 3600 + random.uniform(0, 1800),
                "signal_file": f"patient_{100 + i:03d}_ecg.edf",
                "signal_format": random.choice(["EDF", "CSV", "NPZ"]),
                "patient_id": f"PT-{100 + i:03d}",
                "duration_sec": random.choice([30, 60, 120, 300]),
                "fs": 125.0,
                "model_name": random.choice(models),
                "routing": random.choice(["Auto", "Force Standard"]),
                "rhythm": rhythm,
                "confidence": conf,
                "review_flag": flag,
                "review_reason": "Low confidence" if flag else "",
                "ece": round(random.uniform(0.04, 0.14), 4),
                "macro_f1": round(random.uniform(0.80, 0.96), 3),
                "total_input_tokens": random.randint(1800, 3500),
                "total_output_tokens": random.randint(500, 1200),
                "total_cost_usd": round(random.uniform(0.0, 0.08), 4),
                "analysis_duration": round(random.uniform(3.5, 18.0), 2),
            })

    def close(self) -> None:
        self._conn.close()
