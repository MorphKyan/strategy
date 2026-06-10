# -*- coding: utf-8 -*-
import json
import pandas as pd
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

def format_pct(val):
    if val is None:
        return "N/A"
    return f"{val*100:.2f}%"

def format_num(val, fmt="{:.3f}"):
    if val is None:
        return "N/A"
    return fmt.format(val)

def main():
    json_path = ROOT / "results" / "all_configs_evaluation_results.json"
    if not json_path.exists():
        print(f"Error: {json_path} does not exist.")
        return

    with open(json_path, "r", encoding="utf-8") as f:
        results = json.load(f)

    # Let's organize the data
    if not results:
        print("No evaluation results to summarize.")
        output_path = ROOT / "results" / "summary_table.md"
        with open(output_path, "w", encoding="utf-8") as f_out:
            f_out.write("## Platform Configs Evaluation Results Summary\n\nNo configs evaluated (all rejected due to short training sample).\n")
        print(f"Summary table successfully written to {output_path}")
        return

    rows = []
    for r in results:
        name = r["config_name"]
        
        # Metrics
        full_m = r["full_metrics"]
        is_m = r["is_metrics"]
        oos_m = r["oos_metrics"]
        sens = r["sensitivity_stats"]
        
        row = {
            "Config": name.replace(".yaml", ""),
            "Full Sharpe": format_num(full_m.get("sharpe_ratio")),
            "IS Sharpe": format_num(is_m.get("sharpe_ratio")),
            "OOS Sharpe": format_num(oos_m.get("sharpe_ratio")),
            "Full Ret": format_pct(full_m.get("annualized_return")),
            "IS Ret": format_pct(is_m.get("annualized_return")),
            "OOS Ret": format_pct(oos_m.get("annualized_return")),
            "Full DD": format_pct(full_m.get("max_drawdown")),
            "IS DD": format_pct(is_m.get("max_drawdown")),
            "OOS DD": format_pct(oos_m.get("max_drawdown")),
            "Full TO Amt": format_pct(full_m.get("annualized_turnover_amount")),
            "OOS TO Amt": format_pct(oos_m.get("annualized_turnover_amount")),
            "Full TO Qty": format_num(full_m.get("annualized_turnover_quantity")),
            "Sens Sharpe Mean": format_num(sens.get("sharpe_mean")),
            "Sens Sharpe Std": format_num(sens.get("sharpe_std")),
            "Sens Sharpe Min": format_num(sens.get("sharpe_min")),
            "Sens Sharpe Max": format_num(sens.get("sharpe_max")),
            "Trade Count": full_m.get("trade_count", 0),
        }
        rows.append(row)

    df = pd.DataFrame(rows)
    
    # Sort configs: baseline first, then optimal
    df["type"] = df["Config"].apply(lambda x: 0 if (x.startswith("baseline_") and "_opt_" not in x) else 1)
    df = df.sort_values(by=["type", "Config"]).drop(columns=["type"])
    
    # Write to summary_table.md
    output_path = ROOT / "results" / "summary_table.md"
    with open(output_path, "w", encoding="utf-8") as f_out:
        f_out.write("## Platform Configs Evaluation Results Summary\n\n")
        f_out.write(df.to_markdown(index=False))
        f_out.write("\n")
    print(f"Summary table successfully written to {output_path}")

if __name__ == "__main__":
    main()
