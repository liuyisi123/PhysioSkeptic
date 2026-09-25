# PhysioSkeptic

<p align="center">
  <img src="assets/physioskeptic-logo.svg" alt="PhysioSkeptic" width="620">
</p>

<p align="center">
  <a href=".github/workflows/tests.yml"><img src="https://img.shields.io/badge/CI-unit%20tests-0e948d.svg" alt="CI unit tests"></a>
  <img src="https://img.shields.io/badge/release-v0.1.0-2563eb.svg" alt="release v0.1.0">
  <img src="https://img.shields.io/badge/license-MIT-0f766e.svg" alt="MIT license">
  <img src="https://img.shields.io/badge/python-3.10%2B-3776ab.svg" alt="Python 3.10 or newer">
  <img src="https://img.shields.io/badge/status-research%20prototype-d97706.svg" alt="research prototype">
</p>

> Beat-level signal-quality evidence for ECG--PPG rhythm classification and
> adaptive skeptical reasoning.

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
- a self-contained synthetic GIF walkthrough of the evidence-to-review flow;
- unit tests for Patch Report validation, routing boundaries, and challenge count;

The repository does not contain paper figures, plotting scripts, raw
MIMIC-III-Ext-PPG or MC-MED files, patient-level manifests, checkpoints, API
credentials, or private provider responses.

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

For a visual walkthrough, open the synthetic
[`demo GIF`](assets/demo/physioskeptic_demo.gif). For an interactive version,
open [`demo/index.html`](demo/index.html) directly in a browser. The page is
self-contained and lets you change SQI, proposer confidence, and conflict
severity while showing the resulting route and challenge budget. Neither demo
loads patient data or calls an external service.

## Demo and paper trace

The browser demo is the quickest way to inspect the paper's evidence contract:
adjust the synthetic SQI and conflict state, then follow the route, challenge
budget, and review flag through the five roles. It is deliberately illustrative
and deterministic; the executable mock pipeline is the authoritative local
smoke test.

| Paper concept | Code entry point |
| --- | --- |
| Patch Report schema and validation | [patch_report.py](src/physioskeptic/patch_report.py), [patch_report.schema.json](data/patch_report.schema.json) |
| FAST / STANDARD / DEEP routing | [routing.py](src/physioskeptic/routing.py) |
| Five-role transcript | [debate.py](src/physioskeptic/debate.py), [prompts](prompts/) |
| Synthetic end-to-end run | [run_demo.py](scripts/run_demo.py) |
| Aggregate results contract | [experiments README](experiments/README.md) |

## Repository map

```text
PhysioSkeptic/
├── src/physioskeptic/       # package: signal, encoder, report, routing, debate
├── prompts/                 # five JSON-output role contracts
├── configs/default.yaml     # paper-aligned dimensions and thresholds
├── data/                    # schema and synthetic Patch Report only
├── demo/                    # self-contained browser demo and notes
├── scripts/                 # demo, evaluation, and release utilities
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

The checked-in JSON schema and sample report are synthetic interface fixtures,
not study data. Author-local aggregate tables, figures, and evaluation outputs
remain outside this repository.

## Figures and manuscript

The ICLR-27 LaTeX source, combined PDF, bibliography audit, and migration log
are delivered separately from this software repository. This repository keeps
only the executable contracts and synthetic demonstrations needed to inspect
the method boundary.

## Testing and release hygiene

```powershell
python -m pytest -q
python -m build                 # optional package build
git status --short
```

Before committing, verify that no raw waveform, credential, model checkpoint,
provider response, paper figure, or generated patient artifact is staged. The
`.gitignore` contains explicit rules for these classes of files, but the final
review is still manual.

The release review is intentionally conservative: tracked files are limited to
source code, synthetic schemas/examples, prompts, tests, documentation, and
non-sensitive UI assets. Restricted waveforms, patient-level manifests,
checkpoints, provider transcripts, and credentials remain excluded from Git.

## License and citation

Code is released under the MIT License. Dataset, checkpoint, and provider
licenses remain separate. Citation metadata is in [`CITATION.cff`](CITATION.cff);
the final paper citation should replace the placeholder bibliographic record
before public release.
