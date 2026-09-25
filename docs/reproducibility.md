# Reproducibility boundary

This release distinguishes runnable software contracts from restricted
evaluation artifacts.

## Runnable without restricted data

- `python scripts/run_demo.py` builds a synthetic ECG--PPG window and runs the
  mock five-role transcript.
- `python -m pytest -q` checks Patch Report schema validation, SQI bounds,
  routing thresholds, and challenge-count behavior.
- `demo/index.html` visualizes the routing contract in a browser.

## Requires local approved data

Full waveform evaluation requires an approved local copy of
MIMIC-III-Ext-PPG and the corresponding preprocessing manifests. MC-MED is used
only for the transfer and weak-label audits described in the paper. These
resources must remain outside Git, together with patient-level splits,
provider responses, checkpoints, and logs.

## Aggregate evaluation outputs

The release does not bundle paper plotting code or aggregate result files.
Author-local tables belong in `experiments/` and remain outside version control;
the directory README records the expected contract. For a validated JSONL of
Patch Reports, `scripts/run_eval.py` produces deterministic mock-backend
predictions without requiring restricted waveforms or model checkpoints.

## Provider boundary

The reference pipeline serializes Patch Report fields for the role prompts. Raw
waveforms and direct identifiers should remain on the local machine. Provider
retention, training, and human-review settings must be checked against the
active service agreement before any real data is processed.
