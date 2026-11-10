import unittest

from daily_research_agent.models import Paper
from daily_research_agent.pipeline import ResearchPipeline


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


if __name__ == "__main__":
    unittest.main()
