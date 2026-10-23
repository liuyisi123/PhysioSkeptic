"""Reserved encoder training entry point; the complete training loop is not included."""

from __future__ import annotations

import argparse


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", default="configs/default.yaml")
    parser.add_argument("--train-jsonl", required=True)
    parser.add_argument("--valid-jsonl", required=True)
    parser.add_argument("--outdir", required=True)
    return parser.parse_args()


def main() -> None:
    parse_args()
    raise NotImplementedError(
        "Encoder training is not implemented in this public entry point. "
        "Supply the study data loader, objectives and training loop; "
        "see docs/reproducibility.md."
    )


if __name__ == "__main__":
    main()
