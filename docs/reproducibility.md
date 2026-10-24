# Reproducibility

This guide identifies what can be run from the public checkout and which
resources are needed to reproduce a study analysis. For installation and
input formats, see [Quick start](../README.md#quick-start) and [Usage](usage.md).

## Software coverage

| Resource | Current implementation |
| --- | --- |
| Signal measurements and Patch Reports | Local NumPy/SciPy processing with a JSON schema and synthetic example |
| PhysioPatch representation | PyTorch encoder modules for temporal/frequency processing and quality-weighted fusion |
| Route selection | Executable thresholds and challenge-count rules in `routing.py` |
| Agent review | Role orchestration with YAML templates and a deterministic mock client |
| External language model client | Adapter interface; `complete_json` requires implementation for the selected provider |
| Encoder training and student distillation | Entry-point skeletons that document inputs/settings; complete training loops and data loaders are not included |
| Browser demonstration | Interactive synthetic visualisation; no encoder execution or model calls |
| Unit tests | Patch Report construction/validation, route boundaries and challenge allocation |

Run the local tests with:

```bash
python -m pytest -q
```

## Analysis-specific resources

Reproducing a numerical result requires the corresponding dataset selection,
patient-level partition, fitted checkpoint, role instructions, model settings
and evaluation outputs. The public mock example does not supply those
study-specific resources. Aggregate benchmark files and the full set of paper
plotting scripts are not currently included in this repository.

The YAML files in [`prompts/`](../prompts/) define the public reference
implementation. Their payload and output fields differ from the experimental
instructions reproduced in the manuscript's Supplementary Information. The
default model identifier in [`configs/default.yaml`](../configs/default.yaml)
also describes a different setup from the paired Qwen comparison. These files
should be matched to the intended analysis before an experiment is run; they
are not interchangeable experimental configurations.

The training entry points
[`train_encoder.py`](../src/physioskeptic/train_encoder.py) and
[`distill_student.py`](../src/physioskeptic/distill_student.py) create configuration
notes rather than executing complete training. The available encoder modules
can be inspected independently of those entry points.

## Source data

Access source recordings through the dataset providers:

- [MIMIC-III-Ext-PPG, version 1.0.0](https://doi.org/10.13026/nmwb-6h34)
- [MC-MED publication and data-access information](https://doi.org/10.1038/s41597-025-05419-5)

The checked-in report is synthetic. Source waveform access, data-use terms
and any sharing restrictions remain governed by the respective datasets.
Keep patient-level materials and credentials outside a public contribution.

## Versions and execution records

The source package currently declares version `0.1.0` in `pyproject.toml`.
GitHub also has a historical `v1.0.0` release tag. Those identifiers refer to
different snapshots and should not be treated as equivalent. For a software
issue or experiment, record the checkout revision alongside the relevant
configuration and dependency versions.

For a model run, retain its dataset release and partition, checkpoint,
prompt files, model identifier, decoding settings and evaluation command.
Record the requested route separately from the roles actually executed when
analysing review allocation.
