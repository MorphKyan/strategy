"""复现当前定时策略的国债日频、其他资产月频研究。仅在本进程注册研究策略。"""
from __future__ import annotations

import argparse
import copy
import hashlib
import importlib.metadata
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
from concurrent.futures import ProcessPoolExecutor, as_completed
from dataclasses import replace
from datetime import date

import numpy as np
import pandas as pd
import yaml

ROOT = Path(__file__).resolve().parents[4]
PLATFORM = ROOT / "platform"
sys.path.insert(0, str(PLATFORM))
from src.platform_core.data import LocalCsvBarData
from src.platform_core.data_store import assets_from_config, validate_market_dates
from src.platform_core.engine import PlatformBacktestEngine
from src.platform_core.execution import ExecutionEngine, FeeProfile
from src.platform_core.models import PendingIntent, PortfolioState, TargetPortfolio
from src.platform_core.storage import InMemoryStore
from src.platform_core.strategy import BUILTIN_STRATEGIES, Strategy, StrategyContext
from src.platform_core.strategies.expected_shortfall import RiskParityExpectedShortfallFixedBudgetStrategy as ES
from src.platform_core.slippage import apply_slippage_scenario

CONFIGS = {
    "etf": "capital_100k/es_252d_fhs_stepdown_trend_200k_v2_563020_511130.yaml",
    "proxy": "index_benchmark/index_es_252d_fhs_stepdown_trend_100k_v2.yaml",
}
SIGNALS = {}


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, default=str).encode()).hexdigest()


class ResearchState(PortfolioState):
    def replace_pending(self, target, current_date):
        if self.strategy_state.pop("bond_only", False):
            # 平台普通目标会把未列出的已有持仓设为零；单资产日频目标须显式保留其份额。
            self.pending_intents = {
                aid: PendingIntent(aid, weight, current_date, signal_date=current_date)
                for aid, weight in target.weights.items()
            }
        else:
            super().replace_pending(target, current_date)


class ResearchStrategy(ES):
    name = "research_bond_daily_mixed"

    def _inverse_vol_target(self, context, universe):
        if not context.params.get("cached_signals", True):
            return super()._inverse_vol_target(context, universe)
        # 每个运行起点重新预热 252 个共同收益；之后只使用截至当日的固定252日信号。
        if self._calendar_index(context) < 252:
            return None
        weights = SIGNALS[context.params["research_universe"]].get(str(context.date))
        return TargetPortfolio(dict(weights)) if weights else None

    def generate_targets(self, context):
        mode = context.params["research_mode"]
        if not mode.startswith("mixed"):
            return super().generate_targets(context)
        bond = context.params["bond_asset"]
        context.runtime["rebalance_frequency"] = "monthly"
        month_end = Strategy.should_check_rebalance(self, context)
        context.runtime["rebalance_frequency"] = "daily"
        target = self.generate_theoretical_targets(context)
        if target is None:
            return None
        context.theoretical_target = target
        if month_end or not any(p.quantity > 1e-9 for p in context.state.positions.values()):
            if self.should_rebalance(context, target):
                return target
        prices = {aid: bar.close for aid, bar in context.bars.items()}
        current = context.state.weights(prices).get(bond, 0.0)
        desired = target.weights.get(bond, 0.0)
        value = context.state.total_value(prices)
        if desired > current + context.state.cash / value + 1e-9:
            context.runtime["bond_cash_limited_days"] = context.runtime.get("bond_cash_limited_days", 0) + 1
        threshold = 0.05 if mode == "mixed5" else 0.0
        if abs(desired - current) <= threshold + 1e-12:
            return None
        context.state.strategy_state["bond_only"] = True
        return TargetPortfolio({bond: desired})


class BondFreeExecution(ExecutionEngine):
    def __init__(self, config, bond):
        super().__init__(config)
        self.normal_fee, self.bond = config.fee_profile, bond

    def _execution_price(self, valuation_price, side, asset, bar, quantity):
        # 在现金购买力检查和实际计费之前切换费用，其余执行逻辑全部沿用平台。
        self.config = replace(self.config, fee_profile=FeeProfile(0, 0) if asset.asset_id == self.bond else self.normal_fee)
        return super()._execution_price(valuation_price, side, asset, bar, quantity)


class ResearchEngine(PlatformBacktestEngine):
    def _initial_state(self):
        return ResearchState.from_dict(super()._initial_state().to_dict())


def initialize(signal_file):
    global SIGNALS
    os.chdir(PLATFORM)
    SIGNALS = json.loads(Path(signal_file).read_text(encoding="utf-8"))
    BUILTIN_STRATEGIES[ResearchStrategy.name] = ResearchStrategy


def prepare(output):
    configs, provenance, signals = {}, {}, {}
    source_files = list((PLATFORM / "src/platform_core").rglob("*.py")) + [Path(__file__)]
    provenance["code"] = {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(source_files)}
    provenance["git_head"] = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    provenance["python"] = sys.version
    provenance["dependencies"] = {p: importlib.metadata.version(p) for p in ("numpy", "pandas", "scipy", "PyYAML", "akshare", "finshare")}
    provenance["data"] = {}
    for name, relative in CONFIGS.items():
        path = PLATFORM / "configs" / relative
        config = yaml.safe_load(path.read_text(encoding="utf-8"))
        configs[name] = config
        frames = {a["code"]: pd.read_csv(PLATFORM / "data" / f"{a['code']}.csv") for a in config["assets"]}
        validate_market_dates({c: date.fromisoformat(f.trade_date.max()) for c, f in frames.items()}, date.today())
        calendar = sorted(set.intersection(*(set(f.trade_date) for f in frames.values())))
        directory = output / "data" / name
        directory.mkdir(parents=True, exist_ok=True)
        provenance[name] = {"start": calendar[0], "end": calendar[-1], "common_observations": len(calendar),
                            "removed_noncommon_rows": {c: int(((f.trade_date >= calendar[0]) & ~f.trade_date.isin(calendar)).sum()) for c, f in frames.items()},
                            "source_config": relative, "source_config_hash": hashlib.sha256(path.read_bytes()).hexdigest()}
        for code, frame in frames.items():
            frame[frame.trade_date.isin(calendar)].to_csv(directory / f"{code}.csv", index=False)
            for p in (PLATFORM / "data" / f"{code}.csv", PLATFORM / "data" / f"{code}_hfq_factor.csv"):
                if p.exists():
                    provenance["data"][str(p.relative_to(ROOT))] = hashlib.sha256(p.read_bytes()).hexdigest()
                    if p.stem.endswith("_hfq_factor"):
                        shutil.copyfile(p, directory / p.name)
        for kind in ("dividends", "splits"):
            p = PLATFORM / "data" / f"platform_{kind}.csv"
            shutil.copyfile(p, directory / p.name)
            provenance["data"][str(p.relative_to(ROOT))] = hashlib.sha256(p.read_bytes()).hexdigest()
        config["data"] = {"data_dir": str(directory)}
        config["portfolio"] = {"initial_cash": 200000.0, "initial_equity": 200000.0, "initial_positions": []}
        config["strategy"].pop("strategy_version_id", None)
        data = LocalCsvBarData(directory, assets_from_config(config["assets"]))
        strategy = ES()
        params = config["strategy"]["params"]
        context = StrategyContext(data.calendar[0], data.assets, {}, PortfolioState(200000), data, params, {})
        strategy.initialize(context)
        signals[name] = {}
        for i, day in enumerate(data.calendar):
            if i < 252:
                continue
            context.date = day
            target = strategy._inverse_vol_target(context, params["universe"])
            if target is not None:
                signals[name][str(day)] = target.weights
            if i % 500 == 0:
                print(f"signals {name}: {i}/{len(data.calendar)}", flush=True)
    (output / "signals.json").write_text(json.dumps(signals), encoding="utf-8")
    (output / "provenance.json").write_text(json.dumps(provenance, ensure_ascii=False, indent=2), encoding="utf-8")
    return configs, provenance


def run_case(task):
    config = copy.deepcopy(task["config"])
    mode = task["mode"]
    params = config["strategy"]["params"]
    bond = next(a["asset_id"] for a in config["assets"] if a["code"] in ("511130", "CBA21801"))
    params.update(research_mode=mode, research_universe=task["universe"], bond_asset=bond,
                  cached_signals=not task.get("uncached", False),
                  rebalance_frequency="monthly" if mode == "monthly" else "daily")
    config["strategy"]["strategy_name"] = ResearchStrategy.name
    config["backtest"] = {"start_date": task["start"], "end_date": task["end"], "enable_checkpoints": False}
    config["platform"] = {"run_name": f"{task['universe']}_{mode}"}
    config = apply_slippage_scenario(config, task["scenario"])
    if mode == "mixed0":
        config["execution"]["weight_tolerance_by_asset_id"] = {bond: 0.0}
    store = InMemoryStore()
    engine = ResearchEngine(config, store, output_dir=task["raw"])
    if mode != "charged_daily":
        engine.execution = BondFreeExecution(engine.execution.config, bond)
    result = engine.run()
    # 引擎把指标保存在 manifest.json；以实际产物为源，不在汇总时重建收益。
    metrics = json.loads((result.output_dir / "manifest.json").read_text(encoding="utf-8"))["metrics"]
    trade_path = result.output_dir / "trades.csv"
    trades = pd.read_csv(trade_path) if trade_path.stat().st_size else pd.DataFrame()
    if not trades.empty:
        assert (pd.to_datetime(trades.signal_date) < pd.to_datetime(trades.date)).all()
        if mode != "charged_daily":
            assert trades.loc[trades.asset_id == bond, "fee"].eq(0).all()
            other = trades[trades.asset_id != bond]
            expected = np.maximum(other.trade_value * .0002, 5)
            assert np.allclose(other.fee, expected)
        if mode.startswith("mixed"):
            calendar = engine.data.calendar
            monthly = {str(d) for d, nxt in zip(calendar, calendar[1:]) if (d.year, d.month) != (nxt.year, nxt.month)}
            first_signal = trades.signal_date.min()
            assert trades.loc[trades.asset_id != bond, "signal_date"].isin(monthly | {first_signal}).all()
    checkpoint = json.loads(next(result.output_dir.glob("checkpoints/*.json")).read_text(encoding="utf-8"))
    row = {k: task[k] for k in ("universe", "mode", "phase", "start", "end", "scenario")}
    row.update(metrics)
    row["bond_trade_count"] = int(trades.asset_id.eq(bond).sum()) if not trades.empty else 0
    row["bond_cash_limited_days"] = checkpoint["strategy_state"]["_strategy_runtime"]["runtime"].get("bond_cash_limited_days", 0)
    row["artifact"] = str(result.output_dir)
    store.close()
    if task["phase"] == "sensitivity":
        shutil.rmtree(result.output_dir)
    return row


def make_tasks(configs, provenance, output, phase):
    tasks = []
    for name, config in configs.items():
        info = provenance[name]
        calendar = pd.read_csv(Path(config["data"]["data_dir"]) / f"{config['assets'][0]['code']}.csv").trade_date.tolist()
        windows = [("base", info["start"])]
        if name == "proxy":
            windows.append(("matched", provenance["etf"]["start"]))
        for anchor in pd.date_range(info["start"], info["end"], freq=pd.DateOffset(months=2)):
            start = next((d for d in calendar if d >= str(anchor.date())), None)
            if start:
                windows.append(("sensitivity", start))
        for kind, start in windows:
            if phase != "all" and kind != phase:
                continue
            modes = ("charged_daily", "daily", "monthly", "mixed5", "mixed0") if kind == "base" else ("daily", "monthly", "mixed5", "mixed0")
            for mode in modes:
                for scenario in ("default", "stress"):
                    task = dict(universe=name, mode=mode, phase=kind, start=start, end=info["end"], scenario=scenario, config=config)
                    task["raw"] = str(output / "raw" / digest({k: v for k, v in task.items() if k != "config"})[:16])
                    tasks.append(task)
    return tasks


def summarize(rows, output):
    frame = pd.DataFrame(rows)
    frame.to_csv(output / "metrics.csv", index=False, encoding="utf-8-sig")
    keys = ["universe", "phase", "start", "end", "scenario"]
    reference = frame[frame["mode"] == "monthly"]
    pairs = frame.merge(reference, on=keys, suffixes=("", "_monthly"), validate="many_to_one")
    for key in ("annualized_return", "annualized_return_active", "sharpe_ratio", "active_sharpe_ratio", "max_drawdown", "annualized_turnover"):
        pairs[f"delta_{key}"] = pairs[key] - pairs[f"{key}_monthly"]
    pairs["valid_pair"] = (pairs.active_observations >= 126) & (pairs.active_observations_monthly >= 126)
    pairs.to_csv(output / "comparisons.csv", index=False, encoding="utf-8-sig")
    eligible = pairs[(pairs.phase == "sensitivity") & pairs.valid_pair]
    summary = eligible.groupby(["universe", "mode", "scenario"]).agg(
        starts=("start", "size"), median_return=("annualized_return_active", "median"),
        median_sharpe=("active_sharpe_ratio", "median"), median_sharpe_edge=("delta_active_sharpe_ratio", "median"),
        min_sharpe_edge=("delta_active_sharpe_ratio", "min"), max_sharpe_edge=("delta_active_sharpe_ratio", "max"),
        sharpe_wins=("delta_active_sharpe_ratio", lambda x: int((x > 1e-10).sum())),
        return_wins=("delta_annualized_return_active", lambda x: int((x > 1e-10).sum())),
        worst_drawdown=("max_drawdown", "min"))
    summary.to_csv(output / "sensitivity_summary.csv", encoding="utf-8-sig")
    print(frame.groupby(["universe", "phase"]).size().to_string(), flush=True)


def render_evidence(rows, output):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    labels = {"daily": "All daily, 5pp", "monthly": "All monthly, 5pp",
              "mixed5": "Bond daily 5pp / others monthly", "mixed0": "Bond daily 0pp / others monthly"}
    colors = {"monthly": "tab:blue", "daily": "tab:orange", "mixed5": "tab:green", "mixed0": "tab:red"}
    fig, axes = plt.subplots(2, 2, figsize=(13, 8))
    for col, universe in enumerate(("proxy", "etf")):
        for row in rows:
            if row["phase"] != "base" or row["scenario"] != "default" or row["universe"] != universe or row["mode"] == "charged_daily":
                continue
            nav = pd.read_csv(Path(row["artifact"]) / "nav.csv")
            dates = pd.to_datetime(nav.date)
            axes[0, col].plot(dates, nav.net_value, label=labels[row["mode"]], color=colors[row["mode"]], linewidth=1.2)
            axes[1, col].plot(dates, 100 * (nav.net_value / nav.net_value.cummax() - 1), color=colors[row["mode"]], linewidth=1)
        axes[0, col].set_title(f"{universe.upper()} | default slippage | bond commission=0")
        axes[0, col].set_ylabel("NAV (includes 252-day cash warmup)")
        axes[0, col].legend(fontsize=7)
        axes[1, col].set_ylabel("Drawdown (%)")
        for ax in axes[:, col]:
            ax.grid(alpha=.2)
    fig.tight_layout()
    fig.savefig(output / "nav_drawdown.png", dpi=160)
    plt.close(fig)
    evidence = {"provenance": json.loads((output / "provenance.json").read_text(encoding="utf-8")),
                "runs": [{k: v for k, v in row.items() if k != "artifact"} for row in rows],
                "verification": json.loads((output / "verification.json").read_text(encoding="utf-8")) if (output / "verification.json").exists() else []}
    (output / "evidence.json").write_text(json.dumps(evidence, ensure_ascii=False, indent=2), encoding="utf-8")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workers", type=int, default=8)
    parser.add_argument("--phase", choices=("all", "base", "sensitivity", "matched"), default="all")
    parser.add_argument("--output", type=Path, default=PLATFORM / "results/bond_daily_mixed_rebalance")
    parser.add_argument("--verify", action="store_true", help="独立禁用信号缓存重算四个主方案，并核对基线")
    args = parser.parse_args()
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=True)
    os.chdir(PLATFORM)
    configs, provenance = prepare(output)
    initialize(output / "signals.json")
    tasks = make_tasks(configs, provenance, output, args.phase)
    generated = PLATFORM / "results/configs/bond_daily_mixed_rebalance" / digest(provenance)[:12]
    generated.mkdir(parents=True, exist_ok=True)
    for name, config in configs.items():
        (generated / f"{name}.yaml").write_text(yaml.safe_dump(config, allow_unicode=True, sort_keys=False), encoding="utf-8")
    rows = []
    with ProcessPoolExecutor(args.workers, initializer=initialize, initargs=(output / "signals.json",)) as pool:
        futures = [pool.submit(run_case, task) for task in tasks]
        for f in as_completed(futures):
            rows.append(f.result())
            if len(rows) % 20 == 0 or len(rows) == len(tasks):
                print(f"runs: {len(rows)}/{len(tasks)}", flush=True)
    summarize(rows, output)
    if args.verify:
        checks = []
        for task in tasks:
            if task["phase"] != "base" or task["scenario"] != "default" or task["mode"] not in ("mixed5", "mixed0"):
                continue
            previous = next(r for r in rows if all(r[k] == task[k] for k in ("universe", "mode", "phase", "scenario", "start")))
            fresh = run_case({**task, "uncached": True, "raw": str(output / "verification")})
            differences = {k: abs(fresh[k] - previous[k]) for k in ("annualized_return", "sharpe_ratio", "max_drawdown", "fee_total", "trade_count", "order_count", "rejected_order_count")}
            assert max(differences.values()) < 1e-9, differences
            checks.append(dict(universe=task["universe"], mode=task["mode"], differences=differences))
        # 对照原策略、原执行器，验证研究包装没有改变现行收佣基线。
        for name, original in configs.items():
            config = apply_slippage_scenario(copy.deepcopy(original), "default")
            info = provenance[name]
            config["backtest"] = {"start_date": info["start"], "end_date": info["end"]}
            config["strategy"]["params"]["rebalance_frequency"] = "daily"
            baseline = PlatformBacktestEngine(config, InMemoryStore(), output_dir=output / "original_baseline").run()
            metrics = json.loads((baseline.output_dir / "manifest.json").read_text(encoding="utf-8"))["metrics"]
            previous = next(r for r in rows if r["universe"] == name and r["mode"] == "charged_daily" and r["phase"] == "base" and r["scenario"] == "default")
            differences = {k: abs(metrics[k] - previous[k]) for k in ("annualized_return", "sharpe_ratio", "fee_total", "trade_count")}
            assert max(differences.values()) < 1e-9, differences
            checks.append(dict(universe=name, mode="original_baseline", differences=differences))
        (output / "verification.json").write_text(json.dumps(checks, indent=2), encoding="utf-8")
        print("独立复现与基线一致性检查通过", flush=True)
    render_evidence(rows, output)


if __name__ == "__main__":
    main()
