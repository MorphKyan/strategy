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


def render_sensitivity_charts(summary_csv_path: str | Path, output_dir: str | Path | None = None) -> Path | None:
    """Render sensitivity charts from sensitivity summary CSV."""
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    plt.rcParams['font.sans-serif'] = ['SimHei', 'Microsoft YaHei', 'Arial Unicode MS', 'sans-serif']
    plt.rcParams['axes.unicode_minus'] = False
    try:
        import seaborn as sns
    except ImportError:
        sns = None

    summary_csv_path = Path(summary_csv_path)
    if not summary_csv_path.exists():
        return None

    df = pd.read_csv(summary_csv_path)
    if df.empty or "start_date" not in df.columns:
        return None

    df["start_date"] = pd.to_datetime(df["start_date"])
    df = df.sort_values("start_date")

    output_dir = Path(output_dir) if output_dir else summary_csv_path.parent
    output_dir.mkdir(parents=True, exist_ok=True)

    return_col = "annualized_return_active" if ("annualized_return_active" in df.columns and df["annualized_return_active"].notna().any()) else "annualized_return"
    sharpe_col = "active_sharpe_ratio" if ("active_sharpe_ratio" in df.columns and df["active_sharpe_ratio"].notna().any()) else "sharpe_ratio"

    fig, axes = plt.subplots(3, 2, figsize=(16, 15))
    
    scenarios = df["slippage_scenario"].unique() if "slippage_scenario" in df.columns else ["all"]
    colors = {"default": "steelblue", "stress": "indianred", "dynamic_participation": "seagreen"}
    styles = {"default": "-", "stress": "--", "dynamic_participation": "-."}

    def plot_metric(row_idx, col_name, title_prefix, scale=1.0, is_pct=False):
        data_all = df[col_name].dropna() * scale
        if data_all.empty:
            return
        
        # Hist
        if sns:
            sns.histplot(data_all, kde=True, ax=axes[row_idx, 0], color=["skyblue", "salmon", "lightgreen"][row_idx % 3])
        else:
            axes[row_idx, 0].hist(data_all, bins=12, alpha=0.75, color=["skyblue", "salmon", "lightgreen"][row_idx % 3])
        axes[row_idx, 0].set_title(f"{title_prefix}分布" + (" (%)" if is_pct else ""))
        axes[row_idx, 0].set_xlabel(title_prefix + (" (%)" if is_pct else ""))

        # Line
        if "slippage_scenario" in df.columns and len(scenarios) > 1:
            for sc in scenarios:
                sub_df = df[df["slippage_scenario"] == sc]
                sub_data = sub_df[col_name].dropna() * scale
                c = colors.get(sc, "steelblue")
                ls = styles.get(sc, "-")
                axes[row_idx, 1].plot(sub_df["start_date"], sub_data, marker='o', markersize=3, linestyle=ls, alpha=0.85, color=c, label=f"滑点场景: {sc}")
            axes[row_idx, 1].legend(loc="best", fontsize=9)
        else:
            axes[row_idx, 1].plot(df["start_date"], data_all, marker='o', markersize=4, linestyle='-', alpha=0.7, color=["steelblue", "indianred", "seagreen"][row_idx % 3])

        axes[row_idx, 1].set_title(f"{title_prefix}随起始日变化" + (" (%)" if is_pct else ""))
        axes[row_idx, 1].set_ylabel(title_prefix + (" (%)" if is_pct else ""))
        axes[row_idx, 1].grid(True, linestyle='--', alpha=0.6)

    plot_metric(0, return_col, "有效年化收益率(扣除预热期)", scale=100.0, is_pct=True)
    plot_metric(1, sharpe_col, "有效夏普比率(扣除预热期)")
    plot_metric(2, "max_drawdown", "最大回撤", scale=100.0, is_pct=True)

    fig.tight_layout()
    save_path = output_dir / "sensitivity_analysis.png"
    fig.savefig(save_path, dpi=150)
    plt.close(fig)
    return save_path
