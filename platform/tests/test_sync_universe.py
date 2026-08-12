from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest
import yaml

from scripts.fetch_etf_dividends import (
    _merge_scoped_events,
    dividend_text,
    parse_dividend,
    sync_etf_corporate_actions,
)
from src.platform_core.corporate_actions import merge_event_table
from src.platform_core.sync_universe import (
    etf_assets,
    load_assets_from_configs,
    merge_assets,
    parse_asset_spec,
)


def _asset(code: str, asset_type: str = "etf", exchange: str = "SH") -> dict:
    prefix = "CN_ETF" if asset_type == "etf" else "CN_INDEX"
    return {
        "asset_id": f"{prefix}:{code}.{exchange}",
        "code": code,
        "name": code,
        "asset_type": asset_type,
        "exchange": exchange,
        "currency": "CNY",
        "lot_size": 100,
        "price_limit_pct": 0.1,
    }


def test_load_assets_from_multiple_configs_deduplicates(tmp_path: Path):
    first = tmp_path / "first.yaml"
    second = tmp_path / "second.yaml"
    first.write_text(yaml.safe_dump({"assets": [_asset("511090")]}), encoding="utf-8")
    second.write_text(
        yaml.safe_dump({"assets": [_asset("511090"), _asset("000300", "index")]}),
        encoding="utf-8",
    )

    assets = load_assets_from_configs([first, second])

    assert [asset["code"] for asset in assets] == ["000300", "511090"]
    assert [asset["code"] for asset in etf_assets(assets)] == ["511090"]


def test_direct_asset_spec_and_config_assets_can_be_merged():
    configured = [_asset("510300")]
    direct = parse_asset_spec("511090.SH=30年国债ETF")

    assets = merge_assets(configured, [direct])

    assert [asset["code"] for asset in assets] == ["510300", "511090"]
    assert direct["name"] == "30年国债ETF"


def test_direct_non_etf_asset_is_supported_but_not_selected_for_actions():
    direct = parse_asset_spec("000300.SH:index=沪深300指数")

    assert direct["asset_id"] == "CN_INDEX:000300.SH"
    assert direct["asset_type"] == "index"
    assert etf_assets([direct]) == []


def test_per_ten_share_dividend_schema_is_normalized_to_per_share():
    row = pd.Series({"每10份分红": "每10份派现金15.0000元"})

    raw = dividend_text(row)

    assert raw == "每10份派现金15.0000元"
    assert parse_dividend(raw) == 1.5


def test_scoped_merge_retains_unrequested_symbols_without_missing_warnings():
    existing = pd.DataFrame(
        [
            {"code": "510300", "ex_date": "2025-01-01", "dividend_per_share": "0.1"},
            {"code": "511090", "ex_date": "2024-04-24", "dividend_per_share": "1.5"},
        ]
    )
    fetched = pd.DataFrame(
        [{"code": "511090", "ex_date": "2025-12-01", "dividend_per_share": "1.5"}]
    )

    merged, notes, additions = _merge_scoped_events(
        existing, fetched, ["code", "ex_date"], merge_event_table
    )

    assert set(merged["code"]) == {"510300", "511090"}
    assert notes == ["上游缺失本地已有事件 [('511090', '2024-04-24')]（已保留，不删除）"]
    assert additions[0]["ex_date"] == "2025-12-01"


def test_scoped_merge_does_not_accept_first_candidate_before_validation():
    existing = pd.DataFrame(
        [{"code": "510300", "split_date": "2012-05-11", "split_ratio": "5.0"}]
    )
    fetched = pd.DataFrame(
        [{"code": "511090", "split_date": "2023-05-29", "split_ratio": "0.01"}]
    )

    merged, notes, additions = _merge_scoped_events(
        existing, fetched, ["code", "split_date"], merge_event_table
    )

    assert list(merged["code"]) == ["510300"]
    assert notes == []
    assert additions == [
        {"code": "511090", "split_date": "2023-05-29", "split_ratio": "0.01"}
    ]


class _FakeAkshare:
    def __init__(self):
        self.calls: list[tuple[str, str]] = []

    def fund_open_fund_info_em(self, symbol: str, indicator: str) -> pd.DataFrame:
        self.calls.append((symbol, indicator))
        if symbol == "511090" and indicator == "分红送配详情":
            return pd.DataFrame(
                [
                    {
                        "年份": "2025年",
                        "权益登记日": "2025-11-28",
                        "除息日": "2025-12-01",
                        "每份分红": "每10份派15元",
                        "分红发放日": "2025-12-04",
                    }
                ]
            )
        return pd.DataFrame()


class _PartiallyFailingAkshare(_FakeAkshare):
    def fund_open_fund_info_em(self, symbol: str, indicator: str) -> pd.DataFrame:
        self.calls.append((symbol, indicator))
        if symbol == "511090" and indicator == "分红送配详情":
            raise RuntimeError("upstream unavailable")
        return pd.DataFrame()


def test_corporate_action_sync_queries_every_supplied_etf_and_excludes_index(tmp_path: Path):
    client = _FakeAkshare()

    sync_etf_corporate_actions(
        [_asset("511090"), _asset("510300"), _asset("000300", "index")],
        data_dir=tmp_path,
        client=client,
    )

    assert set(client.calls) == {
        ("511090", "分红送配详情"),
        ("511090", "拆分详情"),
        ("510300", "分红送配详情"),
        ("510300", "拆分详情"),
    }
    dividends = pd.read_csv(tmp_path / "platform_dividends.csv", dtype={"code": str})
    assert len(dividends) == 1
    assert dividends.iloc[0]["code"] == "511090"
    assert dividends.iloc[0]["dividend_per_share"] == 1.5
    assert dividends.iloc[0]["payment_date"] == "2025-12-04"


def test_corporate_action_sync_attempts_all_etfs_before_reporting_failures(tmp_path: Path):
    client = _PartiallyFailingAkshare()

    with pytest.raises(RuntimeError, match="511090 dividends"):
        sync_etf_corporate_actions(
            [_asset("511090"), _asset("510300")],
            data_dir=tmp_path,
            client=client,
        )

    assert ("510300", "分红送配详情") in client.calls
    assert ("510300", "拆分详情") in client.calls
