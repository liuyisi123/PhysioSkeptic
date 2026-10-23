"""Reserved Student Llama-1B entry point; the distillation loop is not included."""

from __future__ import annotations

import argparse


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--teacher-jsonl", required=True)
    parser.add_argument("--outdir", required=True)
    return parser.parse_args()


def main() -> None:
    parse_args()
    raise NotImplementedError(
        "Student Llama-1B distillation is not implemented in this public entry point. "
        "See docs/reproducibility.md for the required model and training configuration."
    )


if __name__ == "__main__":
    main()
