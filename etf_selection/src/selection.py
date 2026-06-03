from __future__ import annotations

import copy
import itertools
import json
import math
import subprocess
import sys
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

import pandas as pd
import yaml


PRICE_COLUMNS = ["close", "close_price", "close_price_adjusted", "nav", "acc_nav"]


@dataclass(frozen=True)
class CandidateData:
    meta: dict[str, Any]
    price: pd.Series
    amount: pd.Series
    volume: pd.Series
    factor_source: str
    raw_df: pd.DataFrame = None


def load_yaml(path: str | Path) -> dict[str, Any]:
    with Path(path).open("r", encoding="utf-8") as handle:
        return yaml.safe_load(handle)


def write_yaml(path: str | Path, payload: dict[str, Any]) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        yaml.safe_dump(payload, handle, allow_unicode=True, sort_keys=False)


def write_json(path: str | Path, payload: dict[str, Any]) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, ensure_ascii=False, indent=2)


def first_column(frame: pd.DataFrame, candidates: list[str]) -> str | None:
    lower = {column.lower(): column for column in frame.columns}
    for candidate in candidates:
        if candidate in frame.columns:
            return candidate
        if candidate.lower() in lower:
            return lower[candidate.lower()]
    return None


def load_adjusted_price(data_dir: str | Path, candidate: dict[str, Any], allow_raw_prices: bool = False) -> CandidateData:
    data_dir = Path(data_dir)
    code = str(candidate["code"])
    price_path = data_dir / f"{code}.csv"
    factor_path = data_dir / f"{code}_hfq_factor.csv"
    if not price_path.exists():
        raise FileNotFoundError(f"missing price file: {price_path}")

    raw = pd.read_csv(price_path)
    if "trade_date" not in raw.columns:
        raise ValueError(f"`trade_date` column is required: {price_path}")
    close_col = first_column(raw, PRICE_COLUMNS)
    if close_col is None:
        raise ValueError(f"close column not found: {price_path}")

    raw["trade_date"] = pd.to_datetime(raw["trade_date"])
    close = pd.to_numeric(raw[close_col], errors="coerce")

    factor_source = "none"
    if factor_path.exists():
        factor_frame = pd.read_csv(factor_path)
        if {"trade_date", "hfq_factor"}.issubset(factor_frame.columns):
            factor_frame["trade_date"] = pd.to_datetime(factor_frame["trade_date"])
            factor_map = factor_frame.set_index("trade_date")["hfq_factor"]
            factor = raw["trade_date"].map(factor_map).ffill().fillna(1.0)
            factor_source = "sidecar_hfq"
        else:
            raise ValueError(f"invalid HFQ factor file: {factor_path}")
    else:
        factor_col = first_column(raw, ["hfq_factor", "adjust_factor", "qfq_factor"])
        if factor_col:
            factor = pd.to_numeric(raw[factor_col], errors="coerce").ffill().fillna(1.0)
            factor_source = factor_col
        elif allow_raw_prices:
            factor = 1.0
            factor_source = "raw"
        else:
            raise FileNotFoundError(f"missing HFQ factor file: {factor_path}")

    amount_col = first_column(raw, ["amount", "turnover"])
    volume_col = first_column(raw, ["volume", "vol"])
    amount = pd.to_numeric(raw[amount_col], errors="coerce").fillna(0.0) if amount_col else pd.Series(0.0, index=raw.index)
    volume = pd.to_numeric(raw[volume_col], errors="coerce").fillna(0.0) if volume_col else pd.Series(0.0, index=raw.index)

    adjusted_values = pd.to_numeric(close, errors="coerce").to_numpy() * pd.Series(factor).to_numpy()
    adjusted = pd.Series(adjusted_values, index=raw["trade_date"], name=code).sort_index().dropna()
    amount = pd.Series(amount.to_numpy(), index=raw["trade_date"], name=code).sort_index().reindex(adjusted.index).fillna(0.0)
    volume = pd.Series(volume.to_numpy(), index=raw["trade_date"], name=code).sort_index().reindex(adjusted.index).fillna(0.0)
    return CandidateData(meta=dict(candidate), price=adjusted, amount=amount, volume=volume, factor_source=factor_source, raw_df=raw)


def normalize(values: pd.Series) -> pd.Series:
    values = pd.to_numeric(values, errors="coerce").fillna(0.0)
    min_value = float(values.min()) if len(values) else 0.0
    max_value = float(values.max()) if len(values) else 0.0
    if math.isclose(max_value, min_value):
        return pd.Series(1.0, index=values.index)
    return (values - min_value) / (max_value - min_value)


def corr_matrix(price_frame: pd.DataFrame) -> pd.DataFrame:
    returns = price_frame.sort_index().pct_change().dropna(how="any")
    if returns.empty:
        return pd.DataFrame(index=price_frame.columns, columns=price_frame.columns, dtype=float)
    return returns.corr()


def pair_values(matrix: pd.DataFrame) -> pd.Series:
    if matrix.empty or len(matrix.columns) <= 1:
        return pd.Series(dtype=float)
    mask = ~pd.DataFrame(
        [[left == right for right in matrix.columns] for left in matrix.index],
        index=matrix.index,
        columns=matrix.columns,
    )
    return matrix.where(mask).stack()


def screen_sleeves(config: dict[str, Any], allow_raw_prices: bool = False) -> tuple[pd.DataFrame, dict[str, pd.DataFrame], dict[str, CandidateData]]:
    selection = config.get("selection", {})
    paths = config.get("paths", {})
    data_dir = paths.get("data_dir", "platform/data")
    min_history_years = float(selection.get("min_history_years", 3))
    candidates: dict[str, CandidateData] = {}
    rows: list[dict[str, Any]] = []

    for item in config.get("candidates", []):
        if not item.get("include", True):
            continue
        code = str(item["code"])
        try:
            data = load_adjusted_price(data_dir, item, allow_raw_prices=allow_raw_prices)
            candidates[code] = data
            returns = data.price.pct_change().dropna()
            observations = len(data.price)
            history_years = observations / 252
            avg_amount = float(data.amount.tail(252).mean()) if len(data.amount) else 0.0
            suspension_ratio = float((data.volume <= 0).mean()) if len(data.volume) else 1.0
            volatility = float(returns.std() * math.sqrt(252)) if len(returns) > 1 else 0.0
            eligible = history_years >= min_history_years
            reason = "" if eligible else f"history_years<{min_history_years}"

            import numpy as np
            premium_std = np.nan
            holding_cost = np.nan
            if item["sleeve"] == "qdii":
                df = data.raw_df
                if df is not None and "nav" in df.columns and "acc_nav" in df.columns:
                    df = df.copy()
                    df['premium'] = df['close'] / df['nav'] - 1
                    premium_std = float(df['premium'].std())
                    ter = float(item.get("ter", 0.006))
                    if "index_close" in df.columns and "fx_rate" in df.columns:
                        r_nav = np.log(df['acc_nav'] / df['acc_nav'].shift(1))
                        r_idx_rmb = np.log((df['index_close'] * df['fx_rate']) / (df['index_close'].shift(1) * df['fx_rate'].shift(1)))
                        td = float((r_nav - r_idx_rmb).dropna().mean() * 252)
                        holding_cost = ter + abs(td)
                    else:
                        holding_cost = ter
                else:
                    premium_std = 0.02
                    holding_cost = float(item.get("ter", 0.006))

            rows.append(
                {
                    "code": code,
                    "asset_id": item["asset_id"],
                    "name": item.get("name", code),
                    "sleeve": item["sleeve"],
                    "subtype": item.get("subtype", ""),
                    "start_date": data.price.index.min().strftime("%Y-%m-%d") if observations else None,
                    "end_date": data.price.index.max().strftime("%Y-%m-%d") if observations else None,
                    "observations": observations,
                    "history_years": history_years,
                    "avg_amount_252d": avg_amount,
                    "suspension_ratio": suspension_ratio,
                    "annualized_volatility": volatility,
                    "factor_source": data.factor_source,
                    "eligible": eligible,
                    "reject_reason": reason,
                    "premium_std": premium_std,
                    "holding_cost": holding_cost,
                }
            )
        except Exception as exc:
            rows.append(
                {
                    "code": code,
                    "asset_id": item.get("asset_id", code),
                    "name": item.get("name", code),
                    "sleeve": item.get("sleeve", ""),
                    "subtype": item.get("subtype", ""),
                    "eligible": False,
                    "reject_reason": str(exc),
                }
            )

    frame = pd.DataFrame(rows)
    if frame.empty:
        return frame, {}, candidates

    eligible_frame = frame[frame["eligible"] == True].copy()
    sleeve_corrs: dict[str, pd.DataFrame] = {}
    frame["peer_representative_corr"] = 0.0
    for sleeve, group in eligible_frame.groupby("sleeve"):
        codes = group["code"].tolist()
        prices = pd.concat([candidates[code].price for code in codes], axis=1, join="inner")
        matrix = corr_matrix(prices)
        sleeve_corrs[str(sleeve)] = matrix
        for code in codes:
            if len(codes) == 1:
                peer_corr = 1.0
            else:
                peer_corr = float(matrix[code].drop(index=code).abs().mean())
            frame.loc[frame["code"] == code, "peer_representative_corr"] = peer_corr

    frame["history_score"] = frame["history_years"].fillna(0).clip(upper=10) / 10
    frame["liquidity_score"] = normalize(frame["avg_amount_252d"].fillna(0).map(lambda value: math.log1p(float(value))))
    frame["representative_corr_score"] = frame["peer_representative_corr"].fillna(0).clip(0, 1)
    frame["data_quality_score"] = (1 - frame["suspension_ratio"].fillna(1)).clip(0, 1)
    frame["volatility_sanity_score"] = 0.0
    for sleeve, group in frame[frame["eligible"] == True].groupby("sleeve"):
        median_vol = group["annualized_volatility"].replace(0, pd.NA).dropna().median()
        if pd.isna(median_vol) or median_vol <= 0:
            frame.loc[group.index, "volatility_sanity_score"] = 1.0
            continue
        ratio = (group["annualized_volatility"] / median_vol).replace(0, pd.NA)
        score = 1 - ratio.map(lambda value: min(abs(math.log(float(value))), 1.0) if pd.notna(value) else 1.0)
        frame.loc[group.index, "volatility_sanity_score"] = score.clip(0, 1)

    weights = selection.get("scoring", {}).get("sleeve", {})
    frame["sleeve_score"] = (
        float(weights.get("history", 0.25)) * frame["history_score"]
        + float(weights.get("liquidity", 0.25)) * frame["liquidity_score"]
        + float(weights.get("representative_corr", 0.20)) * frame["representative_corr_score"]
        + float(weights.get("data_quality", 0.15)) * frame["data_quality_score"]
        + float(weights.get("volatility_sanity", 0.15)) * frame["volatility_sanity_score"]
    )
    
    qdii_mask = frame["sleeve"] == "qdii"
    if qdii_mask.any():
        qdii_group = frame[qdii_mask].copy()
        import numpy as np
        cost_score = 1.0 - normalize(qdii_group["holding_cost"])
        premium_std_score = 1.0 - normalize(qdii_group["premium_std"])
        liquidity_score = normalize(qdii_group["avg_amount_252d"].fillna(0).map(lambda x: math.log1p(float(x))))
        history_score = qdii_group["history_years"].fillna(0).clip(upper=10) / 10.0
        
        qdii_weights = selection.get("scoring", {}).get("sleeve_qdii", {})
        w_cost = float(qdii_weights.get("holding_cost", 0.30))
        w_premium = float(qdii_weights.get("premium_std", 0.30))
        w_liquidity = float(qdii_weights.get("liquidity", 0.30))
        w_history = float(qdii_weights.get("history", 0.10))
        
        sleeve_score = (
            w_cost * cost_score
            + w_premium * premium_std_score
            + w_liquidity * liquidity_score
            + w_history * history_score
        )
        frame.loc[qdii_mask, "sleeve_score"] = sleeve_score

    frame.loc[frame["eligible"] != True, "sleeve_score"] = 0.0
    return frame.sort_values(["sleeve", "sleeve_score"], ascending=[True, False]), sleeve_corrs, candidates


def commodity_options(eligible: pd.DataFrame, top_k: int, config: dict[str, Any]) -> list[list[str]]:
    commodity = eligible[eligible["sleeve"] == "commodity"].sort_values("sleeve_score", ascending=False)
    if commodity.empty:
        return []
    rules = config.get("selection", {}).get("commodity", {})
    broad = commodity[commodity["subtype"] == "broad"].head(top_k)
    if bool(rules.get("prefer_broad", True)) and not broad.empty:
        return [[code] for code in broad["code"].tolist()]
    singles = commodity[commodity["subtype"].astype(str).str.startswith("single")].head(top_k)["code"].tolist()
    min_count = int(rules.get("min_single_commodity_count", 2))
    max_count = int(rules.get("max_single_commodity_count", 3))
    options: list[list[str]] = []
    for size in range(min_count, min(max_count, len(singles)) + 1):
        options.extend([list(combo) for combo in itertools.combinations(singles, size)])
    return options


def build_baskets(
    config: dict[str, Any],
    ranking: pd.DataFrame,
    candidates: dict[str, CandidateData],
) -> tuple[pd.DataFrame, dict[str, pd.DataFrame], list[list[str]]]:
    selection = config.get("selection", {})
    top_k = int(selection.get("top_k_per_sleeve", 3))
    max_baskets = int(selection.get("max_baskets", 20))
    required_sleeves = list(selection.get("required_sleeves", ["gold", "hs300", "commodity", "bond"]))
    eligible = ranking[ranking["eligible"] == True].copy()
    options_by_sleeve: dict[str, list[list[str]]] = {}
    for sleeve in required_sleeves:
        if sleeve == "commodity":
            options_by_sleeve[sleeve] = commodity_options(eligible, top_k, config)
        else:
            codes = (
                eligible[eligible["sleeve"] == sleeve]
                .sort_values("sleeve_score", ascending=False)
                .head(top_k)["code"]
                .tolist()
            )
            options_by_sleeve[sleeve] = [[code] for code in codes]

    if any(not options_by_sleeve.get(sleeve) for sleeve in required_sleeves):
        return pd.DataFrame(), {}, []

    rows: list[dict[str, Any]] = []
    corr_by_basket: dict[str, pd.DataFrame] = {}
    basket_codes: list[list[str]] = []
    basket_weights = selection.get("scoring", {}).get("basket", {})
    for index, option_tuple in enumerate(itertools.product(*(options_by_sleeve[sleeve] for sleeve in required_sleeves)), start=1):
        codes = list(dict.fromkeys(itertools.chain.from_iterable(option_tuple)))
        prices = pd.concat([candidates[code].price for code in codes], axis=1, join="inner")
        if prices.empty:
            continue
        returns = prices.pct_change().dropna()
        if returns.empty:
            continue
        matrix = returns.corr()
        corr_by_basket[f"basket_{index}"] = matrix
        pair_corr = pair_values(matrix).abs()
        avg_abs_corr = float(pair_corr.mean()) if len(pair_corr) else 0.0
        max_abs_corr = float(pair_corr.max()) if len(pair_corr) else 0.0
        vol = returns.std() * math.sqrt(252)
        inv_vol = (1.0 / vol.replace(0, pd.NA)).dropna()
        weights = inv_vol / inv_vol.sum() if len(inv_vol) else pd.Series(dtype=float)
        hhi = float((weights**2).sum()) if len(weights) else 1.0
        common_years = len(prices) / 252
        liquidity = float(pd.Series([candidates[code].amount.tail(252).mean() for code in codes]).mean())
        sleeve_scores = ranking.set_index("code").loc[codes, "sleeve_score"].mean()
        history_score = min(common_years / 10.0, 1.0)
        corr_score = 1 - min(avg_abs_corr, 1.0)
        concentration_score = 1 - min(hhi, 1.0)
        liquidity_score = min(math.log1p(liquidity) / 25.0, 1.0)
        sleeve_coverage_score = len(required_sleeves) / len(required_sleeves)
        score = (
            float(basket_weights.get("common_history", 0.30)) * history_score
            + float(basket_weights.get("cross_correlation", 0.30)) * corr_score
            + float(basket_weights.get("concentration", 0.20)) * concentration_score
            + float(basket_weights.get("liquidity", 0.10)) * liquidity_score
            + float(basket_weights.get("sleeve_coverage", 0.10)) * sleeve_coverage_score
        )
        rows.append(
            {
                "basket_id": f"basket_{index}",
                "codes": ",".join(codes),
                "asset_ids": ",".join(candidates[code].meta["asset_id"] for code in codes),
                "common_start": prices.index.min().strftime("%Y-%m-%d"),
                "common_end": prices.index.max().strftime("%Y-%m-%d"),
                "common_observations": len(prices),
                "common_history_years": common_years,
                "avg_abs_corr": avg_abs_corr,
                "max_abs_corr": max_abs_corr,
                "inverse_vol_hhi": hhi,
                "avg_liquidity_252d": liquidity,
                "avg_sleeve_score": float(sleeve_scores),
                "basket_score": score,
                "inverse_vol_weights": json.dumps({code: float(weights.get(code, 0.0)) for code in codes}, ensure_ascii=False),
            }
        )
        basket_codes.append(codes)

    basket_frame = pd.DataFrame(rows).sort_values("basket_score", ascending=False).head(max_baskets)
    keep_ids = set(basket_frame["basket_id"].tolist()) if not basket_frame.empty else set()
    corr_by_basket = {key: value for key, value in corr_by_basket.items() if key in keep_ids}
    basket_codes = [row["codes"].split(",") for _, row in basket_frame.iterrows()] if not basket_frame.empty else []
    return basket_frame, corr_by_basket, basket_codes


def platform_asset(meta: dict[str, Any]) -> dict[str, Any]:
    return {
        "asset_id": meta["asset_id"],
        "code": str(meta["code"]),
        "name": meta.get("name", meta["code"]),
        "asset_type": meta.get("asset_type", "etf"),
        "exchange": meta.get("exchange", "SH"),
        "currency": meta.get("currency", "CNY"),
        "lot_size": int(meta.get("lot_size", 100)),
        "price_limit_pct": float(meta.get("price_limit_pct", 0.10)),
    }


def generate_platform_configs(
    base_config_path: str | Path,
    output_dir: str | Path,
    basket_frame: pd.DataFrame,
    candidates: dict[str, CandidateData],
) -> list[Path]:
    if basket_frame.empty:
        return []
    base_config = load_yaml(base_config_path)
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    paths: list[Path] = []
    for _, row in basket_frame.iterrows():
        codes = row["codes"].split(",")
        config = copy.deepcopy(base_config)
        config.setdefault("platform", {})["run_name"] = f"platform_basket_{'_'.join(codes)}"
        config["assets"] = [platform_asset(candidates[code].meta) for code in codes]
        start_date = row["common_start"]
        config.setdefault("backtest", {})["start_date"] = start_date
        for segment in config.setdefault("strategies", {}).setdefault("segments", []):
            segment["start_date"] = start_date
            segment.setdefault("params", {})["universe"] = [candidates[code].meta["asset_id"] for code in codes]
        config["selection_metadata"] = {
            "basket_id": row["basket_id"],
            "codes": codes,
            "score": round(float(row["basket_score"]), 6),
            "avg_abs_corr": round(float(row["avg_abs_corr"]), 6),
            "max_abs_corr": round(float(row["max_abs_corr"]), 6),
            "inverse_vol_hhi": round(float(row["inverse_vol_hhi"]), 6),
            "common_history_years": round(float(row["common_history_years"]), 4),
        }
        path = output_dir / f"platform_basket_{'_'.join(codes)}.yaml"
        write_yaml(path, config)
        paths.append(path)
    return paths


def write_report(
    output_dir: str | Path,
    ranking: pd.DataFrame,
    sleeve_corrs: dict[str, pd.DataFrame],
    basket_frame: pd.DataFrame,
    basket_corrs: dict[str, pd.DataFrame],
    generated_configs: list[Path],
) -> None:
    output_dir = Path(output_dir)
    corr_dir = output_dir / "correlations"
    corr_dir.mkdir(parents=True, exist_ok=True)
    ranking.to_csv(output_dir / "sleeve_rankings.csv", index=False)
    basket_frame.to_csv(output_dir / "basket_scores.csv", index=False)
    for sleeve, matrix in sleeve_corrs.items():
        matrix.to_csv(corr_dir / f"{sleeve}.csv")
    for basket_id, matrix in basket_corrs.items():
        matrix.to_csv(corr_dir / f"{basket_id}.csv")
    write_json(
        output_dir / "summary.json",
        {
            "generated_at": datetime.now().isoformat(timespec="seconds"),
            "generated_configs": [str(path) for path in generated_configs],
            "eligible_count": int((ranking["eligible"] == True).sum()) if not ranking.empty else 0,
            "basket_count": int(len(basket_frame)),
        },
    )
    lines = [
        "# ETF 袖子筛选报告",
        "",
        "## 硬性规则",
        "- 本流程按袖子独立筛选 ETF，再构建跨袖子候选篮子。",
        "- 历史长度是硬性限制，默认至少 3 年。",
        "- 商品袖子优先使用宽基商品 ETF；如果没有合格宽基商品 ETF，可以使用多个单商品 ETF。",
        "",
        "## 袖子内排名",
    ]
    if ranking.empty:
        lines.append("- 没有可评估 ETF。")
    else:
        for sleeve, group in ranking.groupby("sleeve"):
            lines.append(f"### {sleeve}")
            for _, row in group.sort_values("sleeve_score", ascending=False).iterrows():
                status = "eligible" if row.get("eligible") else f"rejected: {row.get('reject_reason')}"
                if sleeve == "qdii":
                    lines.append(
                        f"- `{row['code']}` {row.get('name', '')} | score={float(row.get('sleeve_score', 0)):.4f} | history={float(row.get('history_years', 0)):.2f}y | cost={float(row.get('holding_cost', 0.0)):.4f} | premium_std={float(row.get('premium_std', 0.0)):.4f} | {status}"
                    )
                else:
                    lines.append(
                        f"- `{row['code']}` {row.get('name', '')} | score={float(row.get('sleeve_score', 0)):.4f} | history={float(row.get('history_years', 0)):.2f}y | peer_corr={float(row.get('peer_representative_corr', 0)):.4f} | {status}"
                    )
    lines.extend(["", "## 候选篮子"])
    if basket_frame.empty:
        lines.append("- 未生成候选篮子。通常原因是某个必需袖子没有合格 ETF，尤其是商品袖子缺少宽基或单商品候选。")
    else:
        for _, row in basket_frame.iterrows():
            lines.append(
                f"- `{row['basket_id']}` {row['codes']} | score={float(row['basket_score']):.4f} | corr={float(row['avg_abs_corr']):.4f} | hhi={float(row['inverse_vol_hhi']):.4f}"
            )
    if generated_configs:
        lines.extend(["", "## 生成的平台配置"])
        lines.extend(f"- `{path}`" for path in generated_configs)
    (output_dir / "report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def run_platform_experiments(config_paths: list[Path], platform_script: str | Path, repo_root: str | Path) -> list[dict[str, Any]]:
    results: list[dict[str, Any]] = []
    repo_root = Path(repo_root)
    for config_path in config_paths:
        command = [
            sys.executable,
            str(repo_root / platform_script),
            "--config",
            str(config_path),
            "--baseline-config",
            "configs/baseline_r1_domestic_rolling.yaml",
        ]
        completed = subprocess.run(command, cwd=repo_root, capture_output=True, text=True, encoding="utf-8", errors="replace", check=False)
        results.append(
            {
                "config": str(config_path),
                "command": command,
                "returncode": completed.returncode,
                "stdout": completed.stdout,
                "stderr": completed.stderr,
            }
        )
    return results
