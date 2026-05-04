"""Plot layer-migration probe AUC with seed min/max bands."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

COLORS = {
    "base": "#888888",
    "control_sft": "#1f77b4",
    "honest_sft": "#2ca02c",
    "control_corrupt": "#d62728",
    "honest_corrupt": "#ff7f0e",
}


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def stage_condition(raw: dict[str, Any]) -> tuple[str, str]:
    stage = str(raw.get("stage") or "unknown")
    condition = str(raw.get("condition") or "unknown")
    cell = str(raw.get("cell") or "")
    if condition == "unknown" and "__" in cell:
        _stage, condition = cell.split("__", 1)
    return stage, condition


def plot_aggregate(
    ax: Any, stage: str, condition: str, by_layer: dict[str, Any]
) -> None:
    layers = sorted((int(layer), row) for layer, row in by_layer.items())
    if not layers:
        return
    xs = [layer for layer, _ in layers]
    means = [row["mean"] for _, row in layers]
    lows = [row["min"] for _, row in layers]
    highs = [row["max"] for _, row in layers]
    color = COLORS[stage]
    ax.plot(xs, means, linewidth=2.5, marker="o", color=color, label=f"{stage} mean")
    ax.fill_between(
        xs, lows, highs, color=color, alpha=0.18, label=f"{stage} seed band"
    )


def plot_single(ax: Any, raw: dict[str, Any], condition: str) -> None:
    stage, raw_condition = stage_condition(raw)
    if raw_condition != condition or raw.get("status") == "degenerate":
        return
    layers = sorted(
        (int(layer), row) for layer, row in raw.get("per_layer", {}).items()
    )
    if not layers:
        return
    xs = [layer for layer, _ in layers]
    ys = [row["auc"] for _, row in layers]
    ax.plot(
        xs,
        ys,
        linewidth=1.8,
        marker=".",
        color=COLORS.get(stage, "#666666"),
        label=stage,
    )


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--seed-aggregated", type=Path, required=True)
    parser.add_argument("--single-results", nargs="*", type=Path, default=[])
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--title", default="Deception-feature probe AUC by layer")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    payload = load_json(args.seed_aggregated)
    if payload.get("family_source") != "infamily":
        raise ValueError(
            "seed_aggregated family_source must be 'infamily' for headline plot; "
            f"got {payload.get('family_source')!r}"
        )
    try:
        import matplotlib.pyplot as plt
    except ModuleNotFoundError as exc:
        raise SystemExit(f"matplotlib required for {__file__}: missing {exc.name}")

    singles = [load_json(path) for path in args.single_results]
    conditions = sorted(
        {
            condition
            for by_condition in payload["stages"].values()
            for condition in by_condition
        }
        | {stage_condition(raw)[1] for raw in singles}
    )
    fig, axes = plt.subplots(
        1,
        len(conditions),
        figsize=(max(8, 5 * len(conditions)), 5),
        sharey=True,
        squeeze=False,
    )
    for ax, condition in zip(axes[0], conditions):
        for raw in singles:
            plot_single(ax, raw, condition)
        for stage, by_condition in payload["stages"].items():
            if condition in by_condition:
                plot_aggregate(ax, stage, condition, by_condition[condition])
        ax.axhline(0.5, color="k", linestyle="--", alpha=0.3, label="chance")
        ax.set_title(condition)
        ax.set_xlabel("Layer index")
        ax.set_ylim(0.4, 1.02)
        ax.grid(alpha=0.3)
        ax.legend(loc="best", frameon=False)
    axes[0][0].set_ylabel("Probe AUC")
    fig.suptitle(args.title)
    fig.tight_layout()
    args.out.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(args.out, dpi=200)
    plt.close(fig)
    print(f"[plot-layer-migration-seeds] wrote {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
