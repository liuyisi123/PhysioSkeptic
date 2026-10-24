# Usage

Run commands from the repository root after following the
[installation instructions](../README.md#quick-start).

## Synthetic signal demonstration

```bash
python scripts/run_demo.py
```

The script creates 30-second ECG and PPG signals at 125 Hz, builds a Patch
Report and passes it through `PhysioSkepticDebate` using `MockLLMClient`.
It writes one JSON object to standard output:

| Field | Contents |
| --- | --- |
| `patch_report` | Signal summaries, event intervals, quality and consistency fields |
| `route` | Selected `FAST`, `STANDARD` or `DEEP` route |
| `transcript` | Role messages retained by the orchestrator |
| `final` | Rhythm, confidence, review flag and reasoning summary |

The mock client returns deterministic example responses. It does not invoke an
external model or evaluate a trained rhythm classifier.

## Python interface

The packaged interface accepts a report dictionary. Use the checked-in
synthetic report to explore the review workflow:

```python
import json
from pathlib import Path

from physioskeptic import MockLLMClient, PhysioSkepticDebate

report = json.loads(Path("data/sample_patch_report.json").read_text())
engine = PhysioSkepticDebate(MockLLMClient(), Path("prompts"))
result = engine.run(report)

print(result.route.value)
print(result.final["rhythm"])
print(result.final["review_recommended"])
```

Inspect the [report schema](../data/patch_report.schema.json) and
[role templates](../prompts/) when preparing a different input. The example
loads templates from the source checkout rather than from an installed wheel.

## JSONL batch processing

`scripts/run_eval.py` reads one report object per line and writes one result
object per line. To create a one-record synthetic input:

```bash
python -c "import json; from pathlib import Path; Path('outputs').mkdir(exist_ok=True); d=json.loads(Path('data/sample_patch_report.json').read_text()); Path('outputs/reports.jsonl').write_text(json.dumps(d)+'\n')"
python scripts/run_eval.py --input outputs/reports.jsonl --output outputs/predictions.jsonl
```

Each result contains `sample_id`, `route` and `final`. The batch script uses
`MockLLMClient`, just like the single-example API. It is useful for exercising
the report format and output handling, not reproducing benchmark metrics.
Although its parser accepts `--config`, the current script does not apply that
argument; routing follows the implementation defaults in
[`routing.py`](../src/physioskeptic/routing.py).

## Language model backends

Implement `BaseLLMClient.complete_json(role, system, user, schema)` to connect a
provider. The orchestrator supplies a role name, formatted messages and the
role's declared JSON schema, and expects a response dictionary. Validate the
response against that schema in the client. The current `_call` method passes
the schema to the client but does not validate the returned object itself.

`OpenAICompatibleClient` currently defines the adapter interface and raises a
`RuntimeError` when called. It is not a configured network client. Use the
requirements and data-processing terms of the provider actually selected;
credentials belong in environment variables or a local secret manager, not
in prompts or configuration files.

The [reference configuration](../configs/default.yaml) describes one setup;
changing it does not automatically configure the mock CLI or batch scripts.
For a study run, connect and record the model, decoding settings, prompts and
data partition used by that run. See [reproducibility](reproducibility.md).

## Desktop interface

The optional PySide6 application is installed separately:

```bash
python -m pip install -r physioskeptic_ui/requirements.txt
python physioskeptic_ui/main.py
```

Its dependencies and provider integrations are separate from the core
`PhysioSkepticDebate` example. The browser demo offers an installation-free
way to inspect route selection and role interactions.
