import argparse
import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parents[2]
ETF_ROOT = Path(__file__).resolve().parents[1]
if str(ETF_ROOT) not in sys.path:
    sys.path.insert(0, str(ETF_ROOT))
os.chdir(REPO_ROOT)

from src.selection import (
    build_baskets,
    generate_platform_configs,
    run_platform_validation,
    screen_sleeves,
    write_json,
    write_report,
)


def resolve_repo_path(value: str | Path) -> Path:
    path = Path(value)
    return path if path.is_absolute() else REPO_ROOT / path


def main() -> int:
    parser = argparse.ArgumentParser(description="Screen mainland ETF sleeves and build platform risk-parity basket configs.")
    parser.add_argument("--config", default="etf_selection/config/etf_universe.yaml", help="ETF selection YAML config path.")
    parser.add_argument("--allow-raw-prices", action="store_true", help="Allow ETFs without HFQ sidecar factors.")
    parser.add_argument("--run-experiments", action="store_true", help="运行同窗口平台对比实验及候选/基线的两个月起点敏感性验证。")
    args = parser.parse_args()

    config_path = resolve_repo_path(args.config)
    config = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    paths = config.get("paths", {})
    report_dir = resolve_repo_path(paths.get("report_dir", "etf_selection/reports")) / timestamp
    generated_dir = resolve_repo_path(paths.get("generated_config_dir", "etf_selection/generated_configs")) / timestamp

    try:
        ranking, sleeve_corrs, candidates = screen_sleeves(config, allow_raw_prices=args.allow_raw_prices)
    except RuntimeError:
        command = [sys.executable, str(REPO_ROOT / "platform/scripts/sync_all_market_data.py"),
                   "--data-dir", str(resolve_repo_path(paths.get("data_dir", "platform/data")))]
        for item in config.get("candidates", []):
            if item.get("include", True):
                command.extend(["--asset", f"{item['code']}.{item.get('exchange', 'SH')}:{item.get('asset_type', 'etf')}"])
        subprocess.run(command, cwd=REPO_ROOT, check=True)
        ranking, sleeve_corrs, candidates = screen_sleeves(config, allow_raw_prices=args.allow_raw_prices)
    basket_frame, basket_corrs = build_baskets(config, ranking, candidates)
    generated_configs = generate_platform_configs(
        base_config_path=resolve_repo_path(paths.get("platform_base_config", "platform/configs/domestic_rolling_bond_10y.yaml")),
        output_dir=generated_dir,
        basket_frame=basket_frame,
        candidates=candidates,
    )
    write_report(report_dir, ranking, sleeve_corrs, basket_frame, basket_corrs, generated_configs, config=config)

    if args.run_experiments and generated_configs:
        experiment_results = run_platform_validation(
            generated_configs,
            platform_script=paths.get("platform_experiment_script", "platform/scripts/run_platform_experiment.py"),
            repo_root=REPO_ROOT,
        )
        write_json(report_dir / "platform_validation_runs.json", {"runs": experiment_results})
        if any(run["returncode"] for run in experiment_results):
            print(f"平台验证失败，命令与输出已保存至 {report_dir / 'platform_validation_runs.json'}")
            return 1

    print(f"ETF selection report written to: {report_dir}")
    print(f"Generated platform configs: {len(generated_configs)}")
    if basket_frame.empty:
        print("No complete baskets generated. Check missing required sleeves, especially commodity.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
