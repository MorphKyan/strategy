from __future__ import annotations

from pathlib import Path

import pandas as pd

from src.platform_core.metrics import read_csv_or_empty


def render_platform_charts(result_dir: str | Path, output_dir: str | Path | None = None) -> list[Path]:
    """Render low-coupling charts from platform CSV artifacts.

    The module intentionally depends only on persisted run artifacts, so it can be
    reused by experiment reports, sensitivity reports, or ad hoc runs.
    """

    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    result_dir = Path(result_dir)
    output_dir = Path(output_dir) if output_dir else result_dir / "charts"
    output_dir.mkdir(parents=True, exist_ok=True)

    nav = read_csv_or_empty(result_dir / "nav.csv")
    positions = read_csv_or_empty(result_dir / "positions.csv")
    orders = read_csv_or_empty(result_dir / "orders.csv")

    paths: list[Path] = []
    if not nav.empty and "date" in nav.columns and "net_value" in nav.columns:
        nav["date"] = pd.to_datetime(nav["date"])
        net_value = pd.to_numeric(nav["net_value"], errors="coerce")
        drawdown = net_value / net_value.cummax() - 1
        fig, axes = plt.subplots(2, 1, figsize=(12, 8), sharex=True)
        axes[0].plot(nav["date"], net_value, color="#1f77b4", linewidth=1.6)
        axes[0].set_title("Net Value")
        axes[0].set_ylabel("NAV")
        axes[0].grid(True, alpha=0.25)
        axes[1].fill_between(nav["date"], drawdown, 0, color="#c44e52", alpha=0.35)
        axes[1].set_title("Drawdown")
        axes[1].set_ylabel("Drawdown")
        axes[1].grid(True, alpha=0.25)
        fig.tight_layout()
        path = output_dir / "nav_drawdown.png"
        fig.savefig(path, dpi=150)
        plt.close(fig)
        paths.append(path)

    if not positions.empty and {"date", "asset_id", "weight"}.issubset(positions.columns):
        pos = positions.copy()
        pos["date"] = pd.to_datetime(pos["date"])
        pos["weight"] = pd.to_numeric(pos["weight"], errors="coerce").fillna(0.0)
        pivot = pos.pivot_table(index="date", columns="asset_id", values="weight", aggfunc="last").fillna(0.0)
        if not pivot.empty:
            fig, ax = plt.subplots(figsize=(12, 6))
            pivot.plot.area(ax=ax, linewidth=0)
            ax.set_title("Position Weights")
            ax.set_ylabel("Weight")
            ax.set_xlabel("")
            ax.grid(True, alpha=0.2)
            ax.legend(loc="upper left", bbox_to_anchor=(1.01, 1.0))
            fig.tight_layout()
            path = output_dir / "position_weights.png"
            fig.savefig(path, dpi=150)
            plt.close(fig)
            paths.append(path)

    if not nav.empty and "date" in nav.columns:
        nav["date"] = pd.to_datetime(nav["date"])
        fig, ax = plt.subplots(figsize=(12, 5))
        if "pending_intent_count" in nav.columns:
            ax.plot(nav["date"], pd.to_numeric(nav["pending_intent_count"], errors="coerce").fillna(0), label="Pending intents")
        if "cash" in nav.columns and "total_value" in nav.columns:
            total_value = pd.to_numeric(nav["total_value"], errors="coerce").replace(0, pd.NA)
            cash_weight = pd.to_numeric(nav["cash"], errors="coerce") / total_value
            ax.plot(nav["date"], cash_weight.fillna(0), label="Cash weight")
        ax.set_title("Execution Constraint Effects")
        ax.set_xlabel("")
        ax.grid(True, alpha=0.25)
        ax.legend()
        fig.tight_layout()
        path = output_dir / "execution_effects.png"
        fig.savefig(path, dpi=150)
        plt.close(fig)
        paths.append(path)

    if not orders.empty and {"status", "reason"}.issubset(orders.columns):
        rejected = orders[orders["status"] == "REJECTED"]
        if not rejected.empty:
            counts = rejected["reason"].fillna("unknown").value_counts()
            fig, ax = plt.subplots(figsize=(10, 5))
            counts.plot.bar(ax=ax, color="#dd8452")
            ax.set_title("Rejected Orders By Reason")
            ax.set_xlabel("")
            ax.set_ylabel("Orders")
            ax.grid(True, axis="y", alpha=0.25)
            fig.tight_layout()
            path = output_dir / "rejected_orders.png"
            fig.savefig(path, dpi=150)
            plt.close(fig)
            paths.append(path)

    return paths
