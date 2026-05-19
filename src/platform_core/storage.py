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
