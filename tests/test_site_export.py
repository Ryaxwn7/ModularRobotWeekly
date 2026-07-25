import json
import tempfile
import unittest
from pathlib import Path

from daily_research_agent.models import Paper
from daily_research_agent.site_export import paper_to_site_item, upsert_site_papers


class SiteExportTests(unittest.TestCase):
    def test_site_item_contains_required_display_fields(self) -> None:
        paper = Paper(
            title="Modular robot paper",
            abstract="A concise summary of a modular robot system.",
            doi="10.0000/example",
            url="https://example.com/paper",
            published="2026-07-20",
            venue="Science Robotics",
            topics=["modular_reconfigurable_robotics"],
            tags=["structure"],
            raw={"figure_url": "https://example.com/figure.png"},
        )

        item = paper_to_site_item(paper, "report")

        self.assertEqual(item["title"], "Modular robot paper")
        self.assertEqual(item["url"], "https://example.com/paper")
        self.assertEqual(item["figure_url"], "https://example.com/figure.png")
        self.assertTrue(item["summary"])

    def test_upsert_site_papers_dedupes_by_identity(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "papers.json"
            paper = Paper(title="Swarm robot paper", doi="10.0000/example")

            upsert_site_papers(path, [paper], "first")
            upsert_site_papers(path, [paper], "second")

            data = json.loads(path.read_text(encoding="utf-8"))
            self.assertEqual(len(data["papers"]), 1)


if __name__ == "__main__":
    unittest.main()

