"""复现 ES 修正、明确的资产 ES 对照与两个月起点敏感性。"""
from __future__ import annotations

import argparse
import copy
import hashlib
import io
import json
import math
import os
from pathlib import Path
import subprocess
import sys
import tarfile
from concurrent.futures import ProcessPoolExecutor, as_completed
from datetime import date

import pandas as pd
import yaml

ROOT = Path(__file__).resolve().parents[4]
PLATFORM = ROOT / "platform"
OLD = "ae3930a"
CONFIGS = {
    "factor_es": "index_benchmark/domestic_macro_factor_es_index_benchmark_100k.yaml",
    "constrained_es": "capital_100k/es_252d_fhs_constrained_100k.yaml",
    "constrained_trend_es": "capital_100k/es_252d_fhs_constrained_stepdown_trend_100k.yaml",
}


def fingerprint(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, default=str).encode()).hexdigest()


def initialize(source):
    os.chdir(PLATFORM)
    sys.path.insert(0, str(source))


def run_case(task):
    from src.platform_core.engine import PlatformBacktestEngine
    from src.platform_core.slippage import apply_slippage_scenario
    from src.platform_core.storage import InMemoryStore

    config = copy.deepcopy(task["config"])
    config["data"] = {"data_dir": str(PLATFORM / "data"), "fetch": False}
    config["platform"] = {"run_name": task["id"][:18]}
    config["backtest"] = {"start_date": task["start"], "end_date": task["end"],
                          "enable_checkpoints": False, "enable_database": False}
    config["strategy"].pop("strategy_version_id", None)
    config = apply_slippage_scenario(config, task["scenario"])
    row = {k: task[k] for k in ("id", "variant", "revision", "phase", "start", "end", "scenario")}
    try:
        store = InMemoryStore()
        try:
            result = PlatformBacktestEngine(config, store, output_dir=task["raw"]).run()
        finally:
            store.close()
        manifest = json.loads((result.output_dir / "manifest.json").read_text(encoding="utf-8"))
        row.update(status="ok", metrics=manifest["metrics"])
    except Exception as exc:
        row.update(status="error", error=f"{type(exc).__name__}: {exc}")
    return row


def source_tree(revision, output):
    if revision == "current":
        return PLATFORM
    parent = output / "code" / revision
    if not (parent / "platform/src/platform_core/engine.py").exists():
        archive = subprocess.check_output(["git", "archive", revision, "platform/src"], cwd=ROOT)
        parent.mkdir(parents=True, exist_ok=True)
        with tarfile.open(fileobj=io.BytesIO(archive)) as handle:
            handle.extractall(parent, filter="data")
    # 旧引擎的企业行为入口从模块根目录读取；只复制两份小表。
    import shutil
    data = parent / "platform/data"
    data.mkdir(exist_ok=True)
    for name in ("platform_dividends.csv", "platform_splits.csv"):
        shutil.copyfile(PLATFORM / "data" / name, data / name)
    return parent / "platform"


def tasks(output, phase):
    configs = {name: yaml.safe_load((PLATFORM / "configs" / path).read_text(encoding="utf-8"))
               for name, path in CONFIGS.items()}
    control = copy.deepcopy(configs["factor_es"])
    control["strategy"]["strategy_name"] = "risk_parity_expected_shortfall_fixed_budget"
    control["strategy"]["params"].pop("lambda_beta", None)
    control["strategy"]["params"]["es_method"] = "historical"
    configs["asset_es_control"] = control
    source_hash = fingerprint({p.relative_to(PLATFORM).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
                               for p in sorted((PLATFORM / "src").rglob("*.py"))})
    data_hash = fingerprint({p.relative_to(PLATFORM).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
                             for p in sorted((PLATFORM / "data").rglob("*.csv"))})
    generated = PLATFORM / "results/configs/es_implementation_correction" / source_hash[:12]
    generated.mkdir(parents=True, exist_ok=True)
    for name, config in configs.items():
        (generated / f"{name}.yaml").write_text(yaml.safe_dump(config, allow_unicode=True, sort_keys=False), encoding="utf-8")
        dates = []
        for asset in config["assets"]:
            frame = pd.read_csv(PLATFORM / "data" / f"{asset['code']}.csv", usecols=["trade_date"])
            dates.append(set(frame.trade_date))
        latest = [max(days) for days in dates]
        if len(set(latest)) != 1 or not 0 <= (date.today() - date.fromisoformat(latest[0])).days <= 7:
            raise RuntimeError(f"Stale or unaligned market data: {name}: {latest}")
        calendar = sorted(set.intersection(*dates))
        start, end = calendar[0], calendar[-1]
        windows = [("base", start, end)]
        if name in ("factor_es", "asset_es_control"):
            windows.append(("original_window", "2014-01-20", "2026-08-03"))
        for anchor in pd.date_range(pd.Timestamp(start), pd.Timestamp(end), freq=pd.DateOffset(months=2)):
            origin = next((day for day in calendar if day >= anchor.date().isoformat()), None)
            if origin:
                windows.append(("sensitivity", origin, end))
        for revision in (OLD, "current"):
            for kind, left, right in windows:
                if phase != "all" and ("base" if kind == "original_window" else kind) != phase:
                    continue
                for scenario in ("default", "stress"):
                    task = dict(variant=name, revision=revision, phase=kind, start=left, end=right,
                                scenario=scenario, config=config, data_hash=data_hash,
                                source_hash=source_hash if revision == "current" else revision,
                                runner_hash=hashlib.sha256(Path(__file__).read_bytes()).hexdigest())
                    task["id"] = fingerprint(task)
                    task["raw"] = str(output / "raw" / task["id"])
                    yield task


def summarize(output):
    manifest = json.loads((output / "task_manifest.json").read_text(encoding="utf-8"))
    valid = {task["id"] for task in manifest}
    records = [json.loads(p.read_text(encoding="utf-8")) for p in sorted((output / "completed").glob("*.json")) if p.stem in valid]
    rows = [{**{k: v for k, v in r.items() if k != "metrics"}, **r.get("metrics", {})} for r in records]
    frame = pd.DataFrame(rows)
    frame.to_csv(output / "metrics.csv", index=False, encoding="utf-8-sig")
    sensitivity = frame[(frame.phase == "sensitivity") & (frame.status == "ok")]
    if "active_observations" not in sensitivity:
        print(frame.groupby(["revision", "phase", "status"]).size().to_string(), flush=True)
        return
    sensitivity = sensitivity[sensitivity.active_observations >= 126]
    stats = sensitivity.groupby(["variant", "revision", "scenario"]).agg(
        origins=("id", "size"), median_active_sharpe=("active_sharpe_ratio", "median"),
        min_active_sharpe=("active_sharpe_ratio", "min"), max_active_sharpe=("active_sharpe_ratio", "max"),
        median_active_return=("annualized_return_active", "median"), worst_drawdown=("max_drawdown", "min"))
    stats.to_csv(output / "sensitivity_summary.csv", encoding="utf-8-sig")
    keys = ["variant", "phase", "start", "end", "scenario"]
    old, new = (frame[frame.revision == revision] for revision in (OLD, "current"))
    paired = old.merge(new, on=keys, suffixes=("_old", "_current"), validate="one_to_one")
    for metric in ("total_return", "annualized_return", "annualized_return_active", "annualized_volatility",
                   "sharpe_ratio", "active_sharpe_ratio", "max_drawdown", "annualized_turnover",
                   "trade_count", "order_count", "rejected_order_count", "fee_total", "execution_slippage"):
        paired[f"delta_{metric}"] = paired[f"{metric}_current"] - paired[f"{metric}_old"]
    paired["valid_active_pair"] = (paired.active_observations_old >= 126) & (paired.active_observations_current >= 126)
    paired.to_csv(output / "code_comparison.csv", index=False, encoding="utf-8-sig")
    ranking = frame[frame.variant == "factor_es"].merge(
        frame[frame.variant == "asset_es_control"], on=["revision", "phase", "start", "end", "scenario"],
        suffixes=("_factor", "_control"), validate="one_to_one")
    ranking["sharpe_edge"] = ranking.sharpe_ratio_factor - ranking.sharpe_ratio_control
    ranking["active_sharpe_edge"] = ranking.active_sharpe_ratio_factor - ranking.active_sharpe_ratio_control
    ranking["valid_active_pair"] = (ranking.active_observations_factor >= 126) & (ranking.active_observations_control >= 126)
    ranking.to_csv(output / "factor_vs_asset_es.csv", index=False, encoding="utf-8-sig")
    print(frame.groupby(["revision", "phase", "status"]).size().to_string(), flush=True)


def verify_cases(output):
    expected = list(tasks(output, "all"))
    manifest = json.loads((output / "task_manifest.json").read_text(encoding="utf-8"))
    if {t["id"] for t in manifest} != {t["id"] for t in expected}:
        raise RuntimeError("Inputs/code/data changed; run the full entry before reproduction checks.")
    initialize(PLATFORM)
    checks = []
    for task in expected:
        if (task["revision"], task["phase"], task["scenario"]) != ("current", "base", "default"):
            continue
        previous = json.loads((output / "completed" / f"{task['id']}.json").read_text(encoding="utf-8"))
        task = {**task, "raw": str(output / "reproduction_probe" / task["id"])}
        fresh = run_case(task)
        if fresh["status"] != "ok" or previous["status"] != "ok":
            raise RuntimeError(f"Reproduction failed: {task['variant']}: {fresh.get('error')}")
        differences = {key: abs(value - fresh["metrics"][key]) for key, value in previous["metrics"].items()
                       if isinstance(value, (int, float)) and not isinstance(value, bool)}
        if any(not math.isclose(previous["metrics"][key], fresh["metrics"][key], rel_tol=1e-9, abs_tol=1e-9)
               for key in differences):
            raise RuntimeError(f"Reproduction metrics changed: {task['variant']}: {differences}")
        checks.append({"variant": task["variant"], "status": "ok", "absolute_differences": differences})
    (output / "reproduction_check.json").write_text(json.dumps(checks, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"{len(checks)} independent reproduction checks passed", flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--phase", choices=("all", "base", "sensitivity", "summary", "check"), default="all")
    parser.add_argument("--workers", type=int, default=8)
    parser.add_argument("--output", type=Path, default=PLATFORM / "results/temporary_backtests/es_correction")
    args = parser.parse_args()
    output = args.output.resolve()
    (output / "completed").mkdir(parents=True, exist_ok=True)
    if args.phase == "check":
        verify_cases(output)
        return
    if args.phase != "summary":
        all_tasks = list(tasks(output, "all"))
        (output / "task_manifest.json").write_text(json.dumps(all_tasks, ensure_ascii=False, indent=2), encoding="utf-8")
        for revision in (OLD, "current"):
            pending = [t for t in all_tasks if t["revision"] == revision
                       and (args.phase == "all" or ("base" if t["phase"] == "original_window" else t["phase"]) == args.phase)
                       and not (output / "completed" / f"{t['id']}.json").exists()]
            print(f"{revision}: {len(pending)} pending", flush=True)
            if not pending:
                continue
            source = source_tree(revision, output)
            with ProcessPoolExecutor(max_workers=args.workers, initializer=initialize, initargs=(source,)) as pool:
                futures = [pool.submit(run_case, t) for t in pending]
                for count, future in enumerate(as_completed(futures), 1):
                    result = future.result()
                    (output / "completed" / f"{result['id']}.json").write_text(json.dumps(result, ensure_ascii=False), encoding="utf-8")
                    if count % 10 == 0 or result["status"] != "ok":
                        print(f"{revision} {count}/{len(pending)} {result['variant']} {result['status']} {result.get('error', '')}", flush=True)
    summarize(output)
    if args.phase == "all":
        records = [json.loads((output / "completed" / f"{t['id']}.json").read_text(encoding="utf-8")) for t in all_tasks]
        if any(r["status"] != "ok" for r in records):
            raise RuntimeError("Some cases failed; inspect metrics.csv before drawing conclusions.")
        verify_cases(output)


if __name__ == "__main__":
    main()
