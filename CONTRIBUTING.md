# Contributing

Use a source checkout and a Python 3.10+ virtual environment:

```bash
python -m pip install -e ".[dev]"
python -m pytest -q
```

For a bug report, include the command, Python/package versions, expected behavior
and a minimal synthetic example. Do not attach patient waveforms, identifying
reports, provider credentials or restricted manifests.

Keep changes to the measurement interface, routing policy and metric definitions
explicit. Add a focused regression test when changing their behavior. Changes to
training or model architecture need corresponding executable configuration and
evaluation; a passing unit test does not replace a benchmark experiment.

The desktop prototype and offline package have separate execution paths. Specify
which one a change affects. Training and provider integrations are welcome, but
their availability should be documented only after implementation.
