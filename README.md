# PhysioSkeptic

**Interpreting multimodal physiological signals through sceptical reasoning with language model agents**

<p align="center">
  <img src="assets/physioskeptic-logo.svg" alt="PhysioSkeptic" width="620">
</p>

[![Tests](https://github.com/liuyisi123/PhysioSkeptic/actions/workflows/tests.yml/badge.svg)](https://github.com/liuyisi123/PhysioSkeptic/actions/workflows/tests.yml)
[![Python](https://img.shields.io/badge/python-3.10%2B-596F8B)](pyproject.toml)
[![License: MIT](https://img.shields.io/badge/license-MIT-9184A5)](LICENSE)

[Overview](#overview) · [Quick start](#quick-start) · [Examples](#examples) · [Implementation](#implementation) · [Reproducibility](docs/reproducibility.md)

## Overview

PhysioSkeptic studies how language model agents can inspect and revise physiological
interpretations using identifiable measurements. Its central interface is a **Patch
Report**: a structured account of signal features, beat indices, time intervals and
measurement quality. Proposer, Checker, Skeptic, Advocate and Arbiter roles use this
shared report to formulate an interpretation, examine disagreements and revise the
final judgement. Signal quality determines the depth of review.

This repository provides ECG–PPG signal utilities, a PyTorch encoder, Patch Report
schemas, role prompts and an executable offline demonstration. The demonstration
uses synthetic signals and deterministic role responses. The implementation status
of training, provider integration and study reproduction is listed below.

## Quick start

Python 3.10 or newer is required. Run these commands from a source checkout:

```bash
git clone https://github.com/liuyisi123/PhysioSkeptic.git
cd PhysioSkeptic
python -m venv .venv
```

Activate the environment with `source .venv/bin/activate` on Linux/macOS, or
`.venv\Scripts\Activate.ps1` in Windows PowerShell. Then run:

```bash
python -m pip install -e ".[dev]"
python -m pytest -q
python scripts/run_demo.py
```

The demo prints a synthetic Patch Report, selected route, ordered role transcript
and final review flag. It runs on CPU without a dataset download or API key.

## Examples

### Follow an agent review

<p align="center">
  <img src="assets/demo/physioskeptic_reasoning_trace.gif" alt="Illustrative synthetic Patch Report and agent review" width="900">
</p>

The animation illustrates a synthetic review. Open [the routing animation](assets/demo/physioskeptic_demo.gif)
or [the browser demo](demo/index.html) for the quality thresholds and challenge
budget. The browser page can also be opened directly from a local checkout.

### Process the included report

```bash
python scripts/run_eval.py --input data/sample_patch_report.json --output outputs/sample_predictions.jsonl
```

The input can be one JSON report or a JSONL file containing one report per line.
The script validates each report and writes the route and final mock response.
`--config configs/default.yaml` selects the routing and review thresholds.
Despite its legacy filename, `run_eval.py` is a report-processing demonstration;
it does not compute study benchmark metrics or invoke a trained language model.

### Use the Python API

```python
import json
from pathlib import Path

from physioskeptic.debate import PhysioSkepticDebate
from physioskeptic.llm_clients import MockLLMClient

report = json.loads(Path("data/sample_patch_report.json").read_text(encoding="utf-8"))
engine = PhysioSkepticDebate(MockLLMClient(), prompt_dir="prompts")
result = engine.run(report)
print(result.route.value)
print(result.final)
```

## Implementation

| Component | Location | Available functionality |
|---|---|---|
| Signal processing | [signal_processing.py](src/physioskeptic/signal_processing.py) | Landmark proxies, beat patches, rate and spectral summaries |
| Measurement report | [patch_report.py](src/physioskeptic/patch_report.py), [schema](data/patch_report.schema.json) | Report generation and JSON validation; the demo uses heuristic quality and P-wave features |
| Physiological encoder | [encoder.py](src/physioskeptic/encoder.py) | PyTorch temporal and frequency paths, quality fusion and query projection; the offline demo does not load encoder weights |
| Agent review | [debate.py](src/physioskeptic/debate.py), [prompts](prompts/) | Three review routes and schema-validated role messages |
| Routing | [routing.py](src/physioskeptic/routing.py) | Configurable confidence and quality thresholds, plus challenge count |
| Metrics and perturbations | [metrics.py](src/physioskeptic/metrics.py), [corruptions.py](src/physioskeptic/corruptions.py) | Classification/calibration functions and signal corruption utilities |
| Language model backend | [llm_clients.py](src/physioskeptic/llm_clients.py) | Working deterministic mock; the provider class is an extension interface |
| Encoder training and Student Llama-1B | [training notes](docs/reproducibility.md#training-and-student-model) | Existing entry points describe the recipe; complete training and Llama distillation loops are not included |

The three routes are Fast (Proposer → Checker → Arbiter), Standard (adds Skeptic)
and Deep (also adds Advocate). All retain the Checker response in the transcript.
See [the configuration](configs/default.yaml) for the threshold values and
[the reproducibility guide](docs/reproducibility.md) for the distinction between
this public implementation and the study experiments.

## Data and experiments

The files in [data/](data/) contain a schema and a synthetic report. Access
MIMIC-III-Ext-PPG through [PhysioNet](https://physionet.org/content/mimic-iii-ext-ppg/1.0.0/)
and follow the source terms for each dataset. Data-access permissions do not
automatically authorize sending derived reports to an external provider.

For a study reproduction, record the patient-level split, model and checkpoint,
prompt/configuration revision, decoding settings and per-window predictions for
each comparison. The [experiment guide](experiments/README.md) describes the
required outputs. Synthetic demos and unit tests are separate from benchmark
performance.

## Optional desktop interface

```bash
python -m pip install -r physioskeptic_ui/requirements.txt
python physioskeptic_ui/main.py
```

The [desktop interface](physioskeptic_ui/README.md) is a separate prototype for
signal import and transcript inspection. Its demo displays and API adapters are
not the command-line research pipeline. Use Mock / Demo to explore it offline.

## Repository structure

```text
src/physioskeptic/    Signal processing, encoder, reports, routing and agents
prompts/             Five role templates and output schemas
configs/             Configuration definitions
data/                Report schema and synthetic example
scripts/             Offline demo, report processing and source packaging
tests/               Unit and integration tests
docs/                Reproducibility and implementation notes
demo/                Standalone browser demonstration
physioskeptic_ui/    Optional desktop prototype
```

## Development and contact

Run `python -m pytest -q` before submitting a change. See
[CONTRIBUTING.md](CONTRIBUTING.md) for setup, tests and issue reports. Please
report software problems through [GitHub Issues](https://github.com/liuyisi123/PhysioSkeptic/issues)
without including patient records or credentials.

The source code is distributed under the [MIT License](LICENSE). Dataset and
third-party model terms apply separately.
