"""复核旧沪深 300 文件名映射；缺失或过期数据时由原审计入口停止回测。"""
import argparse
import copy
import csv
import gzip
import importlib.util
import io
import json
from pathlib import Path
import zipfile


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    report = Path(__file__).resolve().parent
    repo = report.parents[3]
    output = args.output or repo / "platform/results/temporary_backtests/idx_000300_mapping"
    output = output.resolve()
    spec = importlib.util.spec_from_file_location("original_audit", report / "reproduce.py")
    driver = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(driver)
    plan = json.loads(gzip.decompress((report / "inputs.json.gz").read_bytes()))
    with zipfile.ZipFile(report / "audit.zip") as archive:
        coverage = csv.DictReader(io.StringIO(archive.read("input_coverage.csv").decode("utf-8-sig")))
        ids = sorted({r["config_id"] for r in coverage if "idx_000300.csv" in r["error_examples"]})
    assert len(ids) == 25, "冻结审计范围变化，请重新核对"
    retired = [ident for ident in ids if ident not in plan["jobs"]]
    ids = [ident for ident in ids if ident in plan["jobs"]]
    if not ids:
        print(json.dumps({"retired_groups": len(retired), "attempted_scenarios": 0,
                          "reason": "user_authorized_retirement"}))
        return
    output.mkdir(parents=True, exist_ok=True)
    driver.init_worker(repo / "platform")
    import pandas as pd

    replacement = repo / "platform/data/000300.csv"
    dates = pd.read_csv(replacement, usecols=["trade_date"])["trade_date"]
    assert not dates.duplicated().any(), "沪深 300 日期重复"
    checks, runs = [], []
    for ident in ids:
        job = plan["jobs"][ident]
        cfg = copy.deepcopy(job["config"])
        count = 0
        for asset in cfg["assets"]:
            if asset["code"] == "idx_000300":
                asset["code"] = "000300"
                count += 1
        assert count == 1
        bt = cfg.get("backtest", {})
        missing = [a["code"] for a in cfg["assets"]
                   if not (repo / "platform/data" / (a["code"] + ".csv")).exists()]
        checks.append({"config_id": ident, "sources": job["sources"],
                       "missing_codes_after_mapping": missing,
                       "historical_start": bt.get("start_date"),
                       "historical_end": bt.get("end_date")})
        for scenario in ("default", "stress"):
            task = dict(id=driver.digest([ident, "000300", scenario]), config_id=ident,
                        revision="current", scenario=scenario, phase="mapping_check",
                        start=bt.get("start_date"), end=bt.get("end_date"), config=cfg,
                        raw=str(output / "raw" / ident / scenario))
            result = driver.worker(task)
            if result["status"] == "ok":
                comparisons = []
                for baseline in job["baselines"]:
                    old = baseline["metrics"]
                    if old.get("slippage_scenario") != scenario:
                        continue
                    same_window = all(old.get(k) == result["metrics"].get(k)
                                      for k in ("start_date", "end_date"))
                    comparisons.append({"baseline": baseline["path"], "same_window": same_window,
                                        "deltas": {k: result["metrics"][k] - old[k]
                                                   for k in driver.CORE_METRICS
                                                   if isinstance(old.get(k), (float, int))
                                                   and isinstance(result["metrics"].get(k), (float, int))}})
                result["historical_comparisons"] = comparisons
            runs.append(result)
    summary = {"code": driver.code_identity(), "mapping": {"idx_000300": "000300"},
               "replacement_sha256": driver.hashlib.sha256(replacement.read_bytes()).hexdigest(),
               "replacement_first_date": dates.min(), "replacement_last_date": dates.max(),
               "configuration_count": len(checks), "attempted_scenarios": len(runs),
               "returned_metrics": sum(r["status"] == "ok" for r in runs),
               "checks": checks, "runs": runs}
    (output / "mapping_check.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({k: v for k, v in summary.items() if k not in ("checks", "runs")}, ensure_ascii=False))
    print("Failures:", sorted({r.get("error", "") for r in runs if r["status"] != "ok"}))


if __name__ == "__main__":
    main()
