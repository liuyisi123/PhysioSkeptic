from __future__ import annotations

import argparse
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]


def save_main(outdir: Path) -> None:
    df = pd.read_csv(ROOT / "experiments/main_results.csv")
    order = ["PatchTST", "GPT-5.2 + CoT", "Debate", "PP+SP", "PhysioSkeptic (GPT-5.2)"]
    sub = df[df.Method.isin(order)].set_index("Method").loc[order]
    fig, ax = plt.subplots(figsize=(5.2, 2.8))
    ax.barh(range(len(sub)), sub["MacroF1"])
    ax.set_yticks(range(len(sub)), [m.replace("PhysioSkeptic (GPT-5.2)", "PhysioSkeptic") for m in sub.index])
    ax.set_xlabel("Macro-F1")
    ax.set_xlim(0.60, 0.92)
    ax.grid(axis="x", alpha=0.25)
    for i, v in enumerate(sub["MacroF1"]):
        ax.text(v + 0.005, i, f"{v:.3f}", va="center", fontsize=8)
    fig.tight_layout()
    fig.savefig(outdir / "main_macro_f1.pdf")
    fig.savefig(outdir / "main_macro_f1.png", dpi=300)
    plt.close(fig)


def save_ablation(outdir: Path) -> None:
    df = pd.read_csv(ROOT / "experiments/ablations.csv")
    fig, ax = plt.subplots(figsize=(6.2, 3.0))
    ax.plot(range(len(df)), df["MacroF1"], marker="o")
    ax.set_xticks(range(len(df)), df["Method"], rotation=45, ha="right", fontsize=7)
    ax.set_ylabel("Macro-F1")
    ax.set_ylim(0.78, 0.90)
    ax.grid(axis="y", alpha=0.25)
    fig.tight_layout()
    fig.savefig(outdir / "ablation_macro_f1.pdf")
    fig.savefig(outdir / "ablation_macro_f1.png", dpi=300)
    plt.close(fig)


def save_robustness(outdir: Path) -> None:
    df = pd.read_csv(ROOT / "experiments/robustness.csv")
    methods = ["PatchTST", "GPT-5.2+CoT", "Debate", "PP+SP", "PhysioSkeptic"]
    for family, sub in df.groupby("Family"):
        fig, ax = plt.subplots(figsize=(5.0, 2.8))
        for m in methods:
            ax.plot(sub["Level"], sub[m], marker="o", label=m)
        ax.set_title(family)
        ax.set_ylabel("Macro-F1")
        ax.set_ylim(0.15, 0.85)
        ax.grid(axis="y", alpha=0.25)
        ax.legend(fontsize=7, ncol=2)
        fig.tight_layout()
        name = family.lower().replace(" ", "_")
        fig.savefig(outdir / f"robustness_{name}.pdf")
        fig.savefig(outdir / f"robustness_{name}.png", dpi=300)
        plt.close(fig)


def save_backbone(outdir: Path) -> None:
    df = pd.read_csv(ROOT / "experiments/backbone_transfer.csv")
    fig, ax = plt.subplots(figsize=(5.6, 3.2))
    y = range(len(df))
    for col, marker in [("Bare", "o"), ("PP_SP", "s"), ("PhysioSkeptic", "^")]:
        ax.scatter(df[col], y, marker=marker, label=col.replace("_", "+"))
    for _, row in df.iterrows():
        yy = df.index[df["Backbone"] == row["Backbone"]][0]
        ax.plot([row["Bare"], row["PP_SP"], row["PhysioSkeptic"]], [yy, yy, yy], alpha=0.4)
    ax.set_yticks(list(y), df["Backbone"])
    ax.set_xlabel("Macro-F1")
    ax.set_xlim(0.65, 0.90)
    ax.grid(axis="x", alpha=0.25)
    ax.legend(fontsize=8)
    fig.tight_layout()
    fig.savefig(outdir / "backbone_transfer.pdf")
    fig.savefig(outdir / "backbone_transfer.png", dpi=300)
    plt.close(fig)


def save_deployment(outdir: Path) -> None:
    df = pd.read_csv(ROOT / "experiments/routing_deployment.csv")
    sub = df.dropna(subset=["Latency_ms", "F1"])
    fig, ax = plt.subplots(figsize=(5.2, 3.2))
    ax.scatter(sub["Latency_ms"], sub["F1"], s=(sub["Throughput_per_min"].clip(10, 200) * 2))
    for _, r in sub.iterrows():
        ax.text(r["Latency_ms"] * 1.03, r["F1"], r["Policy"], fontsize=7, va="center")
    ax.set_xscale("log")
    ax.set_xlabel("Latency (ms, log scale)")
    ax.set_ylabel("Macro-F1")
    ax.grid(alpha=0.25)
    fig.tight_layout()
    fig.savefig(outdir / "deployment_latency_f1.pdf")
    fig.savefig(outdir / "deployment_latency_f1.png", dpi=300)
    plt.close(fig)


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--outdir", default="figures")
    args = p.parse_args()
    outdir = Path(args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)
    save_main(outdir)
    save_ablation(outdir)
    save_robustness(outdir)
    save_backbone(outdir)
    save_deployment(outdir)
    print(f"Figures written to {outdir}")


if __name__ == "__main__":
    main()
