from datetime import date
from pathlib import Path

import pytest

from src.platform_core.live_dividends import apply_dividends, expected_income
from src.platform_core.models import PortfolioState, Position


@pytest.fixture
def account(tmp_path: Path):
    state = PortfolioState(cash=7000, positions={"A": Position("A", 300, 10)}, last_date=date(2024, 1, 29))
    dividends = tmp_path / "dividends.csv"
    dividends.write_text("code,record_date,ex_date,payment_date,dividend_per_share\n"
                         "AAA,2024-01-29,2024-01-30,2024-01-31,0.1\n")
    return state, dividends, tmp_path / "ledger.csv"


@pytest.mark.parametrize("missing_file", [False, True])
def test_confirmed_dividend_is_paid_without_source_row(account, missing_file):
    state, path, ledger = account
    apply_dividends(state, date(2024, 1, 30), path, {"AAA": "A"}, ledger)
    assert state.total_value({"A": 10}) == 10030
    if missing_file:
        path.unlink()
    else:
        path.write_text(path.read_text().splitlines()[0] + "\n")
    for _ in range(2):
        apply_dividends(state, date(2024, 1, 31), path, {"AAA": "A"}, ledger)
        assert state.cash == 7030
        assert not state.dividend_receivables


def test_distinct_dividends_can_have_identical_amount_and_payment_date(account):
    state, path, ledger = account
    with path.open("a") as handle:
        handle.write("AAA,2024-01-30,2024-01-30,2024-01-31,0.1\n")
    apply_dividends(state, date(2024, 1, 30), path, {"AAA": "A"}, ledger)
    assert state.total_value({"A": 10}) == 10060
    apply_dividends(state, date(2024, 1, 31), path, {"AAA": "A"}, ledger)
    assert state.cash == 7060
    assert not state.dividend_receivables


def test_ledger_trades_after_snapshot_update_record_date_entitlement(account):
    state, path, ledger = account
    path.write_text(path.read_text().replace("2024-01-29,2024-01-30", "2024-01-30,2024-01-31"))
    ledger.write_text("date,code,event,quantity\n2024-01-29,AAA,BUY,300\n2024-01-30,AAA,SELL,100\n")
    apply_dividends(state, date(2024, 1, 31), path, {"AAA": "A"}, ledger)
    assert state.cash == 7020


@pytest.mark.parametrize("value", ["nan", "inf", "-0.1"])
def test_invalid_dividend_amount_fails_before_credit(account, value):
    state, path, ledger = account
    path.write_text(path.read_text().replace(",0.1", f",{value}"))
    with pytest.raises(ValueError, match="股息"):
        apply_dividends(state, date(2024, 1, 31), path, {"AAA": "A"}, ledger)
    assert state.cash == 7000


def test_existing_legacy_receivable_is_not_accrued_twice(account):
    state, path, ledger = account
    state.dividend_receivables = [{"asset_id": "A", "payment_date": date(2024, 1, 31), "amount": 30}]
    apply_dividends(state, date(2024, 1, 30), path, {"AAA": "A"}, ledger)
    assert state.total_value({"A": 10}) == 10030


def test_dividend_ledger_does_not_require_trade_quantity_or_fee(account):
    state, _, ledger = account
    ledger.write_text("date,code,event,quantity,gross_amount,fee\n2024-01-30,AAA,DIVIDEND_RECEIVABLE,,30,\n")
    assert expected_income(state, ledger, date(2024, 1, 31)) == 30


def test_partial_sell_ledger_marks_income_unknown(account):
    state, _, ledger = account
    ledger.write_text("date,code,event,quantity,gross_amount,fee\n2024-01-30,AAA,SELL,100,1100,1\n")
    assert expected_income(state, ledger, date(2024, 1, 31)) is None


@pytest.mark.parametrize("event,quantity,gross,fee", [
    ("BUY", "nan", "1000", "0"), ("BUY", "100", "nan", "0"),
    ("BUY", "100", "1000", "-1"), ("DIVIDEND_RECEIVABLE", "", "inf", ""),
])
def test_invalid_ledger_numbers_fail_explicitly(account, event, quantity, gross, fee):
    state, _, ledger = account
    ledger.write_text(f"date,code,event,quantity,gross_amount,fee\n2024-01-30,AAA,{event},{quantity},{gross},{fee}\n")
    with pytest.raises(ValueError, match="流水"):
        expected_income(state, ledger, date(2024, 1, 31))
