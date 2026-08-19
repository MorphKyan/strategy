from __future__ import annotations

from pathlib import Path
from typing import Any, Iterable

import yaml


EXCLUDED_CONFIG_DIRS = {"archive", "archived", "generated"}


def discover_fixed_configs(config_dir: str | Path) -> list[Path]:
    """Return fixed platform YAML configs, excluding generated/archived trees."""
    root = Path(config_dir)
    return sorted(
        path
        for path in root.rglob("*.yaml")
        if not EXCLUDED_CONFIG_DIRS.intersection(path.relative_to(root).parts)
    )


def load_assets_from_configs(config_paths: Iterable[str | Path]) -> list[dict[str, Any]]:
    """Load and de-duplicate asset mappings from one or more platform configs."""
    assets: dict[str, dict[str, Any]] = {}
    for raw_path in config_paths:
        path = Path(raw_path)
        with path.open("r", encoding="utf-8") as handle:
            config = yaml.safe_load(handle) or {}
        for raw_asset in config.get("assets", []) or []:
            asset = dict(raw_asset)
            _validate_asset(asset, source=str(path))
            key = str(asset["asset_id"])
            existing = assets.get(key)
            if existing is not None and _asset_identity(existing) != _asset_identity(asset):
                raise ValueError(
                    f"Conflicting definitions for {key}: "
                    f"{_asset_identity(existing)} != {_asset_identity(asset)} ({path})"
                )
            assets.setdefault(key, asset)
    return sorted(assets.values(), key=_asset_sort_key)


def parse_asset_spec(spec: str) -> dict[str, Any]:
    """Parse ``CODE[.EXCHANGE][:TYPE][=NAME]``; TYPE defaults to ``etf``."""
    code_exchange, separator, name = spec.partition("=")
    identity, type_separator, explicit_type = code_exchange.strip().partition(":")
    asset_type = explicit_type.strip().lower() if type_separator else "etf"
    if not asset_type:
        raise ValueError(f"Invalid --asset value: {spec!r}")
    parts = identity.upper().split(".")
    if len(parts) > 2 or not parts[0]:
        raise ValueError(f"Invalid --asset value: {spec!r}")
    code = parts[0]
    if len(parts) == 2:
        exchange = parts[1]
    elif asset_type == "etf":
        exchange = _infer_exchange(code)
    else:
        raise ValueError(f"Exchange is required for non-ETF --asset value: {spec!r}")
    if asset_type == "etf" and exchange not in {"SH", "SZ"}:
        raise ValueError(f"ETF exchange must be SH or SZ in --asset value: {spec!r}")
    prefix = {"etf": "CN_ETF", "index": "CN_INDEX", "futures": "CN_FUTURES"}.get(
        asset_type, f"CN_{asset_type.upper()}"
    )
    return {
        "asset_id": f"{prefix}:{code}.{exchange}",
        "code": code,
        "name": name.strip() if separator and name.strip() else code,
        "asset_type": asset_type,
        "exchange": exchange,
        "currency": "CNY",
        "lot_size": 100 if asset_type == "etf" else 1,
        "price_limit_pct": 0.1 if asset_type == "etf" else None,
    }


def merge_assets(*groups: Iterable[dict[str, Any]]) -> list[dict[str, Any]]:
    """Merge asset groups by asset_id and reject conflicting identities."""
    merged: dict[str, dict[str, Any]] = {}
    for group in groups:
        for raw_asset in group:
            asset = dict(raw_asset)
            _validate_asset(asset, source="asset arguments")
            key = str(asset["asset_id"])
            existing = merged.get(key)
            if existing is not None and _asset_identity(existing) != _asset_identity(asset):
                raise ValueError(f"Conflicting definitions for {key}")
            merged.setdefault(key, asset)
    return sorted(merged.values(), key=_asset_sort_key)


def etf_assets(assets: Iterable[dict[str, Any]]) -> list[dict[str, Any]]:
    return [dict(asset) for asset in assets if str(asset.get("asset_type", "")).lower() == "etf"]


def _asset_identity(asset: dict[str, Any]) -> tuple[str, str, str]:
    return (
        str(asset.get("code", "")),
        str(asset.get("exchange", "")),
        str(asset.get("asset_type", "")),
    )


def _asset_sort_key(asset: dict[str, Any]) -> tuple[str, str, str]:
    return (
        str(asset.get("code", "")),
        str(asset.get("exchange", "")),
        str(asset.get("asset_type", "")),
    )


def _validate_asset(asset: dict[str, Any], source: str) -> None:
    missing = [key for key in ("asset_id", "code", "exchange", "asset_type") if not asset.get(key)]
    if missing:
        raise ValueError(f"Asset in {source} is missing required fields: {missing}")


def _infer_exchange(code: str) -> str:
    if code.startswith(("5", "6", "9")):
        return "SH"
    if code.startswith(("0", "1", "3")):
        return "SZ"
    raise ValueError(f"Cannot infer ETF exchange for code {code!r}; use CODE.SH or CODE.SZ")
