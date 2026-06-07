from __future__ import annotations

import hashlib
import inspect
import json
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Any


def stable_hash(payload: str) -> str:
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


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
            CREATE TABLE IF NOT EXISTS strategy_drafts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                source_code TEXT NOT NULL,
                params_json TEXT NOT NULL DEFAULT '{}',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS strategy_versions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                draft_id INTEGER,
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

    def create_draft(self, name: str, source_code: str, params: dict[str, Any] | None = None) -> int:
        now = self._now()
        cursor = self.conn.execute(
            "INSERT INTO strategy_drafts(name, source_code, params_json, created_at, updated_at) VALUES (?, ?, ?, ?, ?)",
            (name, source_code, self._json(params or {}), now, now),
        )
        self.conn.commit()
        return int(cursor.lastrowid)

    def publish_version(self, draft_id: int | None, name: str, version: str, source_code: str, params: dict[str, Any] | None = None) -> int:
        params_json = self._json(params or {})
        source_hash = stable_hash(source_code)
        params_hash = stable_hash(params_json)
        existing = self.conn.execute(
            "SELECT id FROM strategy_versions WHERE name = ? AND source_hash = ? AND params_hash = ?",
            (name, source_hash, params_hash),
        ).fetchone()
        if existing:
            return int(existing["id"])

        cursor = self.conn.execute(
            """
            INSERT INTO strategy_versions(draft_id, name, version, source_hash, params_hash, source_code, params_json, created_at, immutable)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, 1)
            """,
            (draft_id, name, version, source_hash, params_hash, source_code, params_json, self._now()),
        )
        self.conn.commit()
        return int(cursor.lastrowid)

    def ensure_builtin_version(self, strategy_cls: type, params: dict[str, Any] | None = None) -> int:
        source_code = inspect.getsource(strategy_cls)
        return self.publish_version(
            draft_id=None,
            name=strategy_cls.name,
            version=strategy_cls.version,
            source_code=source_code,
            params=params or {},
        )

    def get_strategy_version(self, version_id: int) -> sqlite3.Row:
        row = self.conn.execute("SELECT * FROM strategy_versions WHERE id = ?", (version_id,)).fetchone()
        if row is None:
            raise KeyError(f"Strategy version not found: {version_id}")
        return row

    def record_backtest(self, run_id: str, config_payload: dict[str, Any], output_dir: str | Path) -> int:
        config_json = self._json(config_payload)
        cursor = self.conn.execute(
            "INSERT INTO backtest_records(run_id, config_hash, output_dir, created_at) VALUES (?, ?, ?, ?)",
            (run_id, stable_hash(config_json), str(output_dir), self._now()),
        )
        self.conn.commit()
        return int(cursor.lastrowid)

    def add_strategy_reference(self, strategy_version_id: int, ref_type: str, ref_id: str) -> None:
        self.conn.execute(
            "INSERT INTO strategy_references(strategy_version_id, ref_type, ref_id, created_at) VALUES (?, ?, ?, ?)",
            (strategy_version_id, ref_type, ref_id, self._now()),
        )
        self.conn.commit()

    def add_checkpoint(self, run_id: str, date_value: str, path: str | Path) -> None:
        self.conn.execute(
            """
            INSERT INTO checkpoint_index(run_id, date, path, created_at)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(run_id, date) DO UPDATE SET path = excluded.path, created_at = excluded.created_at
            """,
            (run_id, date_value, str(path), self._now()),
        )
        self.conn.commit()

    def create_sim_portfolio(self, portfolio_id: str, source_checkpoint: str | Path, state_path: str | Path, config_payload: dict[str, Any]) -> int:
        now = self._now()
        config_hash = stable_hash(self._json(config_payload))
        cursor = self.conn.execute(
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
        return int(cursor.lastrowid or 0)

    def record_sim_run(self, portfolio_id: str, asof_date: str, output_dir: str | Path) -> int:
        cursor = self.conn.execute(
            "INSERT INTO sim_portfolio_runs(portfolio_id, asof_date, output_dir, created_at) VALUES (?, ?, ?, ?)",
            (portfolio_id, asof_date, str(output_dir), self._now()),
        )
        self.conn.commit()
        return int(cursor.lastrowid)

    def add_sim_event(self, portfolio_id: str, event_type: str, payload: dict[str, Any]) -> None:
        self.conn.execute(
            "INSERT INTO sim_portfolio_events(portfolio_id, event_type, payload_json, created_at) VALUES (?, ?, ?, ?)",
            (portfolio_id, event_type, self._json(payload), self._now()),
        )
        self.conn.commit()

    def add_portfolio_reference(self, strategy_version_id: int, portfolio_id: str) -> None:
        self.conn.execute(
            "INSERT INTO portfolio_references(strategy_version_id, portfolio_id, created_at) VALUES (?, ?, ?)",
            (strategy_version_id, portfolio_id, self._now()),
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

    @staticmethod
    def _json(payload: dict[str, Any]) -> str:
        return json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))

    @staticmethod
    def _now() -> str:
        return datetime.now().isoformat(timespec="seconds")


class InMemoryStore:
    def __init__(self, *args, **kwargs):
        self.drafts: dict[int, dict[str, Any]] = {}
        self.versions: dict[int, dict[str, Any]] = {}
        self.backtests: dict[int, dict[str, Any]] = {}
        self.strategy_references: list[dict[str, Any]] = []
        self.checkpoints: list[dict[str, Any]] = []
        self.sim_portfolios: dict[str, dict[str, Any]] = {}
        self.sim_portfolio_runs: dict[int, dict[str, Any]] = {}
        self.sim_portfolio_events: list[dict[str, Any]] = []
        self.portfolio_references: list[dict[str, Any]] = []
        self._next_draft_id = 1
        self._next_version_id = 1
        self._next_backtest_id = 1
        self._next_sim_portfolio_id = 1
        self._next_sim_run_id = 1

    def close(self) -> None:
        pass

    def initialize(self) -> None:
        pass

    def create_draft(self, name: str, source_code: str, params: dict[str, Any] | None = None) -> int:
        draft_id = self._next_draft_id
        self._next_draft_id += 1
        self.drafts[draft_id] = {
            "id": draft_id,
            "name": name,
            "source_code": source_code,
            "params_json": json.dumps(params or {}),
            "created_at": self._now(),
            "updated_at": self._now(),
        }
        return draft_id

    def publish_version(self, draft_id: int | None, name: str, version: str, source_code: str, params: dict[str, Any] | None = None) -> int:
        params_json = self._json(params or {})
        source_hash = stable_hash(source_code)
        params_hash = stable_hash(params_json)
        for v_id, v in self.versions.items():
            if v["name"] == name and v["source_hash"] == source_hash and v["params_hash"] == params_hash:
                return v_id
        
        version_id = self._next_version_id
        self._next_version_id += 1
        self.versions[version_id] = {
            "id": version_id,
            "draft_id": draft_id,
            "name": name,
            "version": version,
            "source_hash": source_hash,
            "params_hash": params_hash,
            "source_code": source_code,
            "params_json": params_json,
            "created_at": self._now(),
            "immutable": 1,
        }
        return version_id

    def ensure_builtin_version(self, strategy_cls: type, params: dict[str, Any] | None = None) -> int:
        source_code = inspect.getsource(strategy_cls)
        return self.publish_version(
            draft_id=None,
            name=strategy_cls.name,
            version=strategy_cls.version,
            source_code=source_code,
            params=params or {},
        )

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
            "config_hash": stable_hash(self._json(config_payload)),
            "output_dir": str(output_dir),
            "created_at": self._now(),
        }
        return backtest_id

    def add_strategy_reference(self, strategy_version_id: int, ref_type: str, ref_id: str) -> None:
        self.strategy_references.append({
            "strategy_version_id": strategy_version_id,
            "ref_type": ref_type,
            "ref_id": ref_id,
            "created_at": self._now(),
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
            "created_at": self._now(),
        })

    def create_sim_portfolio(self, portfolio_id: str, source_checkpoint: str | Path, state_path: str | Path, config_payload: dict[str, Any]) -> int:
        self.sim_portfolios[portfolio_id] = {
            "portfolio_id": portfolio_id,
            "source_checkpoint": str(source_checkpoint),
            "state_path": str(state_path),
            "config_hash": stable_hash(self._json(config_payload)),
            "created_at": self._now(),
            "updated_at": self._now(),
        }
        return 1

    def record_sim_run(self, portfolio_id: str, asof_date: str, output_dir: str | Path) -> int:
        run_id = self._next_sim_run_id
        self._next_sim_run_id += 1
        self.sim_portfolio_runs[run_id] = {
            "portfolio_id": portfolio_id,
            "asof_date": asof_date,
            "output_dir": str(output_dir),
            "created_at": self._now(),
        }
        return run_id

    def add_sim_event(self, portfolio_id: str, event_type: str, payload: dict[str, Any]) -> None:
        self.sim_portfolio_events.append({
            "portfolio_id": portfolio_id,
            "event_type": event_type,
            "payload_json": self._json(payload),
            "created_at": self._now(),
        })

    def add_portfolio_reference(self, strategy_version_id: int, portfolio_id: str) -> None:
        self.portfolio_references.append({
            "strategy_version_id": strategy_version_id,
            "portfolio_id": portfolio_id,
            "created_at": self._now(),
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

    @staticmethod
    def _now() -> str:
        return datetime.now().isoformat(timespec="seconds")

    @staticmethod
    def _json(payload: dict[str, Any]) -> str:
        return json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))

