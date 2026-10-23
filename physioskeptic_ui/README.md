# Desktop prototype

Run from the repository root:

```bash
python -m pip install -r physioskeptic_ui/requirements.txt
python physioskeptic_ui/main.py
```

Use **Mock / Demo** for offline exploration of waveform import, report display
and agent transcripts. This application has a separate heuristic pipeline and
provider adapters; it does not load the research encoder or Student Llama-1B.
Demo performance values and illustrative confidence intervals are interface
fixtures, not evaluation results. Do not use them as study statistics.

Provider calls can transmit the displayed report to the configured service.
Use only data authorized for that service. Credentials are used for the current
session or supplied through environment variables, rather than saved in local
application preferences. This repository does not guarantee current provider
pricing or retention terms.

If an earlier version saved a key in application preferences, remove that legacy
entry using your operating system's settings store. This update stops reading and
writing those keys; it does not modify existing local preferences automatically.
