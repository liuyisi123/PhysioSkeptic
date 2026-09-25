# PhysioSkeptic browser demo

Open `index.html` in a browser. No server, package installation, patient data,
or API key is required.

The demo is intentionally a deterministic workflow visualizer. It exposes the
same routing thresholds as the reference implementation and renders an
illustrative Patch Report trace. It does not run the encoder, call an LLM, or
claim useful medical predictions.

For the executable synthetic pipeline, run `python scripts/run_demo.py` from
the repository root.
