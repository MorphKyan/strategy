import argparse
import csv
import json
import os
import re
import sys
import time
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path
from typing import Callable


ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.append(str(ROOT))


REPORTS_ROOT = ROOT / "reports" / "literature" / "etf_screening"


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


prepare_finshare_env()
patch_loguru_for_sandbox()

import finshare as fs


def normalize_text(value: str | None) -> str:
    if not value:
        return ""
    text = str(value)
    text = text.replace("\u3000", " ")
    return re.sub(r"\s+", " ", text).strip()


def contains_any(text: str, keywords: list[str]) -> bool:
    haystack = normalize_text(text).lower()
    return any(keyword.lower() in haystack for keyword in keywords)


def parse_percent(value: str | None) -> float | None:
    if not value:
        return None
    match = re.search(r"([0-9]+(?:\.[0-9]+)?)\s*%", value)
    if not match:
        return None
    return float(match.group(1))


def extract_first_match(text: str, patterns: list[tuple[str, int]]) -> str | None:
    for pattern, flags in patterns:
        match = re.search(pattern, text, flags)
        if match:
            return normalize_text(match.group(1))
    return None


def extract_management_fee(text: str) -> float | None:
    patterns = [
        (r"管理费率[^0-9]{0,20}([0-9]+(?:\.[0-9]+)?\s*%)", re.IGNORECASE),
        (r"管理费[^0-9]{0,20}([0-9]+(?:\.[0-9]+)?\s*%)", re.IGNORECASE),
        (r'"managementFee"\s*:\s*"([^"]+)"', re.IGNORECASE),
        (r'"gl"\s*:\s*"([0-9]+(?:\.[0-9]+)?%)"', re.IGNORECASE),
    ]
    return parse_percent(extract_first_match(text, patterns))


def extract_fund_type(text: str) -> str | None:
    patterns = [
        (r"基金类型[^<:\n]{0,20}(?:</[^>]+>\s*)?<[^>]*>([^<]+)<", re.IGNORECASE),
        (r"基金类型[：:]\s*([^<\n]+)", re.IGNORECASE),
        (r'"基金类型"\s*:\s*"([^"]+)"', re.IGNORECASE),
        (r'"fundType"\s*:\s*"([^"]+)"', re.IGNORECASE),
    ]
    return extract_first_match(text, patterns)


def extract_tracking_index(text: str) -> str | None:
    patterns = [
        (r"(?:跟踪标的|跟踪指数|标的指数)[^<:\n]{0,20}(?:</[^>]+>\s*)?<[^>]*>([^<]+)<", re.IGNORECASE),
        (r"(?:跟踪标的|跟踪指数|标的指数)[：:]\s*([^<\n]+)", re.IGNORECASE),
        (r'"(?:indexName|trackingIndex|benchmark)"\s*:\s*"([^"]+)"', re.IGNORECASE),
    ]
    return extract_first_match(text, patterns)


def extract_duration_years(text: str, context_text: str) -> float | None:
    numeric_candidates: list[float] = []
    patterns = [
        r"久期[^0-9]{0,20}([0-9]+(?:\.[0-9]+)?)\s*年",
        r"剩余期限[^0-9]{0,20}([0-9]+(?:\.[0-9]+)?)\s*年",
        r"平均久期[^0-9]{0,20}([0-9]+(?:\.[0-9]+)?)\s*年",
        r"组合久期[^0-9]{0,20}([0-9]+(?:\.[0-9]+)?)\s*年",
        r"久期[^0-9]{0,20}([0-9]+(?:\.[0-9]+)?)",
    ]
    for pattern in patterns:
        for match in re.finditer(pattern, text, re.IGNORECASE):
            try:
                numeric_candidates.append(float(match.group(1)))
            except ValueError:
                continue

    for match in re.finditer(r"([0-9]+(?:\.[0-9]+)?)\s*年", context_text):
        try:
            numeric_candidates.append(float(match.group(1)))
        except ValueError:
            continue

    if not numeric_candidates:
        return None
    return max(numeric_candidates)


def load_fund_page_text(code: str) -> str:
    from finshare.sources.fund_source import FundDataSource

    source = FundDataSource()
    fund_code = source._format_fund_code(code)
    url = f"{source.eastmoney_base_url}/jjj/{fund_code}.html"
    response = source._make_request(url)
    if response is None:
        return ""
    if isinstance(response, str):
        return response
    return json.dumps(response, ensure_ascii=False)


def summarize_nav_history(code: str) -> dict:
    nav_points = fs.get_fund_nav(code, "1990-01-01", date.today().isoformat())
    if not nav_points:
        return {
            "history_years": 0.0,
            "nav_observations": 0,
            "start_date": None,
            "end_date": None,
        }

    first_date = nav_points[0].nav_date
    last_date = nav_points[-1].nav_date
    history_years = max((last_date - first_date).days / 365.25, 0.0)
    return {
        "history_years": float(history_years),
        "nav_observations": int(len(nav_points)),
        "start_date": first_date.isoformat(),
        "end_date": last_date.isoformat(),
    }


@dataclass
class ScreeningSpec:
    name: str
    slug: str
    description: str
    min_history_years: float
    max_management_fee: float | None
    classifier: Callable[[dict], tuple[bool, str]]


def classify_large_cap(record: dict) -> tuple[bool, str]:
    text = " ".join(
        [
            record.get("name", ""),
            record.get("fund_type", ""),
            record.get("tracking_index", ""),
            record.get("raw_page_excerpt", ""),
        ]
    )
    include_keywords = [
        "上证50",
        "沪深300",
        "上证180",
        "中证a50",
        "msci中国a50",
        "a50",
    ]
    exclude_keywords = [
        "中证500",
        "中证1000",
        "创业板",
        "科创",
        "红利",
        "低波",
        "消费",
        "医药",
        "证券",
        "银行",
        "芯片",
        "军工",
        "港股",
        "纳斯达克",
        "恒生",
    ]

    if not contains_any(text, include_keywords):
        return False, "not_large_cap_proxy"
    if contains_any(text, exclude_keywords):
        return False, "excluded_thematic_or_non_core_equity"
    return True, "matched_large_cap_proxy"


def classify_bond(record: dict) -> tuple[bool, str]:
    text = " ".join(
        [
            record.get("name", ""),
            record.get("fund_type", ""),
            record.get("tracking_index", ""),
            record.get("raw_page_excerpt", ""),
        ]
    )
    include_keywords = [
        "国债",
        "政金债",
        "地方债",
        "利率债",
        "国开债",
        "政策性金融债",
    ]
    exclude_keywords = [
        "可转债",
        "信用债",
        "短融",
        "同业存单",
        "城投",
    ]

    if not contains_any(text, include_keywords):
        return False, "not_target_bond_exposure"
    if contains_any(text, exclude_keywords):
        return False, "excluded_bond_subtype"

    duration = record.get("duration_years")
    if duration is None:
        return False, "duration_not_found"
    if duration < 10.0:
        return False, "duration_below_10_years"
    return True, "matched_long_duration_bond"


def classify_gold(record: dict) -> tuple[bool, str]:
    text = " ".join(
        [
            record.get("name", ""),
            record.get("fund_type", ""),
            record.get("tracking_index", ""),
            record.get("raw_page_excerpt", ""),
        ]
    )
    include_keywords = [
        "黄金",
        "au99",
        "au9999",
        "上海金",
    ]
    if not contains_any(text, include_keywords):
        return False, "not_gold_exposure"
    return True, "matched_gold_exposure"


def extract_record(etf_item: dict) -> dict:
    code = str(etf_item.get("code", "")).strip()
    name = normalize_text(etf_item.get("name"))
    page_text = load_fund_page_text(code)
    history = summarize_nav_history(code)
    fund_type = extract_fund_type(page_text)
    tracking_index = extract_tracking_index(page_text)
    duration_context = " ".join(filter(None, [name, fund_type, tracking_index]))
    duration_years = extract_duration_years(page_text, duration_context)
    raw_excerpt = normalize_text(page_text)[:400]

    record = {
        "code": code,
        "name": name,
        "fund_type": fund_type,
        "tracking_index": tracking_index,
        "management_fee_pct": extract_management_fee(page_text),
        "duration_years": duration_years,
        "raw_page_excerpt": raw_excerpt,
        **history,
    }
    return record


def write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2, ensure_ascii=False)


def write_csv(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        headers = [
            "code",
            "name",
            "history_years",
            "nav_observations",
            "start_date",
            "end_date",
            "fund_type",
            "tracking_index",
            "management_fee_pct",
            "duration_years",
            "decision",
            "reason",
        ]
    else:
        headers = list(rows[0].keys())

    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=headers)
        writer.writeheader()
        writer.writerows(rows)


def build_markdown(spec: ScreeningSpec, selected: list[dict], rejected: list[dict], output_files: dict[str, str]) -> str:
    lines = [
        f"# {spec.name}",
        "",
        f"- Description: {spec.description}",
        f"- Generated at: `{datetime.now().isoformat(timespec='seconds')}`",
        f"- Minimum history: `{spec.min_history_years:.2f}` years",
    ]
    if spec.max_management_fee is not None:
        lines.append(f"- Maximum management fee: `{spec.max_management_fee:.2f}%`")
    lines.extend(
        [
            f"- Selected count: `{len(selected)}`",
            f"- Rejected count: `{len(rejected)}`",
            "",
            "## Selected ETFs",
        ]
    )

    if not selected:
        lines.append("- None")
    else:
        for item in selected:
            lines.append(
                f"- `{item['code']}` {item['name']} | history: `{item['history_years']:.2f}`y | fee: `{format_optional(item['management_fee_pct'], '%')}` | duration: `{format_optional(item['duration_years'], 'y')}` | index: `{item.get('tracking_index') or 'N/A'}`"
            )

    lines.extend(["", "## Rejected ETFs"])
    if not rejected:
        lines.append("- None")
    else:
        for item in rejected:
            lines.append(
                f"- `{item['code']}` {item['name']} | reason: `{item['reason']}` | history: `{item['history_years']:.2f}`y | fee: `{format_optional(item['management_fee_pct'], '%')}` | duration: `{format_optional(item['duration_years'], 'y')}`"
            )

    lines.extend(
        [
            "",
            "## Artifacts",
            f"- Markdown: `{output_files['markdown']}`",
            f"- JSON: `{output_files['json']}`",
            f"- CSV: `{output_files['csv']}`",
        ]
    )
    return "\n".join(lines) + "\n"


def format_optional(value: float | None, suffix: str) -> str:
    if value is None:
        return "N/A"
    return f"{value:.2f}{suffix}"


def evaluate_record(record: dict, spec: ScreeningSpec) -> tuple[bool, str]:
    if record["history_years"] < spec.min_history_years:
        return False, "history_below_threshold"

    if spec.max_management_fee is not None:
        fee = record.get("management_fee_pct")
        if fee is None:
            return False, "management_fee_not_found"
        if fee >= spec.max_management_fee:
            return False, "management_fee_above_threshold"

    return spec.classifier(record)


def run_screening(spec: ScreeningSpec, limit: int = 0, sleep_seconds: float = 0.0) -> dict:
    prepare_finshare_env()
    patch_loguru_for_sandbox()

    etfs = fs.get_etf_list()
    if not etfs:
        raise RuntimeError("finshare returned an empty ETF list; aborting screening instead of producing a misleading empty report.")
    if limit > 0:
        etfs = etfs[:limit]

    selected: list[dict] = []
    rejected: list[dict] = []

    for index, etf_item in enumerate(etfs, start=1):
        record = extract_record(etf_item)
        is_selected, reason = evaluate_record(record, spec)
        row = {
            "code": record["code"],
            "name": record["name"],
            "history_years": round(record["history_years"], 4),
            "nav_observations": record["nav_observations"],
            "start_date": record["start_date"],
            "end_date": record["end_date"],
            "fund_type": record["fund_type"],
            "tracking_index": record["tracking_index"],
            "management_fee_pct": record["management_fee_pct"],
            "duration_years": record["duration_years"],
            "decision": "selected" if is_selected else "rejected",
            "reason": reason,
        }

        if is_selected:
            selected.append(row)
        else:
            rejected.append(row)

        print(f"[{index}/{len(etfs)}] {row['code']} {row['name']} -> {row['decision']} ({reason})")
        if sleep_seconds > 0:
            time.sleep(sleep_seconds)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    base_dir = REPORTS_ROOT / spec.slug
    markdown_path = base_dir / f"{timestamp}_{spec.slug}.md"
    json_path = base_dir / f"{timestamp}_{spec.slug}.json"
    csv_path = base_dir / f"{timestamp}_{spec.slug}.csv"

    payload = {
        "spec": {
            "name": spec.name,
            "slug": spec.slug,
            "description": spec.description,
            "min_history_years": spec.min_history_years,
            "max_management_fee": spec.max_management_fee,
        },
        "selected": selected,
        "rejected": rejected,
    }
    output_files = {
        "markdown": str(markdown_path),
        "json": str(json_path),
        "csv": str(csv_path),
    }
    markdown = build_markdown(spec, selected, rejected, output_files)

    markdown_path.parent.mkdir(parents=True, exist_ok=True)
    markdown_path.write_text(markdown, encoding="utf-8")
    write_json(json_path, payload)
    write_csv(csv_path, selected)

    print(f"Report written to: {markdown_path}")
    print(f"JSON written to: {json_path}")
    print(f"CSV written to: {csv_path}")

    return payload


def build_base_parser(description: str) -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=description)
    parser.add_argument("--limit", type=int, default=0, help="Only inspect the first N ETFs from finshare for debugging.")
    parser.add_argument("--sleep-seconds", type=float, default=0.0, help="Pause between ETF requests to reduce source pressure.")
    return parser
