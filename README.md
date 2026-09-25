# PhysioSkeptic

PhysioSkeptic is a research framework for ECG--PPG rhythm classification with
beat-level signal-quality evidence and adaptive skeptical reasoning. The
repository separates local signal processing from the serialized Patch Report
sent to an optional language-model backend.

> Research prototype. This repository is not a medical device, diagnostic
> system, or source of clinical advice. The synthetic demo is an API and
> workflow demonstration, not a clinical prediction.

## What is included

The release contains the reproducible software contracts used by the paper:

- cardiac landmark detection and deterministic Patch Report construction;
- PhysioPatch's dual-path encoder and SQI head interfaces;
- FAST, STANDARD, and DEEP routing with the paper's threshold policy;
- Proposer, Checker, Skeptic, Advocate, and Arbiter prompt contracts;
- a mock-backend CLI and a browser-only interactive demo;
- unit tests for Patch Report validation, routing boundaries, and challenge count;
- plotting utilities that consume checked aggregate tables when those tables are
  available locally.

Raw MIMIC-III-Ext-PPG or MC-MED files, patient-level manifests, checkpoints,
API credentials, and private provider responses are intentionally excluded.

## Start here

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -e ".[dev]"
python -m pytest -q
python scripts\run_demo.py
```

The CLI demo creates a fully synthetic 30-second ECG--PPG window and runs the
mock five-role pipeline. It requires no API key and prints the Patch Report,
route, structured transcript, and final review flag.

For a visual walkthrough, open [`demo/index.html`](demo/index.html) directly in
a browser. The page is self-contained and lets you change SQI, proposer
confidence, and conflict severity while showing the resulting route and
challenge budget. It never loads patient data or calls an external service.

## Repository map

```text
PhysioSkeptic/
├── src/physioskeptic/       # package: signal, encoder, report, routing, debate
├── prompts/                 # five JSON-output role contracts
├── configs/default.yaml     # paper-aligned dimensions and thresholds
├── data/                    # schema and synthetic Patch Report only
├── demo/                    # self-contained browser demo and notes
├── scripts/                 # demo, evaluation, release, and plot utilities
├── tests/                   # unit tests
├── docs/                    # data and reproducibility boundaries
├── experiments/             # local-only aggregate-table contract
└── physioskeptic_ui/        # optional PySide6 desktop interface
```

The package is deliberately small: `patch_report.py` forms the evidence
interface, `routing.py` implements the SQI gates, and `debate.py` orchestrates
the role sequence. `llm_clients.py` provides the mock and provider adapters;
provider calls are opt-in.

## Running the software

### Synthetic CLI

```powershell
python scripts\run_demo.py
```

### Patch Report batch evaluation

```powershell
python scripts\run_eval.py `
  --input C:\path\to\patch_reports.jsonl `
  --output outputs\predictions.jsonl
```

The input must contain validated Patch Report JSON objects. Keep real outputs
outside the repository; `outputs/` is ignored by Git.

### Optional provider backend

The provider adapter accepts an API-compatible client, but credentials must be
provided through a local secret manager or environment variable. Never place a
key in `configs/default.yaml`, prompts, notebooks, logs, or source files. Only
the derived Patch Report should cross the provider boundary; raw waveforms and
identifiers should remain local.

### Optional desktop UI

The PySide6 application is kept separate from the research package:

```powershell
python -m pip install -r physioskeptic_ui\requirements.txt
python physioskeptic_ui\main.py
```

Use the Mock / Demo path for a no-credential smoke test. The UI is an
experimental convenience layer and is not required for the paper pipeline.

## Data and evaluation boundaries

MIMIC-III-Ext-PPG and MC-MED are credentialed or restricted resources. Obtain
them directly from their approved distribution channels and keep all waveform
files, manifests, and derived patient-level artifacts outside this repository.
The checked-in JSON schema and sample report are synthetic. See
[`data/README.md`](data/README.md) and
[`docs/reproducibility.md`](docs/reproducibility.md) before running an
evaluation.

The figure helper in `scripts/reproduce_figures.py` expects paper aggregate
tables under `experiments/` that are not included in this release. This keeps
restricted or author-local evaluation artifacts out of the repository while
preserving the plotting entry point and its expected file contract.

## Figures and manuscript

The ICLR-27 LaTeX source, combined PDF, bibliography audit, and migration log
are delivered alongside this code under `../../ICLR2027/`. The repository
contains the executable code and the synthetic demo; the manuscript delivery
contains the paper assets and their provenance record.

## Testing and release hygiene

```powershell
python -m pytest -q
python -m build                 # optional package build
git status --short
```

Before committing, verify that no raw waveform, credential, model checkpoint,
provider response, or generated patient artifact is staged. The `.gitignore`
contains explicit rules for these classes of files, but the final review is
still manual.

## License and citation

Code is released under the MIT License. Dataset, checkpoint, and provider
licenses remain separate. Citation metadata is in [`CITATION.cff`](CITATION.cff);
the final paper citation should replace the placeholder bibliographic record
before public release.
