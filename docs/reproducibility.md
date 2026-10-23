# Reproducibility

## Offline example

From the repository root:

```bash
python -m pip install -e ".[dev]"
python -m pytest -q
python scripts/run_demo.py
python scripts/run_eval.py --input data/sample_patch_report.json --output outputs/sample_predictions.jsonl
```

The demo constructs synthetic ECG and PPG, derives a heuristic Patch Report and
executes deterministic role responses. Batch processing accepts the included JSON
example or JSONL reports. Neither command trains the encoder or calls a provider.
The tests check software behavior, not diagnostic accuracy.

## Measurement interface

`PatchReport` records quality, rate, interval variability, a P-wave proxy,
spectral summaries and low-confidence beat intervals. The public report builder
uses deterministic signal heuristics. It does not obtain quality or attention
from a trained encoder: its `attention` field is the proxy `1 - confidence`.
The PPG detector returns systolic peaks, used as landmark proxies, rather than
validated systolic onsets. The `lf_hf` field is computed from waveform spectral
power, not an independently validated autonomic measure.

The JSON schema describes the serialized interface. Input validation and role
output validation establish its structure; they do not establish physiological
measurement validity or verify every natural-language interpretation.

## Configuration and providers

`configs/default.yaml` contains demonstration defaults and design settings.
`run_eval.py` consumes its routing/review settings; it uses only the mock backend.
`PhysioSkepticDebate` also accepts a `RoutingConfig` directly.

To use a language model, implement `BaseLLMClient.complete_json` and pass the
client explicitly to `PhysioSkepticDebate`. `OpenAICompatibleClient` is currently
an extension interface, not a working SDK integration. Record the provider,
exact model revision, decoding settings and response failures for any experiment.
Retention settings, including zero-data-retention eligibility, depend on the
provider agreement and are not guaranteed by this repository.

## Training and student model

`encoder.py` implements a PyTorch encoder forward pass. `train_encoder.py` and
`distill_student.py` are recipe entry points without complete training loops;
they raise `NotImplementedError` when invoked for training. The repository does
not provide the Student Llama-1B comparator implementation or its complete
distillation setup. These components require their actual data loader, training
objective, model revision and run configuration before a study reproduction.

## Reproducing the study analyses

Keep each analysis tied to its own dataset and output files. At minimum record:

1. Dataset release, inclusion criteria, label source and patient-level split.
2. Checkpoint ancestry, model revision and training/configuration settings.
3. Prompt versions, review thresholds, provider settings and failed requests.
4. Reference labels, emitted labels, full class probabilities and initial/final
   decisions for the same evaluated windows.
5. Metric definitions, aggregation unit, random seeds and patient-clustered
   uncertainty estimates when computed.

The repository does not currently include a complete mapping from these artifacts
to every manuscript table and figure. See [experiments/](../experiments/README.md)
for the export structure. Do not infer an independent test result from the mock
demo or the existence of training recipe files.

## Source archive

```bash
python scripts/make_release_zip.py --output dist/PhysioSkeptic-source.zip
```

The packager selects tracked source, documentation, prompts, configuration and
public demonstration assets. It excludes Git internals, local outputs, caches
and untracked files. Review the archive before distributing it.
