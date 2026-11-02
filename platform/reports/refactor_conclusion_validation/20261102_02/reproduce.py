"""重跑重构影响配置；所有运行产物写入 results，历史证据只读。

默认执行版本对照、历史窗口、两个月起点、专项诊断及复现检查；可用 --phase 分批续跑。
"""
from __future__ import annotations

import argparse
import copy
import hashlib
import gzip
import io
import importlib.util
import json
import math
import os
import re
import shutil
from pathlib import Path
import subprocess
import sys
import tarfile
import time
from concurrent.futures import ProcessPoolExecutor, as_completed
from datetime import date
from functools import lru_cache

import pandas as pd
import yaml

REPO = Path(__file__).resolve().parents[4]
PLATFORM = REPO / "platform"
CORE_METRICS = ["total_return", "annualized_return", "annualized_return_active",
                "annualized_volatility", "sharpe_ratio", "active_sharpe_ratio", "max_drawdown",
                "annualized_turnover", "trade_count", "order_count", "rejected_order_count",
                "turnover_amount_total", "turnover_quantity_total", "fee_total", "execution_slippage",
                "average_cash_weight", "max_pending_intent_count", "pending_intent_count"]
BEHAVIOR_METRICS = ("total_return", "max_drawdown", "trade_count", "order_count", "fee_total", "execution_slippage")
BASE_REVISIONS = ("current", "7cd3ca2", "27a8dce", "6692e66")


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False, default=str).encode()).hexdigest()


def code_identity():
    head = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=REPO, text=True).strip()
    scopes = ("platform/src", "platform/scripts", "etf_selection/src", "etf_selection/scripts")
    changed = subprocess.check_output(["git", "status", "--porcelain", "--untracked-files=normal", "--", *scopes], cwd=REPO)
    if not changed.strip():
        return head
    files = {p.relative_to(REPO).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
             for scope in scopes for p in (REPO / scope).rglob("*.py")}
    return f"{head}+worktree-{digest(files)}"


def current_records(plan, output):
    rows = [json.loads(p.read_text(encoding="utf-8")) for p in (output / "completed").glob("*.json")]
    return [r for r in rows if r["config_id"] in plan["jobs"] and r["id"] == digest([r["config_id"], r["revision"], r["scenario"], r["start"],
                                                  r["end"], plan["data_hash"], plan["code"]])]


def read(path):
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def canonical(payload):
    """只迁移单段旧格式，不猜测多段调度含义，日期仍保留在 backtest。"""
    cfg = copy.deepcopy(payload)
    if not cfg.get("strategy"):
        segments = (cfg.get("strategies") or {}).get("segments", [])
        if len(segments) != 1:
            raise ValueError("requires exactly one strategy segment")
        segment = dict(segments[0])
        backtest = cfg.setdefault("backtest", {})
        for key in ("start_date", "end_date"):
            value = segment.pop(key, None)
            if value and not backtest.get(key):
                backtest[key] = value
        cfg["strategy"] = segment
    cfg.pop("strategies", None)
    for key in ("platform", "output", "selection_metadata", "baseline_config"):
        cfg.pop(key, None)
    cfg.get("strategy", {}).pop("strategy_version_id", None)
    backtest = cfg.setdefault("backtest", {})
    for key in ("enable_checkpoints", "enable_database"):
        backtest.pop(key, None)
    return cfg


def inventory(output):
    paths = []
    for directory in ("platform/configs", "platform/reports", "etf_selection/reports",
                      "etf_selection/results/configs", "etf_selection/configs"):
        paths.extend((REPO / directory).rglob("*.yaml"))
    paths.extend(p for p in (PLATFORM / "results").rglob("*.yaml")
                 if not any(part in p.parts for part in ("live_portfolios", "sim_portfolios", "live_rebuilds", "live_cycle_runs", "refactor_validation")))
    entries, jobs = [], {}
    for path in sorted(set(paths)):
        rel = path.relative_to(REPO).as_posix()
        entry = {"path": rel, "sha256": hashlib.sha256(path.read_bytes()).hexdigest()}
        payload = read(path)
        if not payload.get("assets") or not (payload.get("strategy") or payload.get("strategies")):
            entry["status"] = "non_backtest_input"
            entries.append(entry)
            continue
        try:
            cfg = canonical(payload)
        except ValueError as exc:
            entry.update(status="unsupported_schema", error=str(exc))
            entries.append(entry)
            continue
        historical = path.name == "config_snapshot.yaml"
        ident = digest(cfg)
        entry.update(status="planned", config_id=ident, historical=historical)
        job = jobs.setdefault(ident, {"config": cfg, "sources": [], "baselines": [], "primary": False})
        job["sources"].append(rel)
        job["primary"] |= not historical
        if historical and (path.parent / "manifest.json").exists():
            old = json.loads((path.parent / "manifest.json").read_text(encoding="utf-8"))
            if old.get("metrics"):
                job["baselines"].append({"path": (path.parent / "manifest.json").relative_to(REPO).as_posix(),
                                         "metrics": old["metrics"]})
        entries.append(entry)
    data = {}
    for path in sorted((PLATFORM / "data").rglob("*")):
        if path.is_file() and path.suffix == ".csv":
            data[path.relative_to(PLATFORM).as_posix()] = hashlib.sha256(path.read_bytes()).hexdigest()
    plan = {"code": code_identity(),
            "date": date.today().isoformat(), "data_hash": digest(data), "data_files": data,
            "entries": entries, "jobs": jobs}
    output.mkdir(parents=True, exist_ok=True)
    (output / "plan.json").write_text(json.dumps(plan, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"inventory: {len(entries)} files, {len(jobs)} configurations, {sum(j['primary'] for j in jobs.values())} primary", flush=True)
    return plan


def source_tree(revision, output):
    if revision == "current":
        return PLATFORM
    root = output / "code" / revision
    if not (root / "platform/src/platform_core/engine.py").exists():
        archive = subprocess.check_output(["git", "archive", revision, "platform/src"], cwd=REPO)
        root.mkdir(parents=True, exist_ok=True)
        with tarfile.open(fileobj=io.BytesIO(archive)) as handle:
            handle.extractall(root, filter="data")
    # 历史引擎从模块根目录读取除权表，必须给它同一份数据快照。
    shutil.copytree(PLATFORM / "data", root / "platform/data", dirs_exist_ok=True)
    return root / "platform"


def init_worker(source):
    os.chdir(PLATFORM)
    sys.path.insert(0, str(source))


def worker(task):
    from src.platform_core.engine import PlatformBacktestEngine
    from src.platform_core.storage import InMemoryStore
    from src.platform_core.slippage import apply_slippage_scenario
    from src.platform_core.strategy import get_strategy_class
    result = {k: task[k] for k in ("id", "config_id", "revision", "scenario", "phase", "start", "end")}
    started = time.monotonic()
    try:
        cfg = copy.deepcopy(task["config"])
        calendar(cfg)
        get_strategy_class(cfg["strategy"]["strategy_name"])
        cfg.setdefault("platform", {})["run_name"] = task["id"][:18]
        cfg.setdefault("data", {})["data_dir"] = str(PLATFORM / "data")
        cfg["data"]["fetch"] = False
        if cfg["data"].get("market_store_dir"):
            cfg["data"]["market_store_dir"] = str(PLATFORM / "data")
        cfg.setdefault("backtest", {}).update(enable_database=False, enable_checkpoints=False)
        for key in ("start_date", "end_date"):
            value = task["start" if key == "start_date" else "end"]
            if value:
                cfg["backtest"][key] = value
        cfg = apply_slippage_scenario(cfg, task["scenario"])
        # 修复前版本使用单段调度；仅在引擎确实要求旧格式时适配。
        import inspect
        if "load_strategy_config(config.get" not in inspect.getsource(PlatformBacktestEngine.__init__):
            seg = cfg.pop("strategy")
            seg.update(start_date=cfg["backtest"].get("start_date"), end_date=None)
            cfg["strategies"] = {"segments": [seg]}
        store = InMemoryStore()
        try:
            run = PlatformBacktestEngine(cfg, store, output_dir=task["raw"]).run()
        finally:
            store.close()
        manifest = json.loads((run.output_dir / "manifest.json").read_text(encoding="utf-8"))
        result.update(status="ok", metrics=manifest["metrics"], raw=str(run.output_dir),
                      artifact_hashes={name: hashlib.sha256((run.output_dir / name).read_bytes()).hexdigest()
                                       for name in ("nav.csv", "trades.csv", "orders.csv", "positions.csv")})
    except Exception as exc:
        result.update(status="error", error_type=type(exc).__name__, error=str(exc)[:800])
    result["seconds"] = round(time.monotonic() - started, 3)
    return result


@lru_cache(maxsize=256)
def market_dates(codes):
    frames = [pd.read_csv(PLATFORM / "data" / f"{a['code']}.csv", usecols=["trade_date"])["trade_date"]
              for a in ({"code": code} for code in codes)]
    return tuple(sorted(set.intersection(*(set(f) for f in frames)))), tuple(str(f.max()) for f in frames)


def calendar(cfg):
    days, all_latest = market_dates(tuple(a['code'] for a in cfg["assets"]))
    latest = set(all_latest)
    if len(latest) != 1 or not 0 <= (date.today() - date.fromisoformat(next(iter(latest)))).days <= 7:
        raise RuntimeError("market data stale or unaligned")
    bt = cfg.get("backtest", {})
    return [d for d in days if (not bt.get("start_date") or d >= bt["start_date"])
            and (not bt.get("end_date") or d <= bt["end_date"])]


def tasks_for(plan, args):
    tasks = []
    changed_ids = None
    if getattr(args, "changed_only", False):
        records = current_records(plan, args.output)
        current = {(r["config_id"], r["scenario"], r["start"], r["end"]): r for r in records
                   if r["revision"] == "current" and r["status"] == "ok"}
        changed_ids = set()
        changed_ids.update(cid for cid, job in plan["jobs"].items()
                           if job["primary"] and job["config"]["strategy"]["strategy_name"] == "risk_parity_black_litterman")
        for old in records:
            key = (old["config_id"], old["scenario"], old["start"], old["end"])
            new = current.get(key)
            if old["revision"] != "6692e66" or old["phase"] != "base" or old["status"] != "ok" or not new:
                continue
            if any(isinstance(old["metrics"].get(k), (float, int)) and isinstance(new["metrics"].get(k), (float, int))
                   and not math.isclose(old["metrics"][k], new["metrics"][k], rel_tol=1e-9, abs_tol=1e-9)
                   for k in BEHAVIOR_METRICS):
                changed_ids.add(old["config_id"])
    for config_id, job in plan["jobs"].items():
        if changed_ids is not None and config_id not in changed_ids:
            continue
        if args.phase in ("base", "sensitivity") and not job["primary"] and job["baselines"]:
            continue
        if args.phase == "history" and not job["baselines"]:
            continue
        cfg = job["config"]
        bt = cfg.get("backtest", {})
        start, end = bt.get("start_date"), bt.get("end_date")
        starts = [start]
        if args.phase == "history":
            # 旧快照有时没有写入实际日期，使用其真实运行指标锁定原样本。
            m = job["baselines"][0]["metrics"]
            start, end = m.get("start_date"), m.get("end_date")
            starts = [start]
        elif args.phase == "sensitivity":
            try:
                dates = pd.DatetimeIndex(pd.to_datetime(calendar(cfg)))
                anchors = pd.date_range(dates[0], dates[-1], freq=pd.DateOffset(months=2))
                starts = sorted({dates[i].date().isoformat() for i in dates.searchsorted(anchors) if i < len(dates)})
                end = dates[-1].date().isoformat()
            except Exception:
                starts = [start]  # 引擎给出逐配置的真实阻断原因。
        scenarios = ["default", "stress"]
        if args.phase == "history":
            old_scenario = (cfg.get("execution") or {}).get("slippage_scenario", "default")
            scenarios = [old_scenario] if old_scenario in ("default", "stress", "dynamic_participation") else ["default"]
        windows = [(value, end) for value in starts]
        if args.phase == "history":
            windows = sorted({(b["metrics"].get("start_date"), b["metrics"].get("end_date"))
                              for b in job["baselines"]}, key=str)
        for scenario in scenarios:
            for runtime_start, runtime_end in windows:
                identity = [config_id, args.revision, scenario, runtime_start, runtime_end, plan["data_hash"], plan["code"]]
                ident = digest(identity)
                tasks.append(dict(id=ident, config_id=config_id, revision=args.revision, scenario=scenario,
                                  phase=args.phase, start=runtime_start, end=runtime_end, config=cfg,
                                  raw=str(args.output / "raw" / args.revision / ident)))
    return tasks


def execute(plan, args):
    source = source_tree(args.revision, args.output)
    tasks = tasks_for(plan, args)
    results_dir = args.output / "completed"
    results_dir.mkdir(exist_ok=True)
    tasks = [task for task in tasks if not (results_dir / f"{task['id']}.json").exists()]
    print(f"{args.phase}/{args.revision}: {len(tasks)} pending", flush=True)
    with ProcessPoolExecutor(max_workers=args.workers, initializer=init_worker, initargs=(source,)) as pool:
        futures = {pool.submit(worker, task): task for task in tasks}
        for index, future in enumerate(as_completed(futures), 1):
            result = future.result()
            temporary = results_dir / f"{result['id']}.tmp"
            temporary.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
            temporary.replace(results_dir / f"{result['id']}.json")
            if index % 20 == 0 or result["status"] != "ok" or index == len(futures):
                print(f"{index}/{len(futures)} {result['status']} {result.get('error', '')[:150]}", flush=True)


def summarize(plan, output):
    rows = current_records(plan, output)
    for row in rows:
        if row["phase"] == "history" and row["status"] == "ok":
            actual = (row["metrics"].get("start_date"), row["metrics"].get("end_date"))
            requested = (row["start"], row["end"])
            if actual != requested:
                row.update(status="window_mismatch", error=f"历史原窗口 {requested}，当前实际可得窗口 {actual}；不能按同窗复现比较")
    # 老版本 manifest 没有年化收益与 Sharpe；从真实流水按当前统一口径重算，保留原指标。
    sys.path.insert(0, str(PLATFORM))
    from src.platform_core.metrics import compute_period_metrics, read_csv_or_empty
    harmonized_dir = output / "harmonized_metrics"
    harmonized_dir.mkdir(exist_ok=True)
    for row in rows:
        if row["status"] != "ok" or row["revision"] != "6692e66":
            continue
        path = harmonized_dir / f"{row['id']}.json"
        if path.exists():
            audited = json.loads(path.read_text(encoding="utf-8"))
        else:
            raw = Path(row["raw"])
            audited = compute_period_metrics(*(read_csv_or_empty(raw / name) for name in
                                                ("nav.csv", "trades.csv", "orders.csv", "skipped_orders.csv", "positions.csv")))
            path.write_text(json.dumps(audited, ensure_ascii=False, indent=2), encoding="utf-8")
        row["original_metrics"] = row["metrics"]
        row["metrics"] = audited
    by = {(r["config_id"], r["scenario"], r["start"], r["end"], r["revision"]): r
          for r in rows if r["status"] == "ok"}
    comparisons, details = [], []
    for row in rows:
        job = plan["jobs"][row["config_id"]]
        item = {k: row.get(k) for k in ("id", "config_id", "revision", "phase", "scenario", "start", "end", "status", "error")}
        item["source"] = job["sources"][0]
        item.update({k: row.get("metrics", {}).get(k) for k in CORE_METRICS})
        details.append(item)
        if row["revision"] != "current" or row["status"] != "ok":
            continue
        candidates = []
        for revision in BASE_REVISIONS[1:]:
            old = by.get((row["config_id"], row["scenario"], row["start"], row["end"], revision))
            if old:
                candidates.append((revision, old["metrics"], old.get("original_metrics", old["metrics"])))
        if job["baselines"]:
            for baseline in job["baselines"]:
                m = baseline["metrics"]
                if m.get("start_date") == row["start"] and m.get("end_date") == row["end"]:
                    candidates.append((baseline["path"], m, m))
        for label, old_metrics, originally_reported in candidates:
            common = [k for k in CORE_METRICS if isinstance(old_metrics.get(k), (float, int))
                      and isinstance(row["metrics"].get(k), (float, int))]
            delta = {k: row["metrics"][k] - old_metrics[k] for k in common}
            changed = [k for k in common if not math.isclose(row["metrics"][k], old_metrics[k], rel_tol=1e-9, abs_tol=1e-9)]
            reported_changes = [k for k in CORE_METRICS if isinstance(originally_reported.get(k), (int, float))
                                and isinstance(row["metrics"].get(k), (int, float))
                                and not math.isclose(row["metrics"][k], originally_reported[k], rel_tol=1e-9, abs_tol=1e-9)]
            comparisons.append({"config_id": row["config_id"], "source": job["sources"][0],
                                "phase": row["phase"], "scenario": row["scenario"], "start": row["start"], "end": row["end"],
                                "baseline": label, "changed": bool(changed), "changed_keys": ",".join(changed),
                                "originally_reported_changed_keys": ",".join(reported_changes),
                                **{f"delta_{key}": value for key, value in delta.items()}})
    pd.DataFrame(details).to_csv(output / "runs_summary.csv", index=False, encoding="utf-8-sig")
    pd.DataFrame(comparisons).to_csv(output / "comparisons.csv", index=False, encoding="utf-8-sig")
    report_inputs = []
    all_by = {(r["config_id"], r["revision"], r["scenario"], r["start"], r["end"]): r for r in rows}
    for entry in plan["entries"]:
        if "/reports/" not in entry["path"] or not entry.get("config_id"):
            continue
        config_id = entry["config_id"]
        bt = plan["jobs"][config_id]["config"].get("backtest", {})
        for revision in BASE_REVISIONS:
            for scenario in ("default", "stress"):
                match = all_by.get((config_id, revision, scenario, bt.get("start_date"), bt.get("end_date")))
                item = {"input_path": entry["path"], "config_id": config_id, "revision": revision,
                        "scenario": scenario, "status": match["status"] if match else "missing"}
                if match:
                    item.update(match.get("metrics", {}))
                report_inputs.append(item)
    pd.DataFrame(report_inputs).to_csv(output / "report_input_metrics.csv", index=False, encoding="utf-8-sig")
    report_by = {(r["input_path"], r["revision"], r["scenario"]): r for r in report_inputs}
    execution_pairs = []
    for candidate in report_inputs:
        path = candidate["input_path"]
        if (candidate["revision"] != "current" or candidate["status"] != "ok"
                or "/platform_execution_validation/" not in path or "/optimized_execution/platform_basket_" not in path):
            continue
        baseline_path = str(Path(path).parent / "aligned_baselines" / Path(path).name.replace("platform_basket_", "baseline_aligned_for_")).replace("\\", "/")
        baseline = report_by.get((baseline_path, "current", candidate["scenario"]))
        item = {"candidate": path, "scenario": candidate["scenario"], "baseline": baseline_path,
                "status": baseline["status"] if baseline else "missing_baseline"}
        for key in CORE_METRICS:
            item[f"candidate_{key}"] = candidate.get(key)
            item[f"baseline_{key}"] = baseline.get(key) if baseline else None
        if baseline and baseline["status"] == "ok":
            item["delta_sharpe"] = candidate["sharpe_ratio"] - baseline["sharpe_ratio"]
            item["delta_annualized_return"] = candidate["annualized_return"] - baseline["annualized_return"]
        execution_pairs.append(item)
    pd.DataFrame(execution_pairs).to_csv(output / "etf_execution_comparison.csv", index=False, encoding="utf-8-sig")
    qdii_review(plan, output, rows)
    missing_references = []
    pattern = r"(?:(?:[A-Za-z]:/strategy/)?(?:platform|etf_selection)/)?configs/[A-Za-z0-9_./-]+\.ya?ml"
    for subsystem in ("platform", "etf_selection"):
        for report in (REPO / subsystem / "reports").rglob("*.md"):
            if "refactor_conclusion_validation" in report.parts:
                continue
            references = set(re.findall(pattern, report.read_text(encoding="utf-8").replace("\\", "/"), flags=re.IGNORECASE))
            for reference in sorted(references):
                path = Path(reference)
                candidates = [path] if path.is_absolute() else [report.parent / path, REPO / path, PLATFORM / path]
                if not any(p.is_file() for p in candidates):
                    missing_references.append({"report": report.relative_to(REPO).as_posix(), "reference": reference,
                                               "status": "historical_reference_unavailable"})
    pd.DataFrame(missing_references).to_csv(output / "missing_report_references.csv", index=False, encoding="utf-8-sig")
    counts = {}
    for row in rows:
        key = f"{row['phase']}/{row['revision']}/{row['status']}"
        counts[key] = counts.get(key, 0) + 1
    current_groups = {}
    for row in rows:
        if row["revision"] == "current":
            current_groups.setdefault(row["config_id"], []).append(row)
    input_rows = []
    for entry in plan["entries"]:
        cases = current_groups.get(entry.get("config_id"), [])
        good = sum(r["status"] == "ok" for r in cases)
        bad = len(cases) - good
        status = "not_backtest" if not entry.get("config_id") else "missing" if not cases else "unavailable" if not good else "partial" if bad else "executed"
        input_rows.append({"input_path": entry["path"], "sha256": entry["sha256"], "config_id": entry.get("config_id"),
                           "status": status, "current_cases": len(cases), "ok_cases": good, "failed_cases": bad,
                           "error_examples": " | ".join(sorted({r.get("error", "") for r in cases if r["status"] != "ok"}))})
    pd.DataFrame(input_rows).to_csv(output / "input_coverage.csv", index=False, encoding="utf-8-sig")
    present = {row["id"]: row for row in rows}
    coverage = {}
    sensitivity_rows = []
    for phase, revision, changed_only in (("base", "current", False), ("base", "7cd3ca2", False), ("base", "27a8dce", False),
                                           ("base", "6692e66", False), ("history", "current", False),
                                           ("sensitivity", "current", False), ("sensitivity", "6692e66", True)):
        selection = argparse.Namespace(phase=phase, revision=revision, output=output, changed_only=changed_only)
        planned = tasks_for(plan, selection)
        expected = {task["id"] for task in planned}
        coverage[f"{phase}/{revision}"] = {
            "expected": len(expected), "ok": sum(present[i]["status"] == "ok" for i in expected if i in present),
            "error": sum(present[i]["status"] != "ok" for i in expected if i in present),
            "missing": len(expected - present.keys())}
        if phase == "sensitivity":
            for task in planned:
                result = present.get(task["id"])
                item = {k: task[k] for k in ("id", "config_id", "revision", "scenario", "start", "end")}
                item.update(source=plan["jobs"][task["config_id"]]["sources"][0],
                            status=result["status"] if result else "missing")
                if result:
                    item.update(result.get("metrics", {}))
                sensitivity_rows.append(item)
    sensitivity_frame = pd.DataFrame(sensitivity_rows)
    for field in [*CORE_METRICS, "active_observations"]:
        if field not in sensitivity_frame:
            sensitivity_frame[field] = float("nan")
    sensitivity_frame.to_csv(output / "start_date_sensitivity.csv", index=False, encoding="utf-8-sig")
    summaries = []
    for (config_id, revision, scenario), frame in sensitivity_frame.groupby(["config_id", "revision", "scenario"]):
        valid = frame[(frame.status == "ok") & (frame.active_observations.fillna(0) >= 126)]
        item = {"config_id": config_id, "revision": revision, "scenario": scenario, "source": frame.source.iloc[0],
                "origins": len(frame), "ok_origins": int((frame.status == "ok").sum()), "valid_active_origins": len(valid)}
        for field in ("annualized_return_active", "active_sharpe_ratio", "max_drawdown", "annualized_turnover", "average_cash_weight"):
            item[f"median_{field}"] = valid[field].median() if len(valid) else None
            item[f"min_{field}"] = valid[field].min() if len(valid) else None
        summaries.append(item)
    pd.DataFrame(summaries).to_csv(output / "sensitivity_summary.csv", index=False, encoding="utf-8-sig")
    join_keys = ["config_id", "scenario", "start", "end"]
    paired = sensitivity_frame[sensitivity_frame.revision == "current"].merge(
        sensitivity_frame[sensitivity_frame.revision == "6692e66"], on=join_keys, suffixes=("_current", "_old"))
    paired["valid_pair"] = ((paired.status_current == "ok") & (paired.status_old == "ok")
                            & (paired.active_observations_current.fillna(0) >= 126) & (paired.active_observations_old.fillna(0) >= 126))
    for field in ("total_return", "annualized_return_active", "active_sharpe_ratio", "max_drawdown"):
        paired[f"delta_{field}"] = paired[f"{field}_current"] - paired[f"{field}_old"]
    paired.to_csv(output / "paired_sensitivity.csv", index=False, encoding="utf-8-sig")
    payload = {"counts": counts, "coverage": coverage, "input_config_groups": len(plan["jobs"]),
               "current_config_groups_attempted": len(current_groups),
               "unattempted_config_ids": sorted(plan["jobs"].keys() - current_groups.keys()),
               "comparisons": len(comparisons), "changed": sum(r["changed"] for r in comparisons)}
    (output / "summary.json").write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(payload, ensure_ascii=False), flush=True)


def qdii_review(plan, output, rows):
    from src.platform_core.data import LocalCsvBarData
    from src.platform_core.data_store import assets_from_config
    from src.platform_core.etf_premium import EtfPremiumStore
    premiums = EtfPremiumStore(PLATFORM / "data")
    windows = {}; prices = {}; failures = {}; details = []
    for row in rows:
        if row["revision"] != "current" or row["status"] != "ok":
            continue
        start, end = row["metrics"].get("start_date"), row["metrics"].get("end_date")
        if not start or not end:
            continue
        for asset in plan["jobs"][row["config_id"]]["config"]["assets"]:
            code = str(asset["code"])
            if code.startswith("513") or code in ("159920", "159941"):
                windows[(code, start, end)] = asset
    for (code, start, end), asset in sorted(windows.items()):
        item = dict(code=code, requested_start=start, requested_end=end)
        try:
            if code in failures:
                raise ValueError(failures[code])
            if code not in prices:
                premiums.load_premium_series(code)
                data = LocalCsvBarData(PLATFORM / "data", assets_from_config([asset]))
                prices[code] = data.frames[asset["asset_id"]]["adj_close"]
            history = premiums.observable_history(code, date.fromisoformat(end)).copy()
            history = history.loc[history.index >= date.fromisoformat(start)]
            if len(history) < 2:
                raise ValueError("扣除发布滞后后可观测配对样本不足")
            market = prices[code].reindex(history.index)
            if market.isna().any():
                raise ValueError("复权市价与可观测净值未对齐")
            periods = len(history) - 1
            item.update(status="ok", observed_start=str(history.index[0]), observed_end=str(history.index[-1]),
                        observations=len(history),
                        market_annualized_return=float((market.iloc[-1] / market.iloc[0]) ** (252 / periods) - 1),
                        nav_annualized_return=float((history.cum_nav.iloc[-1] / history.cum_nav.iloc[0]) ** (252 / periods) - 1),
                        premium_start=float(history.premium.iloc[0]), premium_end=float(history.premium.iloc[-1]))
        except Exception as exc:
            if code not in prices:
                failures[code] = str(exc)
            item.update(status="unverified", error=str(exc))
        details.append(item)
    pd.DataFrame(details).to_csv(output / "qdii_calibers.csv", index=False, encoding="utf-8-sig")


def self_check():
    old = {"assets": [{"code": "x"}], "strategies": {"segments": [{"strategy_name": "test", "start_date": "2020-01-01", "end_date": None, "params": {"x": 2}}]}}
    new = canonical(old)
    assert new["backtest"]["start_date"] == "2020-01-01"
    assert new["strategy"]["params"] == {"x": 2} and "strategies" in old
    assert digest(canonical(new)) == digest(new)
    try:
        canonical({"strategies": {"segments": [{}, {}]}})
    except ValueError:
        pass
    else:
        raise AssertionError("multi-segment must not be silently migrated")


def diagnostics(plan, args):
    """复核 R060 原窗口的统计诊断；先读完整新鲜行情，再按研究末日切片。"""
    sys.path.insert(0, str(PLATFORM))
    os.chdir(PLATFORM)
    import numpy as np
    from scripts.analyze_es_robustness import config_prices, diagnostic_rows, bootstrap_rows, tracking_summary
    asof = args.asof_date or "2026-08-12"
    target = args.output / "diagnostics" / asof
    target.mkdir(parents=True, exist_ok=True)
    if (target / "manifest.json").exists():
        previous = json.loads((target / "manifest.json").read_text(encoding="utf-8"))
        if previous.get("data_hash") == plan["data_hash"] and previous.get("code") == plan["code"]:
            print(f"diagnostics already completed: {target}", flush=True)
            return
    frames = {}; intervals = []; diagnostic_values = []; rng = np.random.default_rng(20260812)
    for proxy in ("etf_511090", "index_cba21801"):
        suffix = f"es_robustness_{proxy}_w120_historical.yaml"
        job = next(j for j in plan["jobs"].values() if any("/R060_" in s and s.endswith(suffix) for s in j["sources"]))
        prices, universe, budgets = config_prices(job["config"])
        prices = prices.loc[:asof]
        if prices.empty:
            raise ValueError(f"No diagnostic observations through {asof}")
        frames[proxy] = prices
        diagnostic_values.extend(diagnostic_rows(proxy, prices, universe, budgets, [120, 252, 500],
                                                  ["historical", "filtered"], 0.95, 0.94))
        intervals.extend(bootstrap_rows(proxy, prices, universe, budgets, [120, 252, 500],
                                        ["historical", "filtered"], 0.95, 0.94, 500, 10, rng))
    pd.DataFrame(diagnostic_values).to_csv(target / "rebalance_diagnostics.csv", index=False)
    pd.DataFrame(intervals).to_csv(target / "bootstrap_weight_intervals.csv", index=False)
    tracking = tracking_summary(frames["etf_511090"], frames["index_cba21801"])
    (target / "tracking_summary.json").write_text(json.dumps(tracking, ensure_ascii=False, indent=2), encoding="utf-8")
    review = {}
    for name, text in plan.get("diagnostic_baseline", {}).items():
        if name.endswith(".csv"):
            old = pd.read_csv(io.StringIO(text))
            new = pd.read_csv(target / name)
            compatible = old.shape == new.shape and old.columns.equals(new.columns)
            differences = {}
            if compatible:
                differences = {column: float((old[column].astype(float) - new[column].astype(float)).abs().max()) for column in old
                               if pd.api.types.is_numeric_dtype(old[column]) and pd.api.types.is_numeric_dtype(new[column])}
            review[name] = {"same_shape_and_columns": compatible, "maximum_absolute_differences": differences}
        else:
            review[name] = {"equal": json.loads(text) == tracking}
    (target / "comparison.json").write_text(json.dumps(review, ensure_ascii=False, indent=2), encoding="utf-8")
    (target / "manifest.json").write_text(json.dumps({"asof": asof, "data_hash": plan["data_hash"], "code": plan["code"],
                                                      "seed": 20260812, "bootstrap_reps": 500, "block_size": 10}, indent=2), encoding="utf-8")
    print(f"diagnostics completed: {target}", flush=True)


def screening(plan, args):
    target = args.output / "screening_review.json"
    if target.exists():
        runs = json.loads(target.read_text(encoding="utf-8"))
        valid = all(row.get("data_hash") == plan["data_hash"] and row.get("code") == plan["code"]
                    and row.get("config_sha256") == hashlib.sha256(Path(row["config"]).read_bytes()).hexdigest()
                    for row in runs)
        if valid and all("legacy_6692e66" in row for row in runs):
            print("ETF screening review already completed", flush=True)
            return
        if not valid:
            runs = []
    else:
        runs = []
    for name in (() if runs else ("etf_universe.yaml", "etf_universe_style_cross_market.yaml")):
        config = REPO / "etf_selection/configs" / name
        run = subprocess.run([sys.executable, str(REPO / "etf_selection/scripts/screen_etf_sleeves.py"),
                              "--config", str(config)], cwd=REPO, text=True, encoding="utf-8", errors="replace",
                             capture_output=True, check=True)
        match = re.search(r"ETF selection report written to: (.+)", run.stdout)
        if not match:
            raise RuntimeError("ETF screening did not identify its output directory")
        directory = Path(match.group(1).strip())
        summary = json.loads((directory / "summary.json").read_text(encoding="utf-8"))
        ranking = pd.read_csv(directory / "sleeve_rankings.csv")
        baskets = pd.read_csv(directory / "basket_scores.csv")
        runs.append({"config": str(config), "report_dir": str(directory), "summary": summary,
                     "data_hash": plan["data_hash"], "code": plan["code"],
                     "config_sha256": hashlib.sha256(config.read_bytes()).hexdigest(),
                     "rankings": json.loads(ranking.to_json(orient="records", force_ascii=False)),
                     "baskets": json.loads(baskets.to_json(orient="records", force_ascii=False))})
    source = args.output / "code/6692e66/etf_selection/src/selection.py"
    source.parent.mkdir(parents=True, exist_ok=True)
    source.write_bytes(subprocess.check_output(["git", "show", "6692e66:etf_selection/src/selection.py"], cwd=REPO))
    spec = importlib.util.spec_from_file_location("legacy_selection_6692e66", source)
    legacy = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = legacy
    spec.loader.exec_module(legacy)
    for row in runs:
        config = read(Path(row["config"]))
        config["paths"]["data_dir"] = str(PLATFORM / "data")
        calendar({"assets": [a for a in config["candidates"] if a.get("include", True)]})
        ranking, _, candidates = legacy.screen_sleeves(config, allow_raw_prices=False)
        baskets = legacy.build_baskets(config, ranking, candidates)[0]
        row["legacy_6692e66"] = {
            "rankings": json.loads(ranking.to_json(orient="records", force_ascii=False)),
            "baskets": json.loads(baskets.to_json(orient="records", force_ascii=False))}
    target.write_text(json.dumps(runs, ensure_ascii=False, indent=2), encoding="utf-8")
    print("ETF screening review completed", flush=True)


def reproduce_check(plan, args):
    """从冻结定义重新执行代表性样本，不读取旧 YAML 或旧回测配置。"""
    records = current_records(plan, args.output)
    checks = []
    names = ("optimized_execution/platform_basket_518880_510310_159980_159985_511260.yaml",
             "capital_100k/es_252d_fhs_constrained_100k.yaml",
             "index_benchmark/domestic_macro_factor_es_index_benchmark_100k.yaml")
    init_worker(PLATFORM)
    for suffix in names:
        config_id, job = next((cid, j) for cid, j in plan["jobs"].items() if any(s.endswith(suffix) for s in j["sources"]))
        bt = job["config"].get("backtest", {})
        old = next(r for r in records if (r["config_id"], r["revision"], r["scenario"], r["start"], r["end"])
                   == (config_id, "current", "default", bt.get("start_date"), bt.get("end_date")))
        task = {k: old[k] for k in ("id", "config_id", "revision", "scenario", "phase", "start", "end")}
        task.update(config=job["config"], raw=str(args.output / "reproduction_probe" / config_id))
        new = worker(task)
        if old["status"] != "ok" or new["status"] != "ok":
            raise RuntimeError(f"Reproduction probe failed: {suffix}: {new.get('error')}")
        deltas = {key: new["metrics"][key] - old["metrics"][key] for key in CORE_METRICS
                  if isinstance(old["metrics"].get(key), (int, float)) and isinstance(new["metrics"].get(key), (int, float))}
        if any(not math.isclose(new["metrics"][key], old["metrics"][key], rel_tol=1e-9, abs_tol=1e-9) for key in deltas):
            raise RuntimeError(f"Reproduction metrics changed: {suffix}")
        checks.append({"input": suffix, "config_id": config_id, "status": "ok", "absolute_metric_differences": {k: abs(v) for k, v in deltas.items()}})
    (args.output / "reproduction_check.json").write_text(json.dumps({"code": plan["code"], "data_hash": plan["data_hash"], "checks": checks}, ensure_ascii=False, indent=2), encoding="utf-8")
    print("3 frozen-input reproduction probes passed", flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--phase", choices=("all", "inventory", "base", "history", "sensitivity", "summary", "freeze", "diagnostics", "screening", "check"), default="all")
    parser.add_argument("--revision", default="current")
    parser.add_argument("--workers", type=int, default=8)
    parser.add_argument("--changed-only", action="store_true", help="补跑主配置交易变化及预热门槛修复可能影响的配置敏感性")
    parser.add_argument("--asof-date", help="统计诊断截止日，默认复核 R060 原报告的 2026-08-12")
    parser.add_argument("--inputs", type=Path, default=Path(__file__).with_name("inputs.json.gz"))
    parser.add_argument("--output", type=Path, default=PLATFORM / "results/temporary_backtests/refactor_validation")
    args = parser.parse_args()
    args.output = args.output.resolve()
    self_check()
    if args.phase in ("inventory", "all"):
        if args.inputs.exists():
            with gzip.open(args.inputs, "rt", encoding="utf-8") as handle:
                plan = json.load(handle)
            actual = {p.relative_to(PLATFORM).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
                      for p in sorted((PLATFORM / "data").rglob("*.csv"))}
            plan.update(data_hash=digest(actual), data_files=actual,
                        code=code_identity())
            args.output.mkdir(parents=True, exist_ok=True)
            (args.output / "plan.json").write_text(json.dumps(plan, ensure_ascii=False, indent=2), encoding="utf-8")
        else:
            plan = inventory(args.output)
        if args.phase == "all":
            steps = [("base", revision) for revision in BASE_REVISIONS] + [("history", "current"), ("sensitivity", "current")]
            for phase, revision in steps:
                args.phase, args.revision = phase, revision
                execute(plan, args)
            args.phase, args.revision, args.changed_only = "sensitivity", "6692e66", True
            execute(plan, args)
            diagnostics(plan, args)
            screening(plan, args)
            summarize(plan, args.output)
            reproduce_check(plan, args)
    else:
        plan = json.loads((args.output / "plan.json").read_text(encoding="utf-8"))
        actual = {p: hashlib.sha256((PLATFORM / p).read_bytes()).hexdigest() for p in plan["data_files"]}
        if digest(actual) != plan["data_hash"]:
            raise RuntimeError("数据已变化，请重新 inventory 后再运行，不得复用旧断点")
        if code_identity() != plan["code"]:
            raise RuntimeError("代码已变化，请重新 inventory 后再运行，不得复用旧版本断点")
        if args.phase == "freeze":
            if args.inputs.exists():
                raise FileExistsError(args.inputs)
            with gzip.open(args.inputs, "wt", encoding="utf-8") as handle:
                json.dump(plan, handle, ensure_ascii=False, separators=(",", ":"))
            print(f"frozen inputs: {args.inputs}, {args.inputs.stat().st_size} bytes")
        elif args.phase == "check":
            reproduce_check(plan, args)
        elif args.phase == "screening":
            screening(plan, args)
        elif args.phase == "diagnostics":
            diagnostics(plan, args)
        elif args.phase == "summary":
            summarize(plan, args.output)
        else:
            execute(plan, args)


if __name__ == "__main__":
    main()
