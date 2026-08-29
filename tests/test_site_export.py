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
            content_types=["structure_design"],
            raw={"figure_url": "https://example.com/figure.png"},
        )

        item = paper_to_site_item(paper, "report")

        self.assertEqual(item["title"], "Modular robot paper")
        self.assertEqual(item["url"], "https://doi.org/10.0000/example")
        self.assertEqual(item["figure_url"], "https://example.com/figure.png")
        self.assertTrue(item["summary"])
        self.assertEqual(item["content_types"], ["structure_design"])

    def test_site_export_infers_content_type_when_missing(self) -> None:
        paper = Paper(
            title="Learning-based coordination algorithm for robot swarms",
            abstract="A distributed control policy coordinates the robots.",
        )

        item = paper_to_site_item(paper, "report")

        self.assertEqual(item["content_types"], ["algorithm_design"])

    def test_consensus_url_is_not_exported_as_original_paper(self) -> None:
        paper = Paper(
            title="Consensus result",
            url="https://consensus.app/papers/example/123",
            raw={"original_url": "https://arxiv.org/abs/2604.21894"},
        )

        item = paper_to_site_item(paper, "report")

        self.assertEqual(item["url"], "https://arxiv.org/abs/2604.21894")

    def test_consensus_only_url_is_removed(self) -> None:
        paper = Paper(
            title="Consensus-only result",
            url="https://consensus.app/papers/example/123",
        )

        item = paper_to_site_item(paper, "report")

        self.assertEqual(item["url"], "")

    def test_upsert_site_papers_dedupes_by_identity(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "papers.json"
            paper = Paper(title="Swarm robot paper", doi="10.0000/example")

            upsert_site_papers(path, [paper], "first")
            upsert_site_papers(path, [paper], "second")

            data = json.loads(path.read_text(encoding="utf-8"))
            self.assertEqual(len(data["papers"]), 1)

    def test_upsert_removes_legacy_humanoid_and_out_of_scope_items(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "papers.json"
            path.write_text(
                json.dumps(
                    {
                        "papers": [
                            {"id": "humanoid", "title": "Versatile humanoid control"},
                            {"id": "medical", "title": "Robotic pancreas surgery"},
                            {"id": "swarm", "title": "Distributed control for robot swarms"},
                        ]
                    }
                ),
                encoding="utf-8",
            )

            upsert_site_papers(path, [], "scope-cleanup")

            data = json.loads(path.read_text(encoding="utf-8"))
            self.assertEqual([item["id"] for item in data["papers"]], ["swarm"])


if __name__ == "__main__":
    unittest.main()
