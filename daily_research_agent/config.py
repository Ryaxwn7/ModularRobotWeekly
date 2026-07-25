from __future__ import annotations

import json
import os
from copy import deepcopy
from pathlib import Path
from typing import Any


DEFAULT_CONFIG: dict[str, Any] = {
    "agent": {
        "name": "Robotics Daily Research Agent",
        "language": "zh-CN",
        "lookback_days": 14,
        "max_results_per_query": 15,
        "max_report_items": 25,
        "min_score": 4.0,
    },
    "topics": [],
    "sources": {},
    "ranking": {
        "preferred_venues": [],
        "publisher_keywords": [],
        "method_keywords": [],
    },
    "summarizer": {
        "provider": "template",
        "model": "",
        "base_url": "",
        "temperature": 0.2,
    },
    "storage": {
        "state_file": "outputs/state/papers.json",
        "report_dir": "outputs/reports",
    },
}


def deep_merge(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    merged = deepcopy(base)
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(merged.get(key), dict):
            merged[key] = deep_merge(merged[key], value)
        else:
            merged[key] = value
    return merged


def load_env_file(path: Path) -> None:
    if not path.exists():
        return
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key and key not in os.environ:
            os.environ[key] = value


def load_config(path: Path) -> dict[str, Any]:
    root = path.parent.resolve()
    load_env_file(root / ".env")

    if not path.exists():
        raise FileNotFoundError(f"Config file not found: {path}")

    data = json.loads(path.read_text(encoding="utf-8"))
    config = deep_merge(DEFAULT_CONFIG, data)

    crossref_mailto = os.getenv("CROSSREF_MAILTO")
    if crossref_mailto and "crossref" in config["sources"]:
        config["sources"]["crossref"]["mailto"] = crossref_mailto

    return config

