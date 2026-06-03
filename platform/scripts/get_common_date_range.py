# -*- coding: utf-8 -*-
import argparse
import os
import sys
import yaml
from pathlib import Path
import pandas as pd

ORIG_CWD = Path.cwd()
ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
os.chdir(ROOT)

def resolve_path(path_str: str, root_dir: Path, orig_cwd: Path) -> Path:
    p = Path(path_str)
    if p.is_absolute():
        return p
    if (orig_cwd / p).exists():
        return orig_cwd / p
    if (root_dir / p).exists():
        return root_dir / p
    if (root_dir.parent / p).exists():
        return root_dir.parent / p
    parts = p.parts
    if parts and parts[0] == "platform":
        return root_dir.parent / p
    return root_dir / p

def load_yaml(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as f:
        return yaml.safe_load(f)

def get_asset_dates(data_dir: Path, code: str) -> set:
    path = data_dir / f"{code}.csv"
    if not path.exists():
        print(f"Warning: Data file not found for asset code {code}: {path}", file=sys.stderr)
        return set()
    df = pd.read_csv(path)
    if "trade_date" not in df.columns:
        print(f"Warning: trade_date column not found in {path}", file=sys.stderr)
        return set()
    df = df.dropna(subset=["close"])
    dates = pd.to_datetime(df["trade_date"]).dt.date.tolist()
    return set(dates)

def main() -> int:
    parser = argparse.ArgumentParser(description="Find the longest common date range (intersection of history) for assets.")
    parser.add_argument("--config", nargs="+", help="One or more platform YAML config paths.")
    parser.add_argument("--codes", nargs="+", help="One or more asset codes directly.")
    parser.add_argument("--data-dir", default="data", help="Local data directory.")
    args = parser.parse_args()

    if not args.config and not args.codes:
        print("Error: Must specify either --config or --codes", file=sys.stderr)
        return 1

    codes = set()
    data_dir = resolve_path(args.data_dir, ROOT, ORIG_CWD)

    if args.codes:
        for code in args.codes:
            codes.add(code.strip())

    if args.config:
        for config_path_str in args.config:
            config_path = resolve_path(config_path_str, ROOT, ORIG_CWD)
            # Extra fallback: if config is just a filename, try platform/configs/
            if not config_path.exists() and not Path(config_path_str).parent.name:
                fallback_path = ROOT / "configs" / config_path_str
                if fallback_path.exists():
                    config_path = fallback_path

            if not config_path.exists():
                print(f"Error: Config file not found: {config_path_str}", file=sys.stderr)
                return 1
            config = load_yaml(config_path)
            for asset in config.get("assets", []):
                if "code" in asset:
                    codes.add(str(asset["code"]).strip())

    if not codes:
        print("Error: No asset codes found.", file=sys.stderr)
        return 1

    print(f"Selected assets: {sorted(list(codes))}", file=sys.stderr)

    common_dates = None
    for code in codes:
        asset_dates = get_asset_dates(data_dir, code)
        if common_dates is None:
            common_dates = asset_dates
        else:
            common_dates = common_dates.intersection(asset_dates)

    if not common_dates:
        print("Error: No common trading dates found for the specified assets.", file=sys.stderr)
        return 1

    start_date = min(common_dates)
    end_date = max(common_dates)

    print(f"Longest common trading dates: {len(common_dates)} days", file=sys.stderr)
    print(f"start_date: '{start_date}'")
    print(f"end_date: '{end_date}'")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
