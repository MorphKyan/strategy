"""Merge validated local percentage-rate CSVs without revising stored history."""
from __future__ import annotations

import argparse
from pathlib import Path
import sys

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from src.platform_core.interest_rates import DEFAULT_RATE_DIR, RATE_SOURCES, load_annual_rates


def import_rates(source: str, input_path: Path, data_dir: Path = DEFAULT_RATE_DIR) -> Path:
    if source not in RATE_SOURCES:
        raise ValueError(f"Unsupported source: {source}")
    incoming = load_annual_rates(input_path)
    destination = data_dir / f"{source}.csv"
    if destination.exists():
        existing = load_annual_rates(destination)
        overlap = existing.index.intersection(incoming.index)
        if not (existing.loc[overlap] == incoming.loc[overlap]).all():
            raise ValueError("Conflicting historical rates; existing file was not changed")
        incoming = pd.concat([existing, incoming.loc[~incoming.index.isin(existing.index)]]).sort_index()
    data_dir.mkdir(parents=True, exist_ok=True)
    output = (incoming * 100).rename("annual_rate_pct").rename_axis("date").reset_index()
    temporary = destination.with_suffix(".csv.tmp")
    try:
        output.to_csv(temporary, index=False, date_format="%Y-%m-%d", float_format="%.12g")
        temporary.replace(destination)
    finally:
        temporary.unlink(missing_ok=True)
    return destination


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", required=True, choices=RATE_SOURCES)
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--data-dir", type=Path, default=DEFAULT_RATE_DIR)
    args = parser.parse_args()
    print(import_rates(args.source, args.input, args.data_dir))


if __name__ == "__main__":
    main()
