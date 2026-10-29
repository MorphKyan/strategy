import json

import pytest

from src.platform_core.storage import InMemoryStore, SQLiteStore, write_csv_rows, write_json
from src.platform_core.strategy import MonthlyEqualWeightStrategy, Strategy


@pytest.mark.parametrize("payload,error", [({"bad": object()}, TypeError), ({"bad": float("nan")}, ValueError)])
def test_json_write_failure_preserves_existing_file(tmp_path, payload, error):
    path = tmp_path / "state.json"
    path.write_text('{"cash": 100}')
    with pytest.raises(error):
        write_json(path, payload)
    assert json.loads(path.read_text()) == {"cash": 100}
    assert list(tmp_path.iterdir()) == [path]


def test_json_write_creates_parent_and_replaces_snapshot(tmp_path):
    path = tmp_path / "portfolio" / "state.json"
    write_json(path, {"cash": 100})
    write_json(path, {"cash": 200, "name": "组合"})
    assert json.loads(path.read_text(encoding="utf-8")) == {"cash": 200, "name": "组合"}
    assert list(path.parent.iterdir()) == [path]


@pytest.mark.parametrize("persisted", [True, False])
def test_builtin_versions_are_deduplicated_by_source_and_parameters(tmp_path, persisted):
    store = SQLiteStore(tmp_path / "metadata.sqlite") if persisted else InMemoryStore()
    try:
        first = store.ensure_builtin_version(MonthlyEqualWeightStrategy, {"universe": ["A"]})
        assert store.ensure_builtin_version(MonthlyEqualWeightStrategy, {"universe": ["A"]}) == first
        assert store.ensure_builtin_version(MonthlyEqualWeightStrategy, {"universe": ["B"]}) != first
        assert store.get_strategy_version(first)["name"] == MonthlyEqualWeightStrategy.name
    finally:
        store.close()


@pytest.mark.parametrize("persisted", [True, False])
def test_invalid_strategy_parameters_are_not_stored(tmp_path, persisted):
    store = SQLiteStore(tmp_path / "metadata.sqlite") if persisted else InMemoryStore()
    try:
        with pytest.raises(ValueError):
            store.ensure_builtin_version(MonthlyEqualWeightStrategy, {"bad": float("nan")})
        if persisted:
            assert store.conn.execute("SELECT COUNT(*) FROM strategy_versions").fetchone()[0] == 0
        else:
            assert not store.versions
    finally:
        store.close()


@pytest.mark.parametrize("persisted", [True, False])
def test_parent_strategy_change_creates_a_new_version(tmp_path, monkeypatch, persisted):
    from src.platform_core import storage

    store = SQLiteStore(tmp_path / "metadata.sqlite") if persisted else InMemoryStore()
    try:
        first = store.ensure_builtin_version(MonthlyEqualWeightStrategy)
        original_source = storage.inspect.getsource
        monkeypatch.setattr(storage.inspect, "getsource", lambda cls: original_source(cls) + (
            "\n# parent implementation changed" if cls is Strategy else ""))
        assert store.ensure_builtin_version(MonthlyEqualWeightStrategy) != first
    finally:
        store.close()


def test_csv_run_artifacts_cannot_overwrite_existing_files(tmp_path):
    path = tmp_path / "run/nav.csv"
    write_csv_rows(path, [{"date": "2024-01-01", "total_value": 1000}])
    before = path.read_bytes()
    with pytest.raises(FileExistsError):
        write_csv_rows(path, [])
    assert path.read_bytes() == before


@pytest.mark.parametrize("persisted", [True, False])
def test_sim_registry_updates_preserve_creation_and_origin(tmp_path, monkeypatch, persisted):
    from datetime import datetime
    from src.platform_core import storage

    class Clock:
        day = 0

        @classmethod
        def now(cls):
            cls.day += 1
            return datetime(2024, 1, cls.day)

    monkeypatch.setattr(storage, "datetime", Clock)
    store = SQLiteStore(tmp_path / "registry.sqlite") if persisted else InMemoryStore()
    try:
        store.create_sim_portfolio("test", "original.json", "state1.json", {})
        store.create_sim_portfolio("test", "resumed.json", "state2.json", {"updated": True})
        record = (store.conn.execute("SELECT * FROM sim_portfolios WHERE portfolio_id = 'test'").fetchone()
                  if persisted else store.sim_portfolios["test"])
        assert record["source_checkpoint"] == "original.json"
        assert record["created_at"] == "2024-01-01T00:00:00"
        assert record["updated_at"] == "2024-01-02T00:00:00"
        assert record["state_path"] == "state2.json"
    finally:
        store.close()
