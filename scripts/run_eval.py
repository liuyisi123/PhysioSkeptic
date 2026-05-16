from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from physioskeptic.debate import PhysioSkepticDebate
from physioskeptic.llm_clients import MockLLMClient


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--config", default="configs/default.yaml")
    p.add_argument("--input", required=True, help="JSONL Patch Reports")
    p.add_argument("--output", default="outputs/predictions.jsonl")
    args = p.parse_args()

    engine = PhysioSkepticDebate(MockLLMClient(), ROOT / "prompts")
    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    with open(args.input) as f, open(out, "w") as g:
        for line in f:
            if not line.strip():
                continue
            report = json.loads(line)
            res = engine.run(report)
            g.write(json.dumps({"sample_id": report.get("sample_id"), "route": res.route.value, "final": res.final}) + "\n")
    print(f"Wrote {out}")


if __name__ == "__main__":
    main()
