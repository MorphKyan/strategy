"""输出截至指定日期已可观测的 ETF 溢价与净值，供独立研究工具通过 CLI 使用。"""

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.platform_core.etf_premium import EtfPremiumStore
from src.platform_core.models import parse_date


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-dir", required=True)
    parser.add_argument("--codes", nargs="+", required=True)
    parser.add_argument("--asof-date", required=True)
    args = parser.parse_args()
    store = EtfPremiumStore(args.data_dir)
    payload = {}
    for code in dict.fromkeys(args.codes):
        history = store.observable_history(code, parse_date(args.asof_date)).reset_index()
        history["trade_date"] = history["trade_date"].map(str)
        payload[code] = history.to_dict(orient="records")
    print(json.dumps(payload, ensure_ascii=False, allow_nan=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
