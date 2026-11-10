import unittest

from daily_research_agent.models import Paper
from daily_research_agent.pipeline import ResearchPipeline
from daily_research_agent.models import retain_richer_abstract
from daily_research_agent.store import merge_papers


class PipelineDedupeTests(unittest.TestCase):
    def test_dedupe_keeps_abstract_from_lower_ranked_duplicate(self) -> None:
        crossref = Paper(
            title="Modular robot docking",
            doi="10.1000/example",
            source="crossref",
            score=9.0,
            venue="Journal of Robotics",
        )
        openalex = Paper(
            title="Modular robot docking",
            doi="10.1000/example",
            source="openalex",
            score=7.0,
            abstract="A modular robot uses a docking mechanism for reconfiguration.",
            authors=["A. Researcher"],
        )

        result = ResearchPipeline.dedupe([crossref, openalex])
        paper = result["doi:10.1000/example"]

        self.assertEqual(paper.source, "crossref")
        self.assertEqual(paper.abstract, openalex.abstract)
        self.assertEqual(paper.authors, ["A. Researcher"])
        self.assertIn("structure", paper.tags)

    def test_doi_url_and_case_are_the_same_identity(self) -> None:
        first = Paper(title="Modular robot", doi="10.1000/EXAMPLE", score=9)
        second = Paper(title="Different metadata title", doi="https://doi.org/10.1000/example", abstract="Complete abstract.", source="openalex")
        result = ResearchPipeline.dedupe([first, second])
        self.assertEqual(len(result), 1)
        self.assertEqual(first.abstract, "Complete abstract.")
        self.assertEqual(first.raw["abstract_source"], "openalex")

    def test_conflicting_dois_never_share_abstract(self) -> None:
        first = Paper(title="Same title", doi="10.1000/a")
        second = Paper(title="Same title", doi="10.1000/b", abstract="Other paper.")
        retain_richer_abstract(first, second)
        self.assertEqual(first.abstract, "")

    def test_title_only_needs_matching_author_and_year(self) -> None:
        first = Paper(title="Modular robot", year=2026, authors=["A. Smith"])
        second = Paper(title="Modular robot", year=2026, authors=["B. Jones"], abstract="Unconfirmed.")
        retain_richer_abstract(first, second)
        self.assertEqual(first.abstract, "")
        second.authors = ["A. Smith"]
        retain_richer_abstract(first, second)
        self.assertEqual(first.abstract, "Unconfirmed.")

    def test_persistent_merge_retains_full_abstract_in_both_score_orders(self) -> None:
        for score in (1, 20):
            with self.subTest(incoming_score=score):
                old = Paper(title="Modular robot", doi="10.1000/a", abstract="Full abstract from the previous run.", score=10)
                new = Paper(title="Modular robot", doi="10.1000/a", abstract="Short.", score=score)
                result = merge_papers({old.identity: old}, [new])
                self.assertEqual(result[old.identity].abstract, "Full abstract from the previous run.")


if __name__ == "__main__":
    unittest.main()
