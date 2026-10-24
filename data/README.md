# Patch Report data

This directory contains the input specification and a synthetic example for
the public review workflow.

| File | Purpose |
| --- | --- |
| [patch_report.schema.json](patch_report.schema.json) | JSON schema for the report fields |
| [sample_patch_report.json](sample_patch_report.json) | Synthetic report used in the Python and batch examples |

Reports include recording-level measurements, signal-quality summaries,
cross-modal consistency fields and indexed low-confidence intervals.
The [usage guide](../docs/usage.md) shows how to pass a report to the agent
workflow and how to prepare a JSONL batch.

## Source datasets

The study uses [MIMIC-III-Ext-PPG](https://doi.org/10.13026/nmwb-6h34) and separate
[MC-MED analyses](https://doi.org/10.1038/s41597-025-05419-5). Obtain recordings
directly from their providers under the applicable access and licence terms.
Source waveforms, patient-level manifests and model checkpoints are not
distributed in this directory. See [reproducibility](../docs/reproducibility.md)
for analysis-specific requirements.
