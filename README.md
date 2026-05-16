# PhysioSkeptic

**Signal-quality-anchored, multi-agent skeptical reasoning for robust ECG–PPG cardiac rhythm diagnosis.**

> Code and desktop application for the accompanying paper (under review).
> Anonymous repository — author details will be released upon acceptance.

---

## What is PhysioSkeptic?

Conventional waveform-to-text pipelines discard beat-level reliability before prompting an LLM.
PhysioSkeptic keeps it. The **PhysioPatch** encoder aligns tokens to detected heartbeats and
produces a structured **Patch Report** that lists per-beat confidence, P-wave support, RR
variability, and cross-modal consistency cues. A **five-role debate** (Proposer → Checker →
Skeptic → Advocate → Arbiter) then uses those numeric anchors to scale challenge pressure,
surface ECG–PPG conflict, and revise overconfident hypotheses — all in auditable JSON.

On MIMIC-III-Ext-PPG: **0.886 Macro-F1**, lowest ECE among GPT-5.2 methods, anchor-trap
retention reduced from 56.6 % to 16.8 %, with gains concentrated in low-SQI and
cross-modal-conflict cases where competing methods degrade most.

---

## Desktop Application

A professional desktop GUI ships with this repository. It provides a point-and-click
interface to the full pipeline — import signals, configure any LLM backend, run the
five-role debate, inspect the role-by-role transcript, and process files in batch.

### Screenshots

| Startup | Dashboard |
|:---:|:---:|
| ![Startup splash screen](assets/screenshots/splash.png) | ![Dashboard with KPI cards](assets/screenshots/dashboard.png) |

| Analysis — Demo Signal | Debate Viewer |
|:---:|:---:|
| ![Analysis page with demo ECG/PPG](assets/screenshots/analysis.png) | ![Five-role debate transcript](assets/screenshots/debate.png) |

| API & Settings | |
|:---:|:---:|
| ![API key configuration](assets/screenshots/setting.png) | |

```
┌─────────────────────────────────────────────────────────────────────┐
│  PhysioSkeptic                          Session: demo_ecg_ppg  ▾  ● │
├──────────────┬──────────────────────────────────────────────────────┤
│              │                                                       │
│  WORKSPACE   │  ◎  Analysis                        [DEMO]           │
│              │  ──────────────────────────────────────────────────  │
│  ⬡  Dashboard│  ECG ─────────────────────────────────────────────── │
│  ↑  Import   │        ╭──╮  ╭──╮  ╭──╮  ╭──╮  ╭──╮  ╭──╮          │
│  ◎  Analysis │  ──────╯  ╰──╯  ╰──╯  ╰──╯  ╰──╯  ╰──╯  ╰───────── │
│  ≡  Debate   │  PPG ─────────────────────────────────────────────── │
│  ⊟  Batch    │       ╭─╮    ╭─╮    ╭─╮    ╭─╮    ╭─╮    ╭─╮        │
│              │  ─────╯ ╰────╯ ╰────╯ ╰────╯ ╰────╯ ╰────╯ ╰─────── │
│  MANAGE      │                                                       │
│  ◷  History  │  ─────────────────────────────────────────────────── │
│  ⚙  Settings │  ♥  Sinus Rhythm               ╭───────────────╮     │
│              │                      Confidence │      87 %     │     │
│  v 1.0.0     │  ✓  Cleared                    ╰───────────────╯     │
│  Research    │  ECE 0.033  Macro-F1 0.886  Route STANDARD           │
└──────────────┴──────────────────────────────────────────────────────┘
```

```
┌──────────────────────────────────────────────────────────────────────┐
│  ≡  Debate Viewer                                Export PDF  Copy JSON│
│  ─────────────────────────────────────────────────────────────────── │
│  ┌──────────────────────────────────────────────────────────────┐    │
│  │ 🔵 PROPOSER   Initial rhythm: Sinus Rhythm (c₀ = 0.74)       │    │
│  │   Evidence: beat_3 HR=68 bpm · p_wave_ratio=0.91 · q̂=0.82   │    │
│  └──────────────────────────────────────────────────────────────┘    │
│  ┌──────────────────────────────────────────────────────────────┐    │
│  │ 🟠 CHECKER    HR conflict flagged: ΔHR(ECG–PPG)=8 bpm        │    │
│  │   Severity: MINOR  beat_7 confidence=0.31                    │    │
│  └──────────────────────────────────────────────────────────────┘    │
│  ┌──────────────────────────────────────────────────────────────┐    │
│  │ 🔴 SKEPTIC    Challenge 1/2: beat_7 q̂=0.31 < 0.40 threshold │    │
│  │   Alternative: cannot confirm SR with corrupted beat cluster  │    │
│  └──────────────────────────────────────────────────────────────┘    │
│  ┌──────────────────────────────────────────────────────────────┐    │
│  │ 🟢 ADVOCATE   Concedes beat_7; retains SR (p_wave_ratio=0.91)│    │
│  └──────────────────────────────────────────────────────────────┘    │
│  ┌──────────────────────────────────────────────────────────────┐    │
│  │ 🟣 ARBITER    Final: Sinus Rhythm · c_final=0.87 · CLEAR     │    │
│  └──────────────────────────────────────────────────────────────┘    │
└──────────────────────────────────────────────────────────────────────┘
```

### Running the desktop app

```bash
cd physioskeptic_ui
pip install PySide6 pyqtgraph pyinstaller
python main.py
```

No API key required — select **Mock / Demo** in the model dropdown to run a full
five-role debate with realistic synthetic results instantly.

A pre-built Windows executable is available in `physioskeptic_ui/dist/PhysioSkeptic.exe`
(no Python installation needed, double-click to launch).

### Desktop app features

| Page | What you can do |
|---|---|
| **Dashboard** | Live KPI cards (analyses, avg F1, flagged, API calls), recent results table, rhythm distribution chart |
| **Signal Import** | Drag-and-drop EDF / CSV / NPZ / WFDB / HDF5 / JSON; channel assignment; bandpass filter; 125 Hz resample; multi-channel pyqtgraph preview |
| **Analysis** | Model selector (7 providers), API key field, routing / temperature / SQI threshold sliders, stage-by-stage progress, confidence arc gauge |
| **Debate Viewer** | Color-coded role bubbles (Proposer blue · Checker amber · Skeptic red · Advocate green · Arbiter purple), beat citation display, PDF export |
| **Batch** | File queue, pause / resume / cancel, per-file status, ETA, CSV export |
| **History** | Searchable / sortable table, date-range and rhythm filters, detail panel, CSV export |
| **Settings** | API keys for 7 providers, default model, routing defaults, preprocessing, appearance |

### Supported LLM providers

| Provider | Models |
|---|---|
| OpenAI | `gpt-5.2`, `gpt-5`, `gpt-4o` |
| Anthropic | `claude-3-7-sonnet`, `claude-3-5-haiku` |
| DeepSeek | `deepseek-chat` |
| Qwen (DashScope) | `qwen3.5-27b`, `qwen-plus` |
| Ollama (local) | any locally running model |
| Azure OpenAI | custom endpoint + deployment |
| **Mock / Demo** | built-in, no key needed |

### Supported signal formats

EDF, CSV, NPZ/NPY, WFDB (`.hea`/`.dat`), HDF5, JSON.
Supported modalities: ECG, PPG, EEG, Respiration, ABP, SpO₂.
Signals are resampled to 125 Hz and only the derived Patch Report is sent to LLM APIs —
raw waveforms never leave the local machine.

---

## Library / command-line usage

This repository also works as a Python library. Install and run without the GUI:

```bash
git clone https://github.com/<your-org>/physioskeptic.git
cd physioskeptic
python -m venv .venv
source .venv/bin/activate       # Windows: .venv\Scripts\activate
pip install -e .[dev]
pytest -q
python scripts/run_demo.py --backend mock
```

---

## Method summary

1. **Heartbeat-aligned patching** — ECG R-peaks (Pan-Tompkins) and PPG systolic onsets define one token per beat; patches are right-padded to min inter-beat interval Δ.
2. **Dual-path encoding** — Path A: multi-scale 1D-CNN + 6-layer Transformer → temporal beat tokens; Path B: STFT (W=256, H=64, 0.5–30 Hz) + 2D-CNN → frequency rhythm embedding; SQI head: σ(MLP(mean H_temp)) → q̂ ∈ [0,1]; SQI-gated fusion: H_fused = q̂·H_temp + (1−q̂)·broadcast(h_freq W_f).
3. **Patch Report** — deterministic JSON: beat_confidences c∈[0,1]^N, scalar q̂, low-confidence beat list (index, time window, attention), P-wave ratio, LF/HF.
4. **Five-role debate** — Proposer, Checker, Skeptic (n_chal = 3−⌊2q̂⌋ ∈ {1,2,3}), Advocate, Arbiter; each challenge must cite a report field.
5. **Adaptive routing** — Fast (c₀>0.9 ∧ q̂>0.8 ∧ no conflict), Deep (q̂<0.5 ∨ c₀<0.6 ∨ MAJOR conflict), else Standard; review flag at c_final < 0.70.

Target classes: `SR  STACH  SBRAD  AF_FAMILY  PACE`

---

## Repository layout

```
physioskeptic/
├── README.md
├── LICENSE
├── pyproject.toml
├── requirements.txt
├── configs/
│   └── default.yaml                  # encoder + routing + LLM defaults
├── data/
│   ├── sample_patch_report.json      # example Patch Report
│   └── patch_report.schema.json      # JSON Schema for validation
├── prompts/
│   ├── proposer.yaml                 # role prompts with output schemas
│   ├── checker.yaml
│   ├── skeptic.yaml
│   ├── advocate.yaml
│   └── arbiter.yaml
├── scripts/
│   ├── run_demo.py                   # CLI demo (mock backend)
│   ├── reproduce_figures.py          # figure reproduction from aggregate tables
│   ├── run_eval.py                   # batch evaluation
│   └── make_release_zip.py
├── src/physioskeptic/
│   ├── signal_processing.py          # bandpass, R-peak, SQI
│   ├── encoder.py                    # PhysioPatch dual-path + Q-Former
│   ├── patch_report.py               # deterministic report builder
│   ├── routing.py                    # Fast/Standard/Deep routing
│   ├── debate.py                     # five-role pipeline
│   ├── llm_clients.py                # pluggable API backends
│   ├── metrics.py                    # F1, ECE, Brier, NLL, AUROC
│   ├── corruptions.py                # GWN / BW / MA noise injection
│   ├── train_encoder.py              # PhysioPatch pre-training
│   └── distill_student.py            # Llama-1B student distillation
├── tests/
│   ├── test_patch_report.py          # 19 patch-report unit tests
│   └── test_routing.py               # 19 routing unit tests
└── physioskeptic_ui/                 # ← desktop application
    ├── main.py                       # entry point (python main.py)
    ├── build.spec                    # PyInstaller → .exe
    ├── core/
    │   ├── api_client.py             # 7-provider unified LLM client
    │   ├── signal_loader.py          # multi-format signal loader
    │   ├── pipeline.py               # pipeline wrapper + progress
    │   └── database.py               # SQLite result history
    ├── ui/
    │   ├── splash.py                 # animated startup screen
    │   ├── main_window.py            # sidebar + stacked pages
    │   ├── theme.py                  # dark medical QSS stylesheet
    │   ├── pages/                    # Dashboard / Import / Analysis /
    │   │                             # Debate / Batch / History / Settings
    │   └── widgets/                  # SignalPlot / ResultCard / NavButton …
    └── dist/
        └── PhysioSkeptic.exe         # pre-built Windows executable
```

---

## Data preparation

The paper uses MIMIC-III-Ext-PPG (v1.0.0, frozen before submission) under PhysioNet
credentialed access. This repository does **not** redistribute waveforms, patient identifiers,
or derived labels.

Expected per-window format (30 s, 125 Hz):

```json
{
  "sample_id": "patient0001_window0001",
  "fs": 125,
  "ecg": [0.01, 0.02, "... 3750 samples ..."],
  "ppg": [0.11, 0.10, "... 3750 samples ..."],
  "label": "AF_FAMILY",
  "patient_id": "local_deidentified_id"
}
```

Split policy: patient-disjoint train / validation / test; fixed subject-window IDs across
all methods; no tuning on the test set.

---

## LLM backend

Paper experiments use `gpt-5.2` (public alias, OpenAI API, ZDR endpoint, January–March 2026).
The default CLI backend is `mock` (deterministic, no network, suitable for CI).

Required behavior for any backend:

- JSON-only structured output;
- fixed decoding settings: T=0.7, top_p=1.0, max 8 192 tokens;
- no raw waveform in context;
- log snapshot ID, access date, prompt template hashes, and sample IDs;
- fail closed on schema violations.

```bash
export PHYSIOSKEPTIC_LLM_BACKEND=openai_compatible
export PHYSIOSKEPTIC_API_KEY=sk-...
python scripts/run_eval.py \
    --config configs/default.yaml \
    --input path/to/patch_reports.jsonl
```

---

## Training and distillation

**PhysioPatch pre-training** (see §3.2 of the accompanying paper):

```bash
python -m physioskeptic.train_encoder \
  --config configs/default.yaml \
  --train-jsonl /path/to/train_windows.jsonl \
  --valid-jsonl /path/to/valid_windows.jsonl \
  --outdir checkpoints/physiopatch
```

Recipe: masked beat reconstruction (30 %) + InfoNCE ECG–PPG contrastive (τ=0.07, queue=4 096)
+ supervised SQI BCE; AdamW β=(0.9, 0.999) wd=1e-4; cosine LR 10 K warmup peak 3e-4;
200 K steps, batch 512, 8×A100 80 GB.

**Student distillation** (Llama-3.2-1B student):

```bash
python -m physioskeptic.distill_student \
  --teacher-jsonl /path/to/teacher_annotations.jsonl \
  --outdir checkpoints/student
```

Loss: `α·CE + β·KL(p̃_T‖p̃_S) + δ₁·MSE(c_T, c_S) + δ₂·KL(A*_low‖A_S)`
with (α, β, δ₁, δ₂) = (1.0, 0.5, 0.3, 0.2); LoRA rank 16 on all attention projections;
20 epochs, batch 64, lr 2e-4.

---

## Evaluation

```bash
python scripts/reproduce_figures.py --outdir figures
```

Metrics: Macro-F1 (primary), AUROC, 10-bin ECE, Brier, NLL.
Statistical tests: Wilcoxon signed-rank with Bonferroni correction (p < 0.05).
Test windows clustered within patients; mean±std over 5 seeds (T=0.7).

---

## Citation

Citation information will be provided upon paper acceptance.
If you use this code, please check back for the official reference.

---

## License and notices

Code: MIT.
Dataset: MIMIC-III-Ext-PPG is governed by the PhysioNet Credentialed Health Data License —
see [PhysioNet](https://physionet.org/content/mimic-iii-ext-ppg/1.0.0/).

> **Clinical safety.** This is a retrospective research prototype. It is not a medical device
> and must not be used for clinical decision-making. Raw waveforms and PHI must remain local.
> The pipeline sends only non-reversible derived Patch Report fields to LLM APIs.
