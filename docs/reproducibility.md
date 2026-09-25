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

## Aggregate plotting

`scripts/reproduce_figures.py` expects the aggregate CSV files named in the
script. The release does not ship those files because they are derived from
restricted or author-local runs. Recreate them in a local `experiments/`
directory and verify their provenance before generating plots.

## Provider boundary

The reference pipeline serializes Patch Report fields for the role prompts. Raw
waveforms and direct identifiers should remain on the local machine. Provider
retention, training, and human-review settings must be checked against the
active service agreement before any real data is processed.
