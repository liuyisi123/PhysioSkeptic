# Contributing

Bug reports, documentation improvements and focused code contributions are
welcome. Start with the [quick start](README.md#quick-start) and
[usage guide](docs/usage.md) to run the synthetic example.

## Reporting an issue

Include the command or API call, Python and operating-system versions, the
checkout revision, expected behaviour and the error message. A small example
based on `data/sample_patch_report.json` is preferable to a private dataset.
Remove credentials, patient information and private provider responses before
attaching logs or screenshots.

For manuscript or study-design enquiries, contact
[Jian Liu](mailto:jianliu@cuhk.edu.hk). Public GitHub issues are for reproducible
software questions and documentation changes.

## Proposing a change

1. Create a branch for one focused change.
2. Add or update a test if behaviour changes.
3. Run `python -m pytest -q` and `python scripts/check_docs.py`.
4. Explain the change and its effect on existing inputs, outputs or defaults
   in the pull request.

Keep measurement definitions, role schemas and routing rules explicit.
Distinguish changes to the public reference implementation from changes to a
particular study configuration. Do not attach restricted waveforms or trained
artifacts to a pull request.
