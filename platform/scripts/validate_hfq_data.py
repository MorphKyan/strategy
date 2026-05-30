import argparse
import os
import sys
from datetime import datetime
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
REPO_ROOT = ROOT.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
os.chdir(ROOT)

from src.platform_core.data_validation import compare_hfq_data, write_hfq_validation


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate platform adjusted close against the research HFQ data chain.")
    parser.add_argument("--codes", nargs="+", default=["510300", "518880", "511260"], help="ETF codes to compare.")
    parser.add_argument("--research-data-dir", default=str(REPO_ROOT / "research" / "data"), help="Research data directory.")
    parser.add_argument("--platform-data-dir", default="data", help="Platform data directory.")
    parser.add_argument("--start", help="Optional start date, YYYY-MM-DD.")
    parser.add_argument("--end", help="Optional end date, YYYY-MM-DD.")
    parser.add_argument("--output-dir", help="Output directory. Defaults to reports/data_validation/<timestamp>.")
    args = parser.parse_args()

    platform_data_dir = (ROOT / args.platform_data_dir).resolve() if not Path(args.platform_data_dir).is_absolute() else Path(args.platform_data_dir)
    output_dir = Path(args.output_dir) if args.output_dir else ROOT / "reports" / "data_validation" / datetime.now().strftime("%Y%m%d_%H%M%S")
    if not output_dir.is_absolute():
        output_dir = ROOT / output_dir

    detail, summary = compare_hfq_data(
        codes=args.codes,
        research_data_dir=Path(args.research_data_dir),
        platform_data_dir=platform_data_dir,
        start=args.start,
        end=args.end,
    )
    write_hfq_validation(output_dir, detail, summary)
    print(f"HFQ validation report written to: {output_dir}")
    for row in summary["rows"]:
        print(f"{row['code']}: common={row['common_observations']} max_abs_diff={row['max_abs_diff']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
