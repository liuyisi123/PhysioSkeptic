from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from physioskeptic.debate import PhysioSkepticDebate
from physioskeptic.llm_clients import MockLLMClient
from physioskeptic.patch_report import validate_patch_report
from physioskeptic.routing import RoutingConfig


def read_reports(path: Path):
    """Read a single JSON report or a stream of JSONL reports."""
    with path.open(encoding="utf-8") as handle:
        if path.suffix.lower() == ".json":
            yield json.load(handle)
        else:
            for line in handle:
                if line.strip():
                    yield json.loads(line)


def main() -> None:
    p = argparse.ArgumentParser()
    p.description = "Process Patch Reports with the offline mock backend."
    p.add_argument("--config", default=str(ROOT / "configs/default.yaml"))
    p.add_argument("--input", required=True, help="One JSON report or JSONL reports")
    p.add_argument("--output", default="outputs/predictions.jsonl")
    args = p.parse_args()

    config = yaml.safe_load(Path(args.config).read_text(encoding="utf-8"))
    if config.get("llm", {}).get("backend", "mock") != "mock":
        p.error("This command supports only the mock backend")
    routing = config.get("routing", {})
    route_config = RoutingConfig(
        **{
            key: routing[key]
            for key in ("fast_confidence", "fast_quality", "deep_quality", "deep_confidence")
            if key in routing
        }
    )
    engine = PhysioSkepticDebate(
        MockLLMClient(),
        ROOT / "prompts",
        review_threshold=routing.get("review_confidence", 0.70),
        routing_config=route_config,
    )
    out = Path(args.output)
    if out.resolve() == Path(args.input).resolve():
        p.error("Input and output must be different files")
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w", encoding="utf-8") as g:
        for report in read_reports(Path(args.input)):
            validate_patch_report(report, ROOT / "data/patch_report.schema.json")
            res = engine.run(report)
            g.write(
                json.dumps(
                    {
                        "sample_id": report.get("sample_id"),
                        "route": res.route.value,
                        "final": res.final,
                    }
                )
                + "\n"
            )
    print(f"Wrote {out}")


if __name__ == "__main__":
    main()
