# Report format and example

- `patch_report.schema.json`: JSON schema for the public measurement interface.
- `sample_patch_report.json`: synthetic report for the offline examples.

Validate a report with `validate_patch_report(report, schema_path)`, then use
`scripts/run_eval.py` to process JSON or JSONL reports with the mock backend.
Beat indices refer to `beat_confidences`; time intervals are in seconds, rates
in beats per minute and quality values on a zero-to-one scale.

MIMIC-III-Ext-PPG is available through
[PhysioNet](https://physionet.org/content/mimic-iii-ext-ppg/1.0.0/) subject to its
credentialed access conditions. Obtain MC-MED from its source distributor and
follow its current access terms. Keep source waveforms, local record identifiers
and patient split files outside this repository. Review the applicable data
agreement before sending a derived report to any remote service.
