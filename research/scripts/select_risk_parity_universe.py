import argparse
import copy
import itertools
import json
import math
import os
import sys
from collections import Counter
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd
import yaml


ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.append(str(ROOT))

from src.data_handler import DataHandler


REPORTS_ROOT = ROOT / "reports" / "literature"
GENERATED_CONFIG_ROOT = ROOT / "configs" / "generated"


def load_yaml(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as handle:
        return yaml.safe_load(handle)


def write_yaml(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        yaml.dump(payload, handle, allow_unicode=True, sort_keys=False)


def write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        handle.write(content)


def write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2, ensure_ascii=False)


def pct(value: float) -> str:
    return f"{value * 100:.2f}%"


def prepare_finshare_env() -> None:
    local_home = ROOT / ".finshare_home"
    local_logs = local_home / ".finshare" / "logs"
    local_appdata = local_home / "AppData" / "Roaming"
    local_logs.mkdir(parents=True, exist_ok=True)
    local_appdata.mkdir(parents=True, exist_ok=True)
    os.environ["HOME"] = str(local_home)
    os.environ["USERPROFILE"] = str(local_home)
    os.environ["APPDATA"] = str(local_appdata)


def patch_loguru_for_sandbox() -> None:
    from loguru import logger as loguru_logger

    if getattr(loguru_logger, "_codex_sandbox_patch", False):
        return

    original_add = loguru_logger.add

    def safe_add(*args, **kwargs):
        kwargs["enqueue"] = False
        return original_add(*args, **kwargs)

    loguru_logger.add = safe_add
    loguru_logger._codex_sandbox_patch = True


def load_adjusted_series(handler: DataHandler, code: str) -> pd.Series:
    frame = handler.load_etf_data([code], auto_fetch=False)
    return frame[code].dropna()


def summarize_history(series: pd.Series) -> dict:
    observations = int(len(series))
    history_years = observations / 252 if observations else 0.0
    return {
        "start_date": series.index.min().strftime("%Y-%m-%d"),
        "end_date": series.index.max().strftime("%Y-%m-%d"),
        "observations": observations,
        "history_years": history_years,
    }


def basket_is_valid(combo: tuple[dict, ...], required_buckets: set[str], max_per_bucket: dict[str, int]) -> bool:
    bucket_counts = Counter(item["bucket"] for item in combo)
    if not required_buckets.issubset(set(bucket_counts)):
        return False
    for bucket, count in bucket_counts.items():
        if count > max_per_bucket.get(bucket, count):
            return False
    return True


def score_basket(handler: DataHandler, combo: tuple[dict, ...], min_overlap_years: float) -> dict | None:
    codes = [item["code"] for item in combo]
    frame = handler.load_etf_data(codes, auto_fetch=False)
    if frame.empty:
        return None

    overlap_years = len(frame) / 252
    if overlap_years < min_overlap_years:
        return None

    returns = frame.pct_change().dropna()
    if returns.empty:
        return None

    corr = returns.corr().abs()
    if len(codes) > 1:
        corr_values = corr.where(~np.eye(len(codes), dtype=bool)).stack()
        avg_abs_corr = float(corr_values.mean()) if not corr_values.empty else 0.0
    else:
        avg_abs_corr = 0.0

    annualized_vol = returns.std() * math.sqrt(252)
    inv_vol = 1.0 / annualized_vol.replace(0, np.nan)
    inv_vol_weights = (inv_vol / inv_vol.sum()).fillna(0.0)
    concentration_hhi = float((inv_vol_weights**2).sum())

    unique_buckets = len({item["bucket"] for item in combo})
    history_score = min(overlap_years / 10.0, 1.0)
    corr_score = 1.0 - min(avg_abs_corr, 1.0)
    concentration_score = 1.0 - min(concentration_hhi, 1.0)
    diversity_score = unique_buckets / len(combo)
    gold_bonus = 0.05 if any(item["bucket"] == "gold" for item in combo) else 0.0

    score = (
        0.40 * history_score
        + 0.25 * corr_score
        + 0.20 * concentration_score
        + 0.15 * diversity_score
        + gold_bonus
    )

    return {
        "codes": codes,
        "assets": [dict(item) for item in combo],
        "score": float(score),
        "overlap_start": frame.index.min().strftime("%Y-%m-%d"),
        "overlap_end": frame.index.max().strftime("%Y-%m-%d"),
        "overlap_observations": int(len(frame)),
        "overlap_years": float(overlap_years),
        "avg_abs_corr": float(avg_abs_corr),
        "annualized_volatility": {code: float(annualized_vol[code]) for code in codes},
        "inverse_vol_weights": {code: float(inv_vol_weights[code]) for code in codes},
        "concentration_hhi": concentration_hhi,
        "bucket_count": unique_buckets,
    }


def build_markdown(
    universe_path: Path,
    eligible_assets: list[dict],
    rejected_assets: list[dict],
    missing_assets: list[dict],
    top_baskets: list[dict],
    generated_configs: list[str],
) -> str:
    lines = [
        "# China ETF Basket Screening",
        "",
        f"- Universe file: `{universe_path}`",
        f"- Generated at: `{datetime.now().isoformat(timespec='seconds')}`",
        "",
        "## Eligible ETFs",
    ]

    for item in eligible_assets:
        lines.append(
            f"- `{item['code']}` {item['name']} | bucket: `{item['bucket']}` | sleeve: `{item['sleeve']}` | history: {item['start_date']} to {item['end_date']} ({item['history_years']:.2f} years)"
        )

    if rejected_assets:
        lines.extend(["", "## Rejected For Short History"])
        for item in rejected_assets:
            lines.append(
                f"- `{item['code']}` {item['name']} | history: {item['start_date']} to {item['end_date']} ({item['history_years']:.2f} years)"
            )

    if missing_assets:
        lines.extend(["", "## Missing Local Data"])
        for item in missing_assets:
            lines.append(
                f"- `{item['code']}` {item['name']} | bucket: `{item['bucket']}` | sleeve: `{item['sleeve']}`"
            )

    lines.extend(["", "## Top Candidate Baskets"])
    for idx, basket in enumerate(top_baskets, start=1):
        asset_line = ", ".join(f"{item['code']} {item['name']}" for item in basket["assets"])
        bucket_line = ", ".join(f"{item['code']}->{item['bucket']}/{item['sleeve']}" for item in basket["assets"])
        ivw_line = ", ".join(f"{code}:{weight:.3f}" for code, weight in basket["inverse_vol_weights"].items())
        lines.extend(
            [
                f"### {idx}. {asset_line}",
                f"- Score: `{basket['score']:.4f}`",
                f"- Buckets: {bucket_line}",
                f"- Common history: `{basket['overlap_start']}` to `{basket['overlap_end']}` ({basket['overlap_years']:.2f} years)",
                f"- Average absolute correlation: `{basket['avg_abs_corr']:.4f}`",
                f"- Inverse-vol concentration HHI: `{basket['concentration_hhi']:.4f}`",
                f"- Average inverse-vol weights: `{ivw_line}`",
            ]
        )

    if generated_configs:
        lines.extend(["", "## Generated Configs"])
        for path in generated_configs:
            lines.append(f"- `{path}`")

    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description="Screen China ETF baskets for risk-parity research.")
    parser.add_argument("--universe-config", default="configs/risk_parity_etf_universe.yaml", help="ETF universe config path.")
    parser.add_argument("--base-config", default="configs/risk_parity.yaml", help="Base config used when writing generated configs.")
    parser.add_argument("--top-k", type=int, default=5, help="How many top baskets to keep.")
    parser.add_argument("--write-configs", action="store_true", help="Write generated basket configs under configs/generated/.")
    parser.add_argument("--fetch-missing", action="store_true", help="Try to fetch missing local ETF data before screening.")
    parser.add_argument("--min-history-years", type=float, help="Override the minimum ETF history threshold.")
    parser.add_argument("--min-overlap-years", type=float, help="Override the minimum basket overlap threshold.")
    args = parser.parse_args()

    universe_path = (ROOT / args.universe_config).resolve()
    base_config_path = (ROOT / args.base_config).resolve()
    universe = load_yaml(universe_path)
    selection = universe["selection"]
    handler = DataHandler()

    min_history_years = float(args.min_history_years if args.min_history_years is not None else selection["min_history_years"])
    min_overlap_years = float(args.min_overlap_years if args.min_overlap_years is not None else selection["min_overlap_years"])
    min_basket_size = int(selection["min_basket_size"])
    max_basket_size = int(selection["max_basket_size"])
    required_buckets = set(selection["required_buckets"])
    max_per_bucket = {str(key): int(value) for key, value in selection["max_per_bucket"].items()}

    eligible_assets = []
    rejected_assets = []
    missing_assets = []
    for item in universe["candidates"]:
        if not item.get("include", True):
            continue
        try:
            series = load_adjusted_series(handler, item["code"])
        except FileNotFoundError:
            if args.fetch_missing:
                prepare_finshare_env()
                patch_loguru_for_sandbox()
                handler.fetch_codes_data([item["code"]])
                try:
                    series = load_adjusted_series(handler, item["code"])
                except FileNotFoundError:
                    missing_assets.append(dict(item))
                    continue
            else:
                missing_assets.append(dict(item))
                continue
        summary = summarize_history(series)
        enriched = {**item, **summary}
        if summary["history_years"] >= min_history_years:
            eligible_assets.append(enriched)
        else:
            rejected_assets.append(enriched)

    scored_baskets = []
    for basket_size in range(min_basket_size, max_basket_size + 1):
        for combo in itertools.combinations(eligible_assets, basket_size):
            if not basket_is_valid(combo, required_buckets, max_per_bucket):
                continue
            scored = score_basket(handler, combo, min_overlap_years)
            if scored is not None:
                scored_baskets.append(scored)

    scored_baskets.sort(
        key=lambda item: (
            item["score"],
            item["overlap_years"],
            -item["avg_abs_corr"],
            -item["concentration_hhi"],
        ),
        reverse=True,
    )

    top_baskets = scored_baskets[: args.top_k]
    generated_configs = []
    if args.write_configs:
        base_config = load_yaml(base_config_path)
        for idx, basket in enumerate(top_baskets, start=1):
            config = copy.deepcopy(base_config)
            config["backtest"]["assets"] = [{"code": item["code"], "name": item["name"]} for item in basket["assets"]]
            config["backtest"]["start_date"] = basket["overlap_start"]
            config["selection_metadata"] = {
                "source_universe": str(universe_path),
                "score": round(basket["score"], 4),
                "avg_abs_corr": round(basket["avg_abs_corr"], 4),
                "overlap_years": round(basket["overlap_years"], 2),
                "inverse_vol_weights": basket["inverse_vol_weights"],
                "rank_at_generation": idx,
            }
            config_name = f"risk_parity_basket_{'_'.join(basket['codes'])}.yaml"
            config_path = GENERATED_CONFIG_ROOT / config_name
            write_yaml(config_path, config)
            generated_configs.append(str(config_path))

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    report_path = REPORTS_ROOT / f"{timestamp}_china_etf_basket_screen.md"
    json_path = REPORTS_ROOT / f"{timestamp}_china_etf_basket_screen.json"
    markdown = build_markdown(universe_path, eligible_assets, rejected_assets, missing_assets, top_baskets, generated_configs)
    write_text(report_path, markdown)
    write_json(
        json_path,
        {
            "eligible_assets": eligible_assets,
            "rejected_assets": rejected_assets,
            "missing_assets": missing_assets,
            "top_baskets": top_baskets,
            "generated_configs": generated_configs,
        },
    )

    print(f"Basket screen written to: {report_path}")
    print(f"Structured results written to: {json_path}")
    for idx, basket in enumerate(top_baskets, start=1):
        codes = ",".join(basket["codes"])
        print(
            f"{idx}. {codes} | score={basket['score']:.4f} | overlap_years={basket['overlap_years']:.2f} | avg_abs_corr={basket['avg_abs_corr']:.4f}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
