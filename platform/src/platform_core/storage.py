from __future__ import annotations

import csv
import hashlib
import inspect
import json
import sqlite3
from datetime import datetime
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import Any


def write_json(path: str | Path, payload: dict[str, Any]) -> None:
    """先完整写入临时文件，再替换快照；序列化失败时保留原文件。"""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = None
    try:
        with NamedTemporaryFile("w", encoding="utf-8", dir=path.parent,
                                prefix=f".{path.name}.", suffix=".tmp", delete=False) as handle:
            temporary = Path(handle.name)
            json.dump(payload, handle, ensure_ascii=False, indent=2, allow_nan=False)
        temporary.replace(path)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


def write_csv_rows(path: Path, rows: list[dict[str, Any]]) -> None:
    """为新运行写 CSV；空数据保留空文件，拒绝覆盖已有产物。"""
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x", newline="", encoding="utf-8") as handle:
        if rows:
            writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
            writer.writeheader()
            writer.writerows(rows)


JSON_ENCODER = json.JSONEncoder(ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False)


def stable_hash(payload: str) -> str:
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def strategy_source(strategy_cls: type) -> str:
    return "\n\n".join(inspect.getsource(cls) for cls in reversed(strategy_cls.__mro__) if cls is not object)


class SQLiteStore:
    def __init__(self, db_path: str | Path):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(self.db_path)
        self.conn.row_factory = sqlite3.Row
        self.initialize()

    def close(self) -> None:
        self.conn.close()

    def initialize(self) -> None:
        self.conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS strategy_versions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                version TEXT NOT NULL,
                source_hash TEXT NOT NULL,
                params_hash TEXT NOT NULL,
                source_code TEXT NOT NULL,
                params_json TEXT NOT NULL DEFAULT '{}',
                created_at TEXT NOT NULL,
                immutable INTEGER NOT NULL DEFAULT 1,
                UNIQUE(name, source_hash, params_hash)
            );
            CREATE TABLE IF NOT EXISTS backtest_records (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                run_id TEXT NOT NULL UNIQUE,
                config_hash TEXT NOT NULL,
                output_dir TEXT NOT NULL,
                created_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS strategy_references (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                strategy_version_id INTEGER NOT NULL,
                ref_type TEXT NOT NULL,
                ref_id TEXT NOT NULL,
                created_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS portfolio_references (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                strategy_version_id INTEGER NOT NULL,
                portfolio_id TEXT NOT NULL,
                created_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS checkpoint_index (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                run_id TEXT NOT NULL,
                date TEXT NOT NULL,
                path TEXT NOT NULL,
                created_at TEXT NOT NULL,
                UNIQUE(run_id, date)
            );
            CREATE TABLE IF NOT EXISTS sim_portfolios (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                portfolio_id TEXT NOT NULL UNIQUE,
                source_checkpoint TEXT NOT NULL,
                state_path TEXT NOT NULL,
                config_hash TEXT NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS sim_portfolio_runs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                portfolio_id TEXT NOT NULL,
                asof_date TEXT NOT NULL,
                output_dir TEXT NOT NULL,
                created_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS sim_portfolio_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                portfolio_id TEXT NOT NULL,
                event_type TEXT NOT NULL,
                payload_json TEXT NOT NULL,
                created_at TEXT NOT NULL
            );
            """
        )
        self.conn.commit()

    def ensure_builtin_version(self, strategy_cls: type, params: dict[str, Any] | None = None) -> int:
        source_code = strategy_source(strategy_cls)
        params_json = JSON_ENCODER.encode(params or {})
        source_hash = stable_hash(source_code)
        params_hash = stable_hash(params_json)
        existing = self.conn.execute(
            "SELECT id FROM strategy_versions WHERE name = ? AND source_hash = ? AND params_hash = ?",
            (strategy_cls.name, source_hash, params_hash),
        ).fetchone()
        if existing:
            return int(existing["id"])

        cursor = self.conn.execute(
            """
            INSERT INTO strategy_versions(name, version, source_hash, params_hash, source_code, params_json, created_at, immutable)
            VALUES (?, ?, ?, ?, ?, ?, ?, 1)
            """,
            (strategy_cls.name, strategy_cls.version, source_hash, params_hash, source_code, params_json, datetime.now().isoformat(timespec="seconds")),
        )
        self.conn.commit()
        return int(cursor.lastrowid)

    def get_strategy_version(self, version_id: int) -> sqlite3.Row:
        row = self.conn.execute("SELECT * FROM strategy_versions WHERE id = ?", (version_id,)).fetchone()
        if row is None:
            raise KeyError(f"Strategy version not found: {version_id}")
        return row

    def record_backtest(self, run_id: str, config_payload: dict[str, Any], output_dir: str | Path) -> int:
        config_json = JSON_ENCODER.encode(config_payload)
        cursor = self.conn.execute(
            "INSERT INTO backtest_records(run_id, config_hash, output_dir, created_at) VALUES (?, ?, ?, ?)",
            (run_id, stable_hash(config_json), str(output_dir), datetime.now().isoformat(timespec="seconds")),
        )
        self.conn.commit()
        return int(cursor.lastrowid)

    def add_strategy_reference(self, strategy_version_id: int, ref_type: str, ref_id: str) -> None:
        self.conn.execute(
            "INSERT INTO strategy_references(strategy_version_id, ref_type, ref_id, created_at) VALUES (?, ?, ?, ?)",
            (strategy_version_id, ref_type, ref_id, datetime.now().isoformat(timespec="seconds")),
        )
        self.conn.commit()

    def add_checkpoint(self, run_id: str, date_value: str, path: str | Path) -> None:
        self.conn.execute(
            """
            INSERT INTO checkpoint_index(run_id, date, path, created_at)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(run_id, date) DO UPDATE SET path = excluded.path, created_at = excluded.created_at
            """,
            (run_id, date_value, str(path), datetime.now().isoformat(timespec="seconds")),
        )
        self.conn.commit()

    def create_sim_portfolio(self, portfolio_id: str, source_checkpoint: str | Path, state_path: str | Path, config_payload: dict[str, Any]) -> None:
        now = datetime.now().isoformat(timespec="seconds")
        config_hash = stable_hash(JSON_ENCODER.encode(config_payload))
        self.conn.execute(
            """
            INSERT INTO sim_portfolios(portfolio_id, source_checkpoint, state_path, config_hash, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT(portfolio_id) DO UPDATE SET
                state_path = excluded.state_path,
                config_hash = excluded.config_hash,
                updated_at = excluded.updated_at
            """,
            (portfolio_id, str(source_checkpoint), str(state_path), config_hash, now, now),
        )
        self.conn.commit()

    def record_sim_run(self, portfolio_id: str, asof_date: str, output_dir: str | Path) -> None:
        self.conn.execute(
            "INSERT INTO sim_portfolio_runs(portfolio_id, asof_date, output_dir, created_at) VALUES (?, ?, ?, ?)",
            (portfolio_id, asof_date, str(output_dir), datetime.now().isoformat(timespec="seconds")),
        )
        self.conn.commit()

    def add_sim_event(self, portfolio_id: str, event_type: str, payload: dict[str, Any]) -> None:
        self.conn.execute(
            "INSERT INTO sim_portfolio_events(portfolio_id, event_type, payload_json, created_at) VALUES (?, ?, ?, ?)",
            (portfolio_id, event_type, JSON_ENCODER.encode(payload), datetime.now().isoformat(timespec="seconds")),
        )
        self.conn.commit()

    def add_portfolio_reference(self, strategy_version_id: int, portfolio_id: str) -> None:
        self.conn.execute(
            "INSERT INTO portfolio_references(strategy_version_id, portfolio_id, created_at) VALUES (?, ?, ?)",
            (strategy_version_id, portfolio_id, datetime.now().isoformat(timespec="seconds")),
        )
        self.conn.commit()

    def delete_strategy_version(self, version_id: int) -> None:
        references = self.conn.execute(
            "SELECT COUNT(*) AS count FROM strategy_references WHERE strategy_version_id = ?",
            (version_id,),
        ).fetchone()["count"]
        portfolio_references = self.conn.execute(
            "SELECT COUNT(*) AS count FROM portfolio_references WHERE strategy_version_id = ?",
            (version_id,),
        ).fetchone()["count"]
        if references or portfolio_references:
            raise ValueError(f"Strategy version {version_id} is referenced and cannot be deleted.")
        self.conn.execute("DELETE FROM strategy_versions WHERE id = ?", (version_id,))
        self.conn.commit()


class InMemoryStore:
    def __init__(self):
        self.versions: dict[int, dict[str, Any]] = {}
        self.backtests: dict[int, dict[str, Any]] = {}
        self.strategy_references: list[dict[str, Any]] = []
        self.checkpoints: list[dict[str, Any]] = []
        self.sim_portfolios: dict[str, dict[str, Any]] = {}
        self.sim_portfolio_runs: dict[int, dict[str, Any]] = {}
        self.sim_portfolio_events: list[dict[str, Any]] = []
        self.portfolio_references: list[dict[str, Any]] = []
        self._next_version_id = 1
        self._next_backtest_id = 1
        self._next_sim_run_id = 1

    def close(self) -> None:
        pass

    def ensure_builtin_version(self, strategy_cls: type, params: dict[str, Any] | None = None) -> int:
        source_code = strategy_source(strategy_cls)
        params_json = JSON_ENCODER.encode(params or {})
        source_hash = stable_hash(source_code)
        params_hash = stable_hash(params_json)
        for v_id, v in self.versions.items():
            if v["name"] == strategy_cls.name and v["source_hash"] == source_hash and v["params_hash"] == params_hash:
                return v_id
        
        version_id = self._next_version_id
        self._next_version_id += 1
        self.versions[version_id] = {
            "id": version_id,
            "name": strategy_cls.name,
            "version": strategy_cls.version,
            "source_hash": source_hash,
            "params_hash": params_hash,
            "source_code": source_code,
            "params_json": params_json,
            "created_at": datetime.now().isoformat(timespec="seconds"),
            "immutable": 1,
        }
        return version_id

    def get_strategy_version(self, version_id: int) -> dict[str, Any]:
        if version_id not in self.versions:
            raise KeyError(f"Strategy version not found: {version_id}")
        return self.versions[version_id]

    def record_backtest(self, run_id: str, config_payload: dict[str, Any], output_dir: str | Path) -> int:
        backtest_id = self._next_backtest_id
        self._next_backtest_id += 1
        self.backtests[backtest_id] = {
            "id": backtest_id,
            "run_id": run_id,
            "config_hash": stable_hash(JSON_ENCODER.encode(config_payload)),
            "output_dir": str(output_dir),
            "created_at": datetime.now().isoformat(timespec="seconds"),
        }
        return backtest_id

    def add_strategy_reference(self, strategy_version_id: int, ref_type: str, ref_id: str) -> None:
        self.strategy_references.append({
            "strategy_version_id": strategy_version_id,
            "ref_type": ref_type,
            "ref_id": ref_id,
            "created_at": datetime.now().isoformat(timespec="seconds"),
        })

    def add_checkpoint(self, run_id: str, date_value: str, path: str | Path) -> None:
        self.checkpoints = [
            c for c in self.checkpoints
            if not (c["run_id"] == run_id and c["date"] == date_value)
        ]
        self.checkpoints.append({
            "run_id": run_id,
            "date": date_value,
            "path": str(path),
            "created_at": datetime.now().isoformat(timespec="seconds"),
        })

    def create_sim_portfolio(self, portfolio_id: str, source_checkpoint: str | Path, state_path: str | Path, config_payload: dict[str, Any]) -> None:
        now = datetime.now().isoformat(timespec="seconds")
        config_hash = stable_hash(JSON_ENCODER.encode(config_payload))
        record = self.sim_portfolios.setdefault(portfolio_id, {
            "portfolio_id": portfolio_id, "source_checkpoint": str(source_checkpoint), "created_at": now,
        })
        record.update(state_path=str(state_path), config_hash=config_hash, updated_at=now)

    def record_sim_run(self, portfolio_id: str, asof_date: str, output_dir: str | Path) -> None:
        run_id = self._next_sim_run_id
        self._next_sim_run_id += 1
        self.sim_portfolio_runs[run_id] = {
            "portfolio_id": portfolio_id,
            "asof_date": asof_date,
            "output_dir": str(output_dir),
            "created_at": datetime.now().isoformat(timespec="seconds"),
        }

    def add_sim_event(self, portfolio_id: str, event_type: str, payload: dict[str, Any]) -> None:
        self.sim_portfolio_events.append({
            "portfolio_id": portfolio_id,
            "event_type": event_type,
            "payload_json": JSON_ENCODER.encode(payload),
            "created_at": datetime.now().isoformat(timespec="seconds"),
        })

    def add_portfolio_reference(self, strategy_version_id: int, portfolio_id: str) -> None:
        self.portfolio_references.append({
            "strategy_version_id": strategy_version_id,
            "portfolio_id": portfolio_id,
            "created_at": datetime.now().isoformat(timespec="seconds"),
        })

    def delete_strategy_version(self, version_id: int) -> None:
        for ref in self.strategy_references:
            if ref["strategy_version_id"] == version_id:
                raise ValueError(f"Strategy version {version_id} is referenced and cannot be deleted.")
        for ref in self.portfolio_references:
            if ref["strategy_version_id"] == version_id:
                raise ValueError(f"Strategy version {version_id} is referenced and cannot be deleted.")
        if version_id in self.versions:
            del self.versions[version_id]
