# Experiment outputs

The offline examples are separate from study evaluation. A reproducible experiment
export should associate each comparison with the following files:

| Artifact | Required contents |
|---|---|
| Run configuration | Dataset release, split designation, seed, checkpoint, method, model revision and decoding settings |
| Predictions | Local window identifier, reference label, emitted label, full class-probability vector and failure status |
| Decision trace | Initial/final judgement, Checker findings, route and role messages for the same window |
| Metric summary | Metric formula, class order, denominator, aggregation unit and uncertainty method |
| Display mapping | Manuscript table/figure identifier and the exported summary used to generate it |

Keep restricted record identifiers and source data in the authorized evaluation
environment. Share aggregate tables only when their provenance and redistribution
terms permit it. If analyses use different datasets or endpoints, export them
separately rather than combining their denominators.

`scripts/run_eval.py` writes mock responses from input reports. It is not the
study benchmark runner, and its outputs should not be relabelled as trained-model
results. Complete study run configurations and result-to-display exports are not
currently distributed in this directory.
