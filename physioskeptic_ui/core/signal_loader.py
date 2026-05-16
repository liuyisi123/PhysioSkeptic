"""
Signal Loader — PhysioSkeptic
Unified loader for EDF, CSV, NPZ, WFDB, JSON, HDF5.
Returns SignalData dataclass. Gracefully handles missing optional deps.
"""
from __future__ import annotations

import json
import math
import os
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

import numpy as np

# ── optional heavy deps ────────────────────────────────────────────────────────
try:
    import pyedflib
    _HAS_PYEDFLIB = True
except ImportError:
    _HAS_PYEDFLIB = False

try:
    import wfdb
    _HAS_WFDB = True
except ImportError:
    _HAS_WFDB = False

try:
    import pandas as pd
    _HAS_PANDAS = True
except ImportError:
    _HAS_PANDAS = False

try:
    import h5py
    _HAS_H5PY = True
except ImportError:
    _HAS_H5PY = False


@dataclass
class SignalData:
    """Unified signal container."""
    # primary channels (may be None)
    ecg: Optional[np.ndarray] = None
    ppg: Optional[np.ndarray] = None
    eeg: Optional[np.ndarray] = None          # shape (n_ch, n_samples) or 1-D
    respiration: Optional[np.ndarray] = None
    abp: Optional[np.ndarray] = None
    spo2: Optional[np.ndarray] = None

    # sampling rate (Hz) — common to all channels after resampling
    fs: float = 125.0

    # raw multi-channel array for display (n_ch × n_samples)
    channels: np.ndarray = field(default_factory=lambda: np.zeros((1, 100)))
    channel_names: List[str] = field(default_factory=list)

    # metadata
    duration_sec: float = 0.0
    patient_id: str = ""
    age: Optional[int] = None
    sex: str = ""
    notes: str = ""
    source_file: str = ""
    source_format: str = ""

    def __post_init__(self) -> None:
        if self.ecg is not None and self.duration_sec == 0.0:
            self.duration_sec = len(self.ecg) / max(self.fs, 1)

    @property
    def n_samples(self) -> int:
        for arr in [self.ecg, self.ppg, self.respiration, self.abp, self.spo2]:
            if arr is not None:
                return len(arr)
        if self.eeg is not None:
            return self.eeg.shape[-1]
        return self.channels.shape[-1]

    @property
    def time_axis(self) -> np.ndarray:
        return np.linspace(0, self.duration_sec, self.n_samples)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "patient_id": self.patient_id,
            "age": self.age,
            "sex": self.sex,
            "notes": self.notes,
            "source_file": self.source_file,
            "source_format": self.source_format,
            "fs": self.fs,
            "duration_sec": self.duration_sec,
            "n_samples": self.n_samples,
            "channels": self.channel_names,
        }


# ── synthetic demo generator ───────────────────────────────────────────────────

def _generate_sinus_ecg(n_samples: int, fs: float, hr_bpm: float = 70.0) -> np.ndarray:
    """Realistic-looking synthetic ECG via mathematical waveform."""
    t = np.linspace(0, n_samples / fs, n_samples)
    rr = 60.0 / hr_bpm
    ecg = np.zeros(n_samples)

    for beat_t in np.arange(0, t[-1], rr):
        # P wave
        p = 0.15 * np.exp(-0.5 * ((t - beat_t - 0.10) / 0.025) ** 2)
        # Q
        q = -0.05 * np.exp(-0.5 * ((t - beat_t - 0.14) / 0.008) ** 2)
        # R
        r = 1.2 * np.exp(-0.5 * ((t - beat_t - 0.17) / 0.010) ** 2)
        # S
        s = -0.20 * np.exp(-0.5 * ((t - beat_t - 0.20) / 0.010) ** 2)
        # T wave
        tw = 0.30 * np.exp(-0.5 * ((t - beat_t - 0.35) / 0.050) ** 2)
        ecg += p + q + r + s + tw

    noise = np.random.normal(0, 0.02, n_samples)
    baseline = 0.05 * np.sin(2 * np.pi * 0.15 * t)
    return ecg + noise + baseline


def _generate_ppg(n_samples: int, fs: float, hr_bpm: float = 70.0) -> np.ndarray:
    """Synthetic PPG waveform."""
    t = np.linspace(0, n_samples / fs, n_samples)
    rr = 60.0 / hr_bpm
    ppg = np.zeros(n_samples)
    for beat_t in np.arange(0, t[-1], rr):
        systolic = 0.8 * np.exp(-0.5 * ((t - beat_t - 0.20) / 0.06) ** 2)
        diastolic = 0.3 * np.exp(-0.5 * ((t - beat_t - 0.50) / 0.08) ** 2)
        ppg += systolic + diastolic
    noise = np.random.normal(0, 0.01, n_samples)
    return ppg + noise


def generate_demo_signal(duration_sec: float = 30.0, fs: float = 125.0) -> SignalData:
    """Generate a fully synthetic demo SignalData (sinus rhythm, 30 s, 125 Hz)."""
    n = int(duration_sec * fs)
    hr = 68.0 + np.random.uniform(-5, 5)
    ecg = _generate_sinus_ecg(n, fs, hr)
    ppg = _generate_ppg(n, fs, hr)
    resp = 0.5 * np.sin(2 * np.pi * 0.25 * np.linspace(0, duration_sec, n)) + np.random.normal(0, 0.02, n)

    channels = np.vstack([ecg, ppg, resp])
    return SignalData(
        ecg=ecg,
        ppg=ppg,
        respiration=resp,
        fs=fs,
        channels=channels,
        channel_names=["ECG Lead-II", "PPG", "Respiration"],
        duration_sec=duration_sec,
        patient_id="DEMO-001",
        age=45,
        sex="M",
        notes="Synthetic demo signal — sinus rhythm 30 s 125 Hz",
        source_file="<demo>",
        source_format="synthetic",
    )


# ── main loader class ──────────────────────────────────────────────────────────

class SignalLoader:
    """Load physiological signals from multiple file formats."""

    SUPPORTED_EXTENSIONS = {
        ".edf": "EDF",
        ".csv": "CSV",
        ".txt": "CSV",
        ".npz": "NPZ",
        ".npy": "NPY",
        ".json": "JSON",
        ".hea": "WFDB",
        ".dat": "WFDB",
        ".hdf5": "HDF5",
        ".h5": "HDF5",
    }

    def load(self, path: str, fs_override: Optional[float] = None) -> SignalData:
        """Dispatch to correct loader based on file extension."""
        ext = os.path.splitext(path)[1].lower()
        fmt = self.SUPPORTED_EXTENSIONS.get(ext, "UNKNOWN")

        if fmt == "EDF":
            data = self._load_edf(path)
        elif fmt == "CSV":
            data = self._load_csv(path)
        elif fmt == "NPZ":
            data = self._load_npz(path)
        elif fmt == "NPY":
            data = self._load_npy(path)
        elif fmt == "JSON":
            data = self._load_json(path)
        elif fmt == "WFDB":
            data = self._load_wfdb(path)
        elif fmt == "HDF5":
            data = self._load_hdf5(path)
        else:
            raise ValueError(f"Unsupported file format: {ext}")

        if fs_override is not None:
            data = self._resample_signal(data, fs_override)

        data.source_file = os.path.basename(path)
        data.source_format = fmt
        return data

    # ── EDF ────────────────────────────────────────────────────────────────────
    def _load_edf(self, path: str) -> SignalData:
        if not _HAS_PYEDFLIB:
            return self._mock_load(path, "EDF")

        import pyedflib
        f = pyedflib.EdfReader(path)
        n_channels = f.signals_in_file
        labels = f.getSignalLabels()
        fs = f.getSampleFrequency(0)
        channels = np.array([f.readSignal(i) for i in range(n_channels)])
        f._close()

        return self._channels_to_signal_data(channels, labels, fs, path)

    # ── CSV ────────────────────────────────────────────────────────────────────
    def _load_csv(self, path: str) -> SignalData:
        if not _HAS_PANDAS:
            return self._mock_load(path, "CSV")

        import pandas as pd
        df = pd.read_csv(path)
        cols = list(df.columns)
        fs = 125.0

        # try to detect a time column
        time_col = None
        for c in cols:
            if c.lower() in ("time", "t", "timestamp", "seconds"):
                time_col = c
                break

        if time_col and len(df) > 1:
            dt = float(df[time_col].iloc[1] - df[time_col].iloc[0])
            if dt > 0:
                fs = 1.0 / dt

        data_cols = [c for c in cols if c != time_col]
        channels = df[data_cols].to_numpy(dtype=np.float32).T

        return self._channels_to_signal_data(channels, data_cols, fs, path)

    # ── NPZ ───────────────────────────────────────────────────────────────────
    def _load_npz(self, path: str) -> SignalData:
        npz = np.load(path, allow_pickle=True)
        keys = list(npz.keys())
        fs = float(npz.get("fs", 125.0))

        channels = []
        names = []
        ecg = ppg = None
        for k in keys:
            if k == "fs":
                continue
            arr = np.squeeze(npz[k]).astype(np.float32)
            if arr.ndim == 1:
                channels.append(arr)
                names.append(k)
                if "ecg" in k.lower():
                    ecg = arr
                elif "ppg" in k.lower():
                    ppg = arr

        if not channels:
            return self._mock_load(path, "NPZ")

        max_len = max(len(c) for c in channels)
        padded = np.array([np.pad(c, (0, max_len - len(c))) for c in channels])

        sd = SignalData(
            ecg=ecg,
            ppg=ppg,
            fs=fs,
            channels=padded,
            channel_names=names,
            duration_sec=max_len / fs,
        )
        return sd

    # ── NPY ───────────────────────────────────────────────────────────────────
    def _load_npy(self, path: str) -> SignalData:
        arr = np.load(path, allow_pickle=False).astype(np.float32)
        if arr.ndim == 1:
            arr = arr[np.newaxis, :]
        fs = 125.0
        names = [f"Ch{i}" for i in range(arr.shape[0])]
        return self._channels_to_signal_data(arr, names, fs, path)

    # ── JSON ──────────────────────────────────────────────────────────────────
    def _load_json(self, path: str) -> SignalData:
        with open(path, "r", encoding="utf-8") as fh:
            obj = json.load(fh)

        fs = float(obj.get("fs", obj.get("sampling_rate", 125.0)))
        channels_dict = obj.get("channels", obj.get("signals", {}))
        meta = obj.get("metadata", {})

        channels = []
        names = []
        ecg = ppg = None
        for k, v in channels_dict.items():
            arr = np.array(v, dtype=np.float32)
            channels.append(arr)
            names.append(k)
            if "ecg" in k.lower():
                ecg = arr
            elif "ppg" in k.lower():
                ppg = arr

        if not channels:
            return self._mock_load(path, "JSON")

        max_len = max(len(c) for c in channels)
        padded = np.array([np.pad(c, (0, max_len - len(c))) for c in channels])

        return SignalData(
            ecg=ecg,
            ppg=ppg,
            fs=fs,
            channels=padded,
            channel_names=names,
            duration_sec=max_len / fs,
            patient_id=str(meta.get("patient_id", "")),
            age=meta.get("age"),
            sex=str(meta.get("sex", "")),
            notes=str(meta.get("notes", "")),
        )

    # ── WFDB ──────────────────────────────────────────────────────────────────
    def _load_wfdb(self, path: str) -> SignalData:
        if not _HAS_WFDB:
            return self._mock_load(path, "WFDB")

        import wfdb
        record_name = os.path.splitext(path)[0]
        rec = wfdb.rdrecord(record_name)
        channels = rec.p_signal.T.astype(np.float32)
        fs = float(rec.fs)
        names = rec.sig_name
        return self._channels_to_signal_data(channels, names, fs, path)

    # ── HDF5 ──────────────────────────────────────────────────────────────────
    def _load_hdf5(self, path: str) -> SignalData:
        if not _HAS_H5PY:
            return self._mock_load(path, "HDF5")

        import h5py
        channels = []
        names = []
        fs = 125.0
        ecg = ppg = None

        with h5py.File(path, "r") as f:
            fs = float(f.attrs.get("fs", fs))
            for k in f.keys():
                arr = np.array(f[k], dtype=np.float32)
                if arr.ndim == 1:
                    channels.append(arr)
                    names.append(k)
                    if "ecg" in k.lower():
                        ecg = arr
                    elif "ppg" in k.lower():
                        ppg = arr

        if not channels:
            return self._mock_load(path, "HDF5")

        max_len = max(len(c) for c in channels)
        padded = np.array([np.pad(c, (0, max_len - len(c))) for c in channels])
        return SignalData(ecg=ecg, ppg=ppg, fs=fs, channels=padded,
                         channel_names=names, duration_sec=max_len / fs)

    # ── helpers ───────────────────────────────────────────────────────────────
    def _channels_to_signal_data(
        self, channels: np.ndarray, names: List[str], fs: float, path: str
    ) -> SignalData:
        ecg = ppg = resp = abp = spo2 = None
        for i, name in enumerate(names):
            nl = name.lower()
            arr = channels[i]
            if any(x in nl for x in ("ecg", "ekg", "lead", "ii")):
                ecg = arr
            elif "ppg" in nl or "pleth" in nl:
                ppg = arr
            elif any(x in nl for x in ("resp", "rsp", "breath")):
                resp = arr
            elif any(x in nl for x in ("abp", "bp", "blood")):
                abp = arr
            elif "spo2" in nl or "spo" in nl:
                spo2 = arr
            # default first channel to ECG if nothing matched
        if ecg is None and channels.shape[0] > 0:
            ecg = channels[0]

        n = channels.shape[1]
        return SignalData(
            ecg=ecg, ppg=ppg, respiration=resp, abp=abp, spo2=spo2,
            fs=fs, channels=channels, channel_names=names,
            duration_sec=n / fs,
        )

    def _mock_load(self, path: str, fmt: str) -> SignalData:
        """Return synthetic data when real loader unavailable."""
        sd = generate_demo_signal()
        sd.source_file = os.path.basename(path)
        sd.source_format = f"{fmt}(mock)"
        sd.notes = f"Mock data — {fmt} loader not available (install optional deps)"
        return sd

    def _resample_signal(self, data: SignalData, target_fs: float) -> SignalData:
        """Simple linear resampling to target_fs."""
        if abs(data.fs - target_fs) < 0.01:
            return data
        try:
            from scipy.signal import resample_poly
            ratio_num = int(target_fs)
            ratio_den = int(data.fs)
            from math import gcd
            g = gcd(ratio_num, ratio_den)
            up, down = ratio_num // g, ratio_den // g

            def _r(arr: Optional[np.ndarray]) -> Optional[np.ndarray]:
                if arr is None:
                    return None
                return resample_poly(arr, up, down).astype(np.float32)

            new_channels = np.array([
                resample_poly(data.channels[i], up, down).astype(np.float32)
                for i in range(data.channels.shape[0])
            ])
            data.ecg = _r(data.ecg)
            data.ppg = _r(data.ppg)
            data.respiration = _r(data.respiration)
            data.abp = _r(data.abp)
            data.spo2 = _r(data.spo2)
            data.channels = new_channels
            data.fs = target_fs
        except Exception:
            pass
        return data
