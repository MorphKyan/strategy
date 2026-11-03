"""复现日/月频收益差归因，以及基于归因的月频小范围改进验证。"""
from __future__ import annotations

import argparse
import copy
import importlib.util
import json
import os
from pathlib import Path
import shutil
import sys
from concurrent.futures import ProcessPoolExecutor, as_completed

import numpy as np
import pandas as pd
import yaml

ROOT = Path(__file__).resolve().parents[4]
PLATFORM = ROOT / "platform"
REFERENCE = PLATFORM / "reports/bond_daily_mixed_rebalance/20261102/reproduce.py"
spec = importlib.util.spec_from_file_location("bond_daily_reference", REFERENCE)
ref = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = ref
spec.loader.exec_module(ref)
from src.platform_core.models import TargetPortfolio
from src.platform_core.strategy import BUILTIN_STRATEGIES, Strategy

COMPONENTS = {}


class AttributionStrategy(ref.ResearchStrategy):
    name = "research_monthly_frequency_attribution"

    def _component(self, context, day, universe):
        if not context.params.get("direct_components", False):
            return COMPONENTS[context.params["research_universe"]][str(day)]
        previous_date = context.date
        context.date = day
        try:
            target = ref.ES._inverse_vol_target(self, context, universe)
            prices = context.data.get_price_frame(universe, day)
            multipliers = np.where(prices.iloc[-1] >= prices.tail(200).mean(), 1., .25)
            risk = np.array([target.weights[aid] for aid in universe]) / multipliers
            covariance = np.cov(prices.pct_change().dropna().tail(252).to_numpy(), rowvar=False)
            return {"risk": risk.tolist(), "trend": multipliers.tolist(), "covariance": covariance.tolist()}
        finally:
            context.date = previous_date

    def _inverse_vol_target(self, context, universe):
        original = super()._inverse_vol_target(context, universe)
        if original is None:
            return None
        mode = context.params["research_mode"]
        if mode in ("monthly", "daily"):
            return original
        component = self._component(context, context.date, universe)
        risk, trend = np.array(component["risk"]), np.array(component["trend"])
        if mode in ("monthly_smooth21", "monthly_confirm3", "monthly_combined"):
            index = self._calendar_index(context)
            if mode in ("monthly_smooth21", "monthly_combined"):
                days = context.data.calendar[max(252, index - 20):index + 1]
                risk = np.mean([self._component(context, day, universe)["risk"] for day in days], axis=0)
                covariance = np.array(component["covariance"])
                volatility = np.sqrt(max(float(risk @ covariance @ risk), 0.) * 252.)
                risk *= min(1., float(context.params["volatility_target"]) / volatility) if volatility > 0 else 1.
            if mode in ("monthly_confirm3", "monthly_combined"):
                held = np.array(context.runtime.get("confirmed_trend", trend.tolist()))
                days = context.data.calendar[max(252, index - 2):index + 1]
                if len(days) == 3:
                    history = np.array([self._component(context, day, universe)["trend"] for day in days])
                    stable = (history == trend).all(axis=0)
                    trend = np.where(stable, trend, held)
                context.runtime["confirmed_trend"] = trend.tolist()
            return TargetPortfolio(dict(zip(universe, map(float, risk * trend))))
        old_frequency = context.runtime["rebalance_frequency"]
        context.runtime["rebalance_frequency"] = "monthly"
        month_end = Strategy.should_check_rebalance(self, context)
        context.runtime["rebalance_frequency"] = old_frequency
        if month_end or "monthly_risk" not in context.runtime:
            context.runtime["monthly_risk"] = risk.tolist()
            context.runtime["monthly_trend"] = trend.tolist()
        if mode in ("frozen", "risk_monthly"):
            risk = np.array(context.runtime["monthly_risk"])
        if mode in ("frozen", "trend_monthly"):
            trend = np.array(context.runtime["monthly_trend"])
        return TargetPortfolio(dict(zip(universe, map(float, risk * trend))))


def initialize(output):
    global COMPONENTS
    ref.initialize(Path(output) / "signals.json")
    COMPONENTS = json.loads((Path(output) / "components.json").read_text(encoding="utf-8"))
    BUILTIN_STRATEGIES[AttributionStrategy.name] = AttributionStrategy


def prepare(output):
    configs, provenance = ref.prepare(output)
    components = {}
    signals = json.loads((output / "signals.json").read_text(encoding="utf-8"))
    for name, config in configs.items():
        data = ref.LocalCsvBarData(config["data"]["data_dir"], ref.assets_from_config(config["assets"]))
        universe = config["strategy"]["params"]["universe"]
        prices = data.get_price_frame(universe, data.calendar[-1])
        returns = prices.pct_change().to_numpy(dtype=float)
        price_index = {str(day): i for i, day in enumerate(prices.index)}
        trend = pd.DataFrame(np.where(prices >= prices.rolling(200).mean(), 1., .25), index=prices.index, columns=prices.columns)
        components[name] = {}
        for day, weights in signals[name].items():
            multipliers = trend.loc[ref.date.fromisoformat(day)].to_numpy(dtype=float)
            target = np.array([weights[aid] for aid in universe])
            index = price_index[day]
            covariance = np.cov(returns[index - 251:index + 1], rowvar=False)
            components[name][day] = {"risk": (target / multipliers).tolist(), "trend": multipliers.tolist(), "covariance": covariance.tolist()}
    # 只改变铜报价的计价单位，保持资产ID、收益率、理论信号及交易成本规则完全一致。
    fine = copy.deepcopy(configs["proxy"])
    directory = output / "data/proxy_fine"
    shutil.copytree(Path(fine["data"]["data_dir"]), directory, dirs_exist_ok=True)
    copper_path = directory / "CU0.csv"
    copper = pd.read_csv(copper_path)
    copper[["open", "high", "low", "close"]] *= .001
    copper["volume"] *= 1000.
    copper.to_csv(copper_path, index=False)
    fine["data"]["data_dir"] = str(directory)
    configs["proxy_fine"] = fine
    signals["proxy_fine"] = signals["proxy"]
    components["proxy_fine"] = components["proxy"]
    provenance["proxy_fine"] = {**provenance["proxy"], "unit_diagnostic": "仅CU0价格乘0.001，成交量乘1000，最小单位仍为1；非可交易合约规格。"}
    (output / "signals.json").write_text(json.dumps(signals), encoding="utf-8")
    (output / "components.json").write_text(json.dumps(components), encoding="utf-8")
    provenance["code"][str(Path(__file__).relative_to(ROOT))] = ref.hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    (output / "provenance.json").write_text(json.dumps(provenance, ensure_ascii=False, indent=2), encoding="utf-8")
    return configs, provenance


def attribution(engine, artifact, initial=200000.):
    nav = pd.read_csv(artifact / "nav.csv").set_index("date")
    positions = pd.read_csv(artifact / "positions.csv")
    trade_path = artifact / "trades.csv"
    trades = pd.read_csv(trade_path) if trade_path.stat().st_size else pd.DataFrame()
    dates = nav.index
    pnl, details, reversals = pd.DataFrame(index=dates), [], []
    for aid, asset in engine.assets.items():
        selected = positions[positions.asset_id == aid]
        quantity = selected.set_index("date").quantity.reindex(dates, fill_value=0.)
        previous = quantity.shift(1, fill_value=0.)
        for event in engine.splits:
            day = str(event.get("effective_date"))
            if event["code"] == asset.code and day in dates:
                assert previous.loc[day] == 0., "归因入口尚不支持持仓期间份额拆分"
        market = engine.data.frames[aid].copy()
        market.index = market.index.map(str)
        opening, closing = market.open.reindex(dates), market.close.reindex(dates)
        overnight = previous * (opening - closing.shift(1).fillna(closing.iloc[0]))
        intraday = quantity * (closing - opening)
        dividend = pd.Series(0., index=dates)
        for event in engine.dividends:
            day = str(event["ex_date"])
            if event["code"] == asset.code and day in dates:
                dividend.loc[day] += previous.loc[day] * event["dividend_per_share"]
        subset = trades[trades.asset_id == aid].copy() if not trades.empty else pd.DataFrame()
        fee, slip = pd.Series(0., index=dates), pd.Series(0., index=dates)
        if not subset.empty:
            fee = subset.groupby("date").fee.sum().reindex(dates, fill_value=0.)
            subset["slippage_amount"] = abs(subset.price - subset.valuation_price) * subset.quantity
            slip = subset.groupby("date").slippage_amount.sum().reindex(dates, fill_value=0.)
            prior_side, prior_index = None, None
            for trade in subset.itertuples():
                current_index = dates.get_loc(trade.date)
                if prior_side is not None and trade.side != prior_side and current_index - prior_index <= 10:
                    reversals.append({"asset": aid, "date": trade.date, "gap_days": current_index - prior_index})
                prior_side, prior_index = trade.side, current_index
        gross = overnight + intraday + dividend
        pnl[aid] = gross - fee - slip
        details.append({"asset": aid, "gross_pnl": gross.sum(), "overnight_pnl": overnight.sum(),
                        "intraday_pnl": intraday.sum(), "dividends": dividend.sum(), "fee": fee.sum(),
                        "slippage": slip.sum(), "net_pnl": pnl[aid].sum(),
                        "mean_weight": selected.weight.sum() / len(dates), "trades": len(subset)})
    actual = nav.total_value.diff().fillna(nav.total_value.iloc[0] - initial)
    residual = actual - pnl.sum(axis=1)
    assert residual.abs().max() < 1e-6, residual.abs().max()
    years = pnl.groupby(pnl.index.str[:4]).sum().to_dict(orient="index")
    return {"assets": details, "yearly_net_pnl": years, "fast_reversals": reversals,
            "max_daily_accounting_residual": float(residual.abs().max())}


def run_case(task):
    config = copy.deepcopy(task["config"])
    mode = task["mode"]
    config["strategy"]["strategy_name"] = ref.ResearchStrategy.name if mode.startswith("mixed") else AttributionStrategy.name
    params = config["strategy"]["params"]
    params.update(research_mode=mode, research_universe=task["universe"],
                  rebalance_frequency="monthly" if mode.startswith("monthly") else "daily",
                  cached_signals=not task.get("direct", False), direct_components=task.get("direct", False))
    config["backtest"] = {"start_date": task["start"], "end_date": task["end"], "enable_checkpoints": False}
    config["platform"] = {"run_name": f"{task['universe']}_{mode}"}
    config = ref.apply_slippage_scenario(config, task["scenario"])
    if task.get("zero_cost"):
        config["execution"]["fee"] = {"rate": 0., "min_fee": 0.}
        config["execution"]["slippage"]["default_bps"] = 0.
        config["execution"]["slippage"]["qdii_commodity_bps"] = 0.
    bond = next(a["asset_id"] for a in config["assets"] if a["code"] in ("511130", "CBA21801"))
    config["strategy"]["params"]["bond_asset"] = bond
    if mode == "mixed0":
        config["execution"]["weight_tolerance_by_asset_id"] = {bond: 0.}
    store = ref.InMemoryStore()
    engine = ref.ResearchEngine(config, store, output_dir=task["raw"])
    engine.execution = ref.BondFreeExecution(engine.execution.config, bond)
    result = engine.run()
    row = {k: task[k] for k in ("universe", "mode", "phase", "start", "end", "scenario")}
    row["zero_cost"] = task.get("zero_cost", False)
    row["metrics"] = json.loads((result.output_dir / "manifest.json").read_text(encoding="utf-8"))["metrics"]
    row["artifact"] = str(result.output_dir)
    if task["phase"] == "base":
        row["attribution"] = attribution(engine, result.output_dir)
    trade_path = result.output_dir / "trades.csv"
    if trade_path.stat().st_size:
        trades = pd.read_csv(trade_path)
        assert (pd.to_datetime(trades.signal_date) < pd.to_datetime(trades.date)).all()
        assert trades.loc[trades.asset_id == bond, "fee"].eq(0).all()
        if mode.startswith("monthly"):
            calendar = engine.data.calendar
            monthly_dates = {str(d) for d, nxt in zip(calendar, calendar[1:]) if (d.year, d.month) != (nxt.year, nxt.month)}
            assert trades.signal_date.isin(monthly_dates | {trades.signal_date.min()}).all()
        elif mode.startswith("mixed"):
            calendar = engine.data.calendar
            monthly_dates = {str(d) for d, nxt in zip(calendar, calendar[1:]) if (d.year, d.month) != (nxt.year, nxt.month)}
            assert trades.loc[trades.asset_id != bond, "signal_date"].isin(monthly_dates | {trades.signal_date.min()}).all()
    store.close()
    if task["phase"] == "sensitivity":
        shutil.rmtree(result.output_dir)
    return row


def tasks(configs, provenance, output, phase):
    cases = []
    for name, config in configs.items():
        if phase == "units" and name != "proxy_fine":
            continue
        info = provenance[name]
        calendar = pd.read_csv(Path(config["data"]["data_dir"]) / f"{config['assets'][0]['code']}.csv").trade_date.tolist()
        windows = [("base", info["start"])]
        if phase in ("all", "units"):
            for anchor in pd.date_range(info["start"], info["end"], freq=pd.DateOffset(months=2)):
                start = next((d for d in calendar if d >= str(anchor.date())), None)
                if start:
                    windows.append(("sensitivity", start))
        for kind, start in windows:
            modes = ["monthly", "daily", "frozen", "risk_monthly", "trend_monthly", "monthly_smooth21", "monthly_confirm3", "monthly_combined"]
            if name == "proxy_fine":
                modes = ["monthly", "daily", "mixed5", "mixed0", "monthly_confirm3"]
            elif kind == "base":
                modes.extend(("mixed5", "mixed0"))
            for mode in modes:
                for scenario in ("default", "stress"):
                    task = dict(universe=name, mode=mode, phase=kind, start=start, end=info["end"], scenario=scenario, config=config)
                    task["raw"] = str(output / "raw" / ref.digest({k: v for k, v in task.items() if k != "config"})[:16])
                    cases.append(task)
        for mode in ("monthly", "daily"):
            task = dict(universe=name, mode=mode, phase="base", start=info["start"], end=info["end"], scenario="default", config=config, zero_cost=True)
            task["raw"] = str(output / "raw" / ref.digest({k: v for k, v in task.items() if k != "config"})[:16])
            cases.append(task)
    return cases


def summarize(rows, output):
    flat = [{**{k: v for k, v in r.items() if k not in ("metrics", "attribution")}, **r["metrics"]} for r in rows]
    frame = pd.DataFrame(flat)
    frame.to_csv(output / "metrics.csv", index=False, encoding="utf-8-sig")
    payload = {"provenance": json.loads((output / "provenance.json").read_text(encoding="utf-8")), "runs": rows}
    (output / "evidence.json").write_text(json.dumps(payload, ensure_ascii=False, indent=2, allow_nan=False), encoding="utf-8")
    reference = frame[(frame["mode"] == "monthly") & ~frame.zero_cost]
    keys = ["universe", "phase", "start", "end", "scenario"]
    pairs = frame[~frame.zero_cost].merge(reference, on=keys, suffixes=("", "_monthly"), validate="many_to_one")
    for key in ("annualized_return", "annualized_return_active", "sharpe_ratio", "active_sharpe_ratio", "max_drawdown", "annualized_turnover"):
        pairs["delta_" + key] = pairs[key] - pairs[key + "_monthly"]
    pairs["valid_pair"] = (pairs.active_observations >= 126) & (pairs.active_observations_monthly >= 126)
    pairs.to_csv(output / "comparisons.csv", index=False, encoding="utf-8-sig")
    eligible = pairs[(pairs.phase == "sensitivity") & pairs.valid_pair]
    summary = eligible.groupby(["universe", "mode", "scenario"]).agg(
        starts=("start", "size"), median_return=("annualized_return_active", "median"),
        median_return_edge=("delta_annualized_return_active", "median"), median_sharpe=("active_sharpe_ratio", "median"),
        median_sharpe_edge=("delta_active_sharpe_ratio", "median"),
        return_wins=("delta_annualized_return_active", lambda x: int((x > 1e-10).sum())),
        sharpe_wins=("delta_active_sharpe_ratio", lambda x: int((x > 1e-10).sum())),
        drawdown_wins=("delta_max_drawdown", lambda x: int((x > 1e-10).sum())), worst_drawdown=("max_drawdown", "min"))
    summary.to_csv(output / "sensitivity_summary.csv", encoding="utf-8-sig")
    print(frame[frame.phase == "base"][["universe", "mode", "zero_cost", "scenario", "annualized_return", "sharpe_ratio", "max_drawdown", "trade_count"]].to_string(index=False), flush=True)


def verify(rows, cases, output):
    checks = []
    for task in cases:
        expected_mode = "monthly_confirm3" if task["universe"] == "proxy_fine" else "monthly_combined"
        if task["phase"] != "base" or task["mode"] != expected_mode or task["scenario"] != "default":
            continue
        previous = next(r for r in rows if r["universe"] == task["universe"] and r["mode"] == task["mode"] and r["phase"] == "base" and r["scenario"] == "default" and not r["zero_cost"])
        fresh = run_case({**task, "direct": True, "raw": str(output / "verification")})
        differences = {k: abs(previous["metrics"][k] - fresh["metrics"][k]) for k in ("annualized_return", "sharpe_ratio", "max_drawdown", "fee_total", "trade_count", "order_count", "rejected_order_count")}
        assert max(differences.values()) < 1e-8, differences
        checks.append({"universe": task["universe"], "mode": task["mode"], "differences": differences})
    old = json.loads((REFERENCE.parent / "evidence.json").read_text(encoding="utf-8"))
    for row in rows:
        if row["universe"] == "proxy_fine" or row["phase"] != "base" or row["mode"] not in ("monthly", "daily", "mixed5", "mixed0") or row["zero_cost"]:
            continue
        baseline = next(r for r in old["runs"] if all(r[k] == row[k] for k in ("universe", "mode", "phase", "scenario", "start", "end")))
        differences = {k: abs(row["metrics"][k] - baseline[k]) for k in ("annualized_return", "sharpe_ratio", "max_drawdown", "fee_total", "trade_count", "order_count", "rejected_order_count")}
        assert max(differences.values()) < 1e-8, differences
        checks.append({"universe": row["universe"], "mode": row["mode"], "scenario": row["scenario"], "baseline_check": True, "differences": differences})
    return checks


def render(rows, output):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    colors = {"monthly": "tab:blue", "daily": "tab:gray", "monthly_smooth21": "tab:orange", "monthly_confirm3": "tab:green", "monthly_combined": "tab:red"}
    fig, axes = plt.subplots(2, 2, figsize=(13, 8))
    has_primary = {"etf", "proxy"}.issubset({r["universe"] for r in rows})
    for col, universe in enumerate(("proxy", "etf")):
        if not has_primary:
            continue
        select = {r["mode"]: r for r in rows if r["universe"] == universe and r["phase"] == "base" and r["scenario"] == "default" and not r["zero_cost"]}
        for mode, color in colors.items():
            nav = pd.read_csv(Path(select[mode]["artifact"]) / "nav.csv")
            day = pd.to_datetime(nav.date)
            axes[0, col].plot(day, nav.net_value, label=mode, color=color, linewidth=1.1)
            axes[1, col].plot(day, 100 * (nav.net_value / nav.net_value.cummax() - 1), color=color, linewidth=1.)
        axes[0, col].set_title(universe.upper() + " | default slippage | bond fee=0")
        axes[0, col].set_ylabel("NAV (includes cash warmup)")
        axes[0, col].legend(fontsize=7)
        axes[1, col].set_ylabel("Drawdown (%)")
    for ax in axes.flat:
        ax.grid(alpha=.2)
    fig.tight_layout()
    if has_primary:
        fig.savefig(output / "monthly_candidates.png", dpi=150)
    plt.close(fig)
    if any(r["universe"] == "proxy_fine" for r in rows):
        fig, axes = plt.subplots(2, 2, figsize=(13, 8))
        colors = {"monthly": "tab:blue", "daily": "tab:gray", "mixed5": "tab:green", "mixed0": "tab:orange", "monthly_confirm3": "tab:red"}
        for col, scenario in enumerate(("default", "stress")):
            for mode, color in colors.items():
                row = next(r for r in rows if r["universe"] == "proxy_fine" and r["phase"] == "base" and r["mode"] == mode and r["scenario"] == scenario and not r["zero_cost"])
                nav = pd.read_csv(Path(row["artifact"]) / "nav.csv")
                day = pd.to_datetime(nav.date)
                axes[0, col].plot(day, nav.net_value, label=mode, color=color, linewidth=1.1)
                axes[1, col].plot(day, 100 * (nav.net_value / nav.net_value.cummax() - 1), color=color, linewidth=1.)
            axes[0, col].set_title("CU0 unit=0.001 original | " + scenario)
            axes[0, col].set_ylabel("NAV (includes cash warmup)")
            axes[0, col].legend(fontsize=7)
            axes[1, col].set_ylabel("Drawdown (%)")
        for ax in axes.flat:
            ax.grid(alpha=.2)
        fig.tight_layout()
        fig.savefig(output / "proxy_unit_sensitivity.png", dpi=150)
        plt.close(fig)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workers", type=int, default=8)
    parser.add_argument("--phase", choices=("base", "all", "units"), default="all")
    parser.add_argument("--verify", action="store_true")
    parser.add_argument("--output", type=Path, default=PLATFORM / "results/monthly_frequency_attribution")
    args = parser.parse_args()
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=True)
    os.chdir(PLATFORM)
    configs, provenance = prepare(output)
    initialize(output)
    generated = PLATFORM / "results/configs/monthly_frequency_attribution" / ref.digest(provenance)[:12]
    generated.mkdir(parents=True, exist_ok=True)
    for name, config in configs.items():
        (generated / f"{name}.yaml").write_text(yaml.safe_dump(config, allow_unicode=True, sort_keys=False), encoding="utf-8")
    cases = tasks(configs, provenance, output, args.phase)
    rows = []
    with ProcessPoolExecutor(args.workers, initializer=initialize, initargs=(output,)) as pool:
        futures = [pool.submit(run_case, task) for task in cases]
        for f in as_completed(futures):
            rows.append(f.result())
            if len(rows) % 40 == 0 or len(rows) == len(cases):
                print(f"runs {len(rows)}/{len(cases)}", flush=True)
    summarize(rows, output)
    checks = verify(rows, cases, output) if args.verify else []
    evidence = json.loads((output / "evidence.json").read_text(encoding="utf-8"))
    evidence["verification"] = checks
    for row in evidence["runs"]:
        row.pop("artifact", None)
    (output / "evidence.json").write_text(json.dumps(evidence, ensure_ascii=False, indent=2, allow_nan=False), encoding="utf-8")
    render(rows, output)
    print(f"独立校验完成: {len(checks)}", flush=True)


if __name__ == "__main__":
    main()
