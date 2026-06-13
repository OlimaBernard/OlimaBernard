from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Dict

import yaml

ROOT = Path(__file__).resolve().parents[1]


def root_path(*parts: str) -> Path:
    return ROOT.joinpath(*parts)


def ensure_dirs() -> None:
    for folder in ["data/csv_fallback", "data/news_cache", "models", "reports", "logs"]:
        root_path(folder).mkdir(parents=True, exist_ok=True)


def load_yaml(path: str | Path) -> Dict[str, Any]:
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def load_settings() -> Dict[str, Any]:
    return load_yaml(root_path("config", "settings.yaml"))


def load_symbols() -> Dict[str, list[str]]:
    return load_yaml(root_path("config", "symbols.yaml"))


def flatten_symbols(symbols_cfg: Dict[str, list[str]]) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for group, symbols in symbols_cfg.items():
        for symbol in symbols or []:
            rows.append({"symbol": symbol, "group": group})
    return rows


def is_synthetic(group: str) -> bool:
    return group.lower() == "synthetics"


def safe_symbol_name(symbol: str) -> str:
    return (
        symbol.replace(" ", "")
        .replace("/", "")
        .replace(".", "")
        .replace("#", "")
        .replace("(", "")
        .replace(")", "")
    )


def read_json(path: str | Path, default: Any) -> Any:
    p = Path(path)
    if not p.exists():
        return default
    with open(p, "r", encoding="utf-8") as f:
        return json.load(f)


def write_json(path: str | Path, data: Any) -> None:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    with open(p, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, default=str)


def timeframe_name(tf: str) -> str:
    return "daily" if tf.upper() == "D1" else "weekly"
