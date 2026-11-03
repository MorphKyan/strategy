"""月末均线确认期与缓冲带的配对验证。"""
import argparse
import copy
import importlib.util
import json
import os
import sys
import subprocess
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

for variable in ("OPENBLAS_NUM_THREADS", "OMP_NUM_THREADS", "MKL_NUM_THREADS"):
    os.environ[variable] = "1"
ROOT = Path(__file__).resolve().parents[4]
spec = importlib.util.spec_from_file_location(
    "bond_reference", ROOT / "platform/reports/bond_daily_mixed_rebalance/20261102/reproduce.py"
)
ref = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = ref
spec.loader.exec_module(ref)
from src.platform_core.models import TargetPortfolio

RATIOS = {}


class MonthlyTrend(ref.ResearchStrategy):
    name = "research_monthly_trend_confirmation"

    def should_check_rebalance(self, context):
        return ref.Strategy.should_check_rebalance(self, context)

    def _inverse_vol_target(self, context, universe):
        target = super()._inverse_vol_target(context, universe)
        if target is None:
            return None
        params = context.params
        ratios = RATIOS[params["research_universe"]]
        today = str(context.date)
        ratio = ratios.loc[today, universe].to_numpy()
        raw = ratio >= 1
        held = context.runtime.get("held_trend", raw)
        mode = params["research_mode"]
        if mode.startswith("band"):
            band = int(mode[4:]) / 100
            trend = ref.np.where(ratio > 1 + band, True, ref.np.where(ratio < 1 - band, False, held))
        else:
            days = int(mode[7:])
            history = ratios.loc[:today, universe].tail(days).to_numpy()
            trend = ref.np.where(((history >= 1) == raw).all(axis=0), raw, held)
        context.runtime["held_trend"] = trend.tolist()
        scale = params["trend_filter_scale_down"]
        weights = [target.weights[aid] for aid in universe]
        return TargetPortfolio(dict(zip(universe, map(float,
            weights / ref.np.where(raw, 1., scale) * ref.np.where(trend, 1., scale)
        ))))


def initialize(output):
    ref.initialize(output / "signals.json")
    ref.BUILTIN_STRATEGIES[MonthlyTrend.name] = MonthlyTrend
    for name in ref.CONFIGS:
        RATIOS[name] = ref.pd.read_csv(output / f"{name}_ratio.csv", index_col=0, float_precision="round_trip")


def run(task):
    name, mode, scenario, phase, start, end, path, output = task
    config = ref.yaml.safe_load(path.read_text(encoding="utf-8"))
    config["backtest"].update(start_date=start, end_date=end)
    config["platform"]["run_name"] = f"{name}_{mode}_{phase}_{start}"
    config = ref.apply_slippage_scenario(config, scenario)
    store = ref.InMemoryStore()
    try:
        result = ref.PlatformBacktestEngine(config, store, output_dir=output / "raw").run()
        row = json.loads((result.output_dir / "manifest.json").read_text(encoding="utf-8"))["metrics"]
        trades = result.output_dir / "trades.csv"
        if trades.stat().st_size:
            filled = ref.pd.read_csv(trades)
            assert (filled.signal_date < filled.date).all()
            row["first_trade"] = filled.date.min()
        ref.shutil.rmtree(result.output_dir)
        return dict(row, universe=name, mode=mode, scenario=scenario, phase=phase, runtime_start=start)
    finally:
        store.close()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--workers", type=int, default=8)
    parser.add_argument("--run-id", default="full")
    args = parser.parse_args()
    key = "monthly_trend_confirmation"
    output = ref.PLATFORM / "results/sensitivity" / key / args.run_id
    config_dir = ref.PLATFORM / "results/configs" / key / args.run_id
    output.mkdir(parents=True, exist_ok=True)
    config_dir.mkdir(parents=True, exist_ok=True)
    configs, provenance = ref.prepare(output)
    provenance["code"][str(Path(__file__).relative_to(ROOT))] = ref.hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    modes = [f"confirm{n}" for n in range(1, 6)] + [f"band{n}" for n in range(1, 6)]
    tasks, skipped = [], []
    for name, base in configs.items():
        data = ref.LocalCsvBarData(base["data"]["data_dir"], ref.assets_from_config(base["assets"]))
        calendar = ref.pd.DatetimeIndex(data.calendar)
        prices = data.get_price_frame(base["strategy"]["params"]["universe"], data.calendar[-1])
        (prices / prices.rolling(200).mean()).to_csv(output / f"{name}_ratio.csv")
        starts = ref.pd.Series(calendar).groupby(calendar.to_period("M")).first()
        month_ends = {i for i in range(len(calendar) - 1) if calendar[i].month != calendar[i + 1].month}
        windows = [("full", calendar[0])]
        for start in starts:
            offset = calendar.get_loc(start)
            if any(i >= offset + 252 for i in month_ends):
                windows.append(("sensitivity", start))
            else:
                skipped.append(dict(universe=name, runtime_start=str(start.date())))
        for mode in modes:
            config = copy.deepcopy(base)
            config["strategy"]["strategy_name"] = MonthlyTrend.name
            config["strategy"]["params"].update(rebalance_frequency="monthly", research_mode=mode, research_universe=name)
            config["platform"]["run_name"] = f"{name}_{mode}"
            path = config_dir / f"{name}_{mode}.yaml"
            path.write_text(ref.yaml.safe_dump(config, allow_unicode=True), encoding="utf-8")
            for phase, start in windows:
                for scenario in ("default", "stress"):
                    tasks.append((name, mode, scenario, phase, str(start.date()), str(calendar[-1].date()), path, output))
    (output / "provenance.json").write_text(json.dumps(provenance, ensure_ascii=False, indent=2), encoding="utf-8")
    (output / "skipped.json").write_text(json.dumps(skipped, indent=2), encoding="utf-8")
    print(f"{len(tasks)} runs, {len(skipped)} ineligible monthly starts", flush=True)
    rows = []
    with ProcessPoolExecutor(args.workers, initializer=initialize, initargs=(output,)) as pool:
        for row in pool.map(run, tasks, chunksize=1):
            rows.append(row)
            if len(rows) % 40 == 0:
                print(f"{len(rows)}/{len(tasks)}", flush=True)
                ref.pd.DataFrame(rows).to_csv(output / "metrics.csv", index=False)
    ref.pd.DataFrame(rows).to_csv(output / "metrics.csv", index=False)
    subprocess.run([sys.executable, str(Path(__file__).with_name('summarize.py')), str(output)], check=True)


if __name__ == "__main__":
    main()
