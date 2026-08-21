from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Iterator


@dataclass(frozen=True)
class SearchWindow:
    since: date
    until: date
    anchor: datetime | None
    anchor_source: str


def _parse_datetime(value: object) -> datetime | None:
    if not isinstance(value, str) or not value.strip():
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


def _read_json(path: Path) -> dict[str, object]:
    if not path.exists():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return data if isinstance(data, dict) else {}


def resolve_search_window(
    cursor_path: Path,
    site_data_path: Path | None,
    report_date: date,
    bootstrap_days: int,
    overlap_days: int,
) -> SearchWindow:
    cursor = _read_json(cursor_path)
    anchor = _parse_datetime(cursor.get("last_successful_run"))
    source = "cursor"

    if anchor is None and site_data_path is not None:
        site_data = _read_json(site_data_path)
        anchor = _parse_datetime(site_data.get("updated_at"))
        source = "site_data"

    if anchor is None:
        since = report_date - timedelta(days=max(0, bootstrap_days))
        return SearchWindow(since, report_date, None, "bootstrap")

    since = anchor.date() - timedelta(days=max(0, overlap_days))
    return SearchWindow(min(since, report_date), report_date, anchor, source)


def iter_date_chunks(since: date, until: date, chunk_days: int) -> Iterator[tuple[date, date]]:
    if since > until:
        return
    size = max(1, chunk_days)
    start = since
    while start <= until:
        end = min(start + timedelta(days=size - 1), until)
        yield start, end
        start = end + timedelta(days=1)


def save_successful_run(
    path: Path,
    completed_at: datetime,
    search_since: date,
    search_until: date,
    report_id: str,
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "last_successful_run": completed_at.isoformat(timespec="seconds"),
        "search_since": search_since.isoformat(),
        "search_until": search_until.isoformat(),
        "report_id": report_id,
    }
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
