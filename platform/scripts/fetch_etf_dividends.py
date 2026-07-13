# -*- coding: utf-8 -*-
import sys
import re
import pandas as pd
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import akshare as ak

# List of ETFs in the universe (core assets + R039 industry rotation candidates)
ETFS = [
    {"code": "510300", "name": "沪深300ETF"},
    {"code": "513500", "name": "标普500ETF"},
    {"code": "518880", "name": "黄金ETF"},
    {"code": "511260", "name": "十年国债ETF"},
    {"code": "159985", "name": "豆粕ETF"},
    {"code": "159981", "name": "能源化工ETF"},
    {"code": "512890", "name": "红利低波ETF"},
    {"code": "513100", "name": "纳指ETF"},
    {"code": "510500", "name": "中证500ETF"},
    {"code": "159920", "name": "恒生ETF"},
    {"code": "513030", "name": "德国ETF"},
    {"code": "510880", "name": "红利ETF"},
    # R039 行业轮动候选池（docs/r039_rotation_blueprint.md §3）
    {"code": "512880", "name": "证券ETF"},
    {"code": "512800", "name": "银行ETF"},
    {"code": "512010", "name": "医药ETF"},
    {"code": "159928", "name": "消费ETF"},
    {"code": "512690", "name": "酒ETF"},
    {"code": "512660", "name": "军工ETF"},
    {"code": "512400", "name": "有色金属ETF"},
    {"code": "512980", "name": "传媒ETF"},
    {"code": "515000", "name": "科技ETF"},
    {"code": "512480", "name": "半导体ETF"},
    {"code": "515050", "name": "5G通信ETF"},
    {"code": "512200", "name": "房地产ETF"},
    {"code": "515220", "name": "煤炭ETF"},
    {"code": "515700", "name": "新能车ETF"},
    {"code": "515210", "name": "钢铁ETF"},
    {"code": "159996", "name": "家电ETF"},
]

def parse_dividend(text):
    if not isinstance(text, str) or not text:
        return 0.0
    # Match value like "分红0.1230元"
    match = re.search(r"分红([\d\.]+)元", text)
    if not match:
        # Try matching "派息X元"
        match = re.search(r"派息([\d\.]+)元", text)
    if not match:
        # Try generic decimal match
        match = re.search(r"([\d\.]+)", text)
        
    if not match:
        return 0.0
        
    val = float(match.group(1))
    if "每百份" in text or "每100份" in text:
        return val / 100.0
    elif "每十份" in text or "每10份" in text:
        return val / 10.0
    return val

def parse_split_ratio(text):
    if not isinstance(text, str) or not text:
        return 1.0
    # Usually in format "1:0.3709" or "1:2.5"
    if ":" in text:
        parts = text.split(":")
        try:
            return float(parts[1]) / float(parts[0])
        except Exception:
            pass
    # Try generic float
    try:
        return float(text)
    except ValueError:
        return 1.0

def main():
    dividend_records = []
    split_records = []
    
    print("Start fetching ETF dividend and split histories from EastMoney via AKShare...")
    
    for etf in ETFS:
        code = etf["code"]
        name = etf["name"]
        print(f"Fetching {code} ({name})...")
        
        # 1. Fetch Dividends
        try:
            df_div = ak.fund_open_fund_info_em(symbol=code, indicator="分红送配详情")
            if not df_div.empty:
                # Expected columns: ['年份', '权益登记日', '除息日', '每份分红', '分红发放日']
                for _, row in df_div.iterrows():
                    raw_div = row.get("每份分红", "")
                    div_val = parse_dividend(raw_div)
                    
                    dividend_records.append({
                        "code": code,
                        "name": name,
                        "year": row.get("年份", ""),
                        "record_date": row.get("权益登记日", ""),
                        "ex_date": row.get("除息日", ""),
                        "raw_text": raw_div,
                        "dividend_per_share": div_val,
                        "payment_date": row.get("分红发放日", "")
                    })
                print(f"  - Found {len(df_div)} dividend events")
            else:
                print("  - No dividend events found")
        except Exception as e:
            print(f"  - Error fetching dividends: {e}")
            
        # 2. Fetch Splits
        try:
            df_split = ak.fund_open_fund_info_em(symbol=code, indicator="拆分详情")
            if not df_split.empty:
                # Expected columns: ['年份', '拆分折算日', '拆分类型', '拆分折算比例']
                for _, row in df_split.iterrows():
                    raw_split = row.get("拆分折算比例", "")
                    ratio = parse_split_ratio(raw_split)
                    
                    split_records.append({
                        "code": code,
                        "name": name,
                        "year": row.get("年份", ""),
                        "split_date": row.get("拆分折算日", ""),
                        "split_type": row.get("拆分类型", ""),
                        "raw_text": raw_split,
                        "split_ratio": ratio
                    })
                print(f"  - Found {len(df_split)} split events")
            else:
                print("  - No split events found")
        except Exception as e:
            print(f"  - Error fetching splits: {e}")
            
    # 事件表写入原则（只增不删 + 新拆分先过价格验证 + 稳定写盘）：
    # 上游数据异常时整表覆盖曾静默删掉已验证的历史事件（510500 两条拆分被
    # 替换成错误的 1:0.01）。本地表是"账本"，抓取结果只能追加候选。
    from src.platform_core.corporate_actions import merge_event_table, validate_split_against_prices
    from src.platform_core.data_store import write_csv_stable

    data_dir = ROOT / "data"

    def read_existing(path):
        return pd.read_csv(path, dtype=str).fillna("") if path.exists() else None

    # Output dividends（键：code + ex_date；纯追加）
    df_out_div = pd.DataFrame(dividend_records)
    if not df_out_div.empty:
        output_div_path = data_dir / "platform_dividends.csv"
        merged, notes, additions = merge_event_table(read_existing(output_div_path), df_out_div, ["code", "ex_date"])
        for note in notes:
            print(f"  [dividends] {note}")
        if additions:
            merged = pd.concat([merged, pd.DataFrame(additions)], ignore_index=True)
        merged = merged.sort_values(by=["code", "ex_date"], ascending=[True, False])
        changed = write_csv_stable(output_div_path, merged)
        print(f"\nDividends: +{len(additions)} new events; file {'updated' if changed else 'unchanged'} ({output_div_path})")

    # Output splits（键：code + split_date；新增必须过价格交叉验证）
    df_out_split = pd.DataFrame(split_records)
    if not df_out_split.empty:
        output_split_path = data_dir / "platform_splits.csv"
        merged, notes, additions = merge_event_table(read_existing(output_split_path), df_out_split, ["code", "split_date"])
        for note in notes:
            print(f"  [splits] {note}")
        accepted = []
        for row in additions:
            ok, verdict = validate_split_against_prices(row["code"], row["split_date"], float(row["split_ratio"]), data_dir)
            print(f"  [splits] {'接受' if ok else '拒绝'}: {verdict}")
            if ok:
                accepted.append(row)
        if accepted:
            merged = pd.concat([merged, pd.DataFrame(accepted)], ignore_index=True)
        merged = merged.sort_values(by=["code", "split_date"], ascending=[True, False])
        changed = write_csv_stable(output_split_path, merged)
        print(f"Splits: +{len(accepted)} accepted / {len(additions) - len(accepted)} rejected; file {'updated' if changed else 'unchanged'} ({output_split_path})")

    return 0

if __name__ == "__main__":
    sys.exit(main())
