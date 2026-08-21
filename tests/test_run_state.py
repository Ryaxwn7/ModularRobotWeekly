import json
import tempfile
import unittest
from datetime import date, datetime
from pathlib import Path

from daily_research_agent.run_state import (
    iter_date_chunks,
    resolve_search_window,
    save_successful_run,
)


class RunStateTests(unittest.TestCase):
    def test_cursor_is_preferred_and_overlap_is_applied(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            cursor = root / "cursor.json"
            site = root / "papers.json"
            cursor.write_text(
                json.dumps({"last_successful_run": "2026-08-10T08:30:00"}),
                encoding="utf-8",
            )
            site.write_text(json.dumps({"updated_at": "2026-08-15T10:00:00"}), encoding="utf-8")

            window = resolve_search_window(cursor, site, date(2026, 8, 21), 21, 2)

            self.assertEqual(window.since, date(2026, 8, 8))
            self.assertEqual(window.until, date(2026, 8, 21))
            self.assertEqual(window.anchor_source, "cursor")

    def test_site_timestamp_is_used_when_cursor_is_missing(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            site = root / "papers.json"
            site.write_text(json.dumps({"updated_at": "2026-07-20T11:31:31"}), encoding="utf-8")

            window = resolve_search_window(
                root / "missing.json", site, date(2026, 8, 21), 21, 2
            )

            self.assertEqual(window.since, date(2026, 7, 18))
            self.assertEqual(window.anchor_source, "site_data")

    def test_bootstrap_window_is_used_without_saved_state(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            window = resolve_search_window(
                root / "missing.json", root / "site.json", date(2026, 8, 21), 21, 2
            )

            self.assertEqual(window.since, date(2026, 7, 31))
            self.assertEqual(window.anchor_source, "bootstrap")

    def test_long_gap_is_split_without_gaps_or_duplicate_days(self) -> None:
        chunks = list(iter_date_chunks(date(2026, 6, 1), date(2026, 7, 5), 14))

        self.assertEqual(
            chunks,
            [
                (date(2026, 6, 1), date(2026, 6, 14)),
                (date(2026, 6, 15), date(2026, 6, 28)),
                (date(2026, 6, 29), date(2026, 7, 5)),
            ],
        )

    def test_successful_run_is_persisted(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "state" / "cursor.json"
            save_successful_run(
                path,
                datetime(2026, 8, 21, 17, 0, 0),
                date(2026, 8, 8),
                date(2026, 8, 21),
                "robotics_research_20260821_170000",
            )

            saved = json.loads(path.read_text(encoding="utf-8"))
            self.assertEqual(saved["last_successful_run"], "2026-08-21T17:00:00")
            self.assertEqual(saved["search_until"], "2026-08-21")


if __name__ == "__main__":
    unittest.main()
