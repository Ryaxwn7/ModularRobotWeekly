import json
import tempfile
import unittest
from datetime import date
from pathlib import Path
from urllib.error import HTTPError
from unittest.mock import patch

from daily_research_agent.models import Paper
from daily_research_agent.pipeline import ResearchPipeline


class SuccessfulSource:
    name = "test"

    def search(self, query: str, since: date, until: date, limit: int):
        return [
            Paper(
                title="Modular self-reconfigurable robot system",
                abstract="A modular robot changes morphology for locomotion.",
                published=until.isoformat(),
                doi="10.0000/test",
                source=self.name,
            )
        ]

    def search_venue(self, venue: str, since: date, until: date, limit: int):
        return []


class FailingSource(SuccessfulSource):
    def search(self, query: str, since: date, until: date, limit: int):
        raise RuntimeError("temporary source failure")


class RateLimitedSource(SuccessfulSource):
    name = "semantic_scholar"

    def search(self, query: str, since: date, until: date, limit: int):
        raise HTTPError("https://example.test", 429, "rate limited", {}, None)


class TemplateSummarizer:
    def summarize(self, papers, config):
        return "summary"


class PipelineCursorTests(unittest.TestCase):
    def _config(self) -> dict:
        return {
            "agent": {
                "lookback_days": 21,
                "cursor_overlap_days": 2,
                "date_chunk_days": 14,
                "max_results_per_query": 10,
                "max_report_items": 10,
                "min_score": 0,
            },
            "topics": [{"name": "modular", "weight": 1, "queries": ["modular robot"]}],
            "sources": {},
            "ranking": {"venue_watch": []},
            "storage": {
                "cursor_file": "state/cursor.json",
                "state_file": "state/papers.json",
                "report_dir": "reports",
                "site_data_file": "site/papers.json",
            },
        }

    def test_success_advances_cursor_and_failure_keeps_previous_timestamp(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            config = self._config()
            pipeline = ResearchPipeline(config, root)
            with (
                patch("daily_research_agent.pipeline.build_sources", return_value=[SuccessfulSource()]),
                patch("daily_research_agent.pipeline.build_summarizer", return_value=TemplateSummarizer()),
            ):
                result = pipeline.run()

            self.assertTrue(result.cursor_advanced)
            cursor_path = root / "state" / "cursor.json"
            first_cursor = json.loads(cursor_path.read_text(encoding="utf-8"))

            with (
                patch("daily_research_agent.pipeline.build_sources", return_value=[FailingSource()]),
                patch("daily_research_agent.pipeline.build_summarizer", return_value=TemplateSummarizer()),
            ):
                failed = pipeline.run()

            self.assertFalse(failed.cursor_advanced)
            self.assertGreater(failed.source_error_count, 0)
            self.assertGreater(failed.blocking_source_error_count, 0)
            self.assertEqual(
                json.loads(cursor_path.read_text(encoding="utf-8"))["last_successful_run"],
                first_cursor["last_successful_run"],
            )

    def test_optional_rate_limit_warns_without_blocking_cursor(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            config = self._config()
            config["sources"] = {"semantic_scholar": {"required": False}}
            pipeline = ResearchPipeline(config, root)
            with (
                patch("daily_research_agent.pipeline.build_sources", return_value=[RateLimitedSource()]),
                patch("daily_research_agent.pipeline.build_summarizer", return_value=TemplateSummarizer()),
            ):
                result = pipeline.run()

            self.assertTrue(result.cursor_advanced)
            self.assertEqual(result.source_error_count, 1)
            self.assertEqual(result.blocking_source_error_count, 0)
            report = Path(result.report_path).read_text(encoding="utf-8")
            self.assertIn("WARNING | semantic_scholar", report)


if __name__ == "__main__":
    unittest.main()
