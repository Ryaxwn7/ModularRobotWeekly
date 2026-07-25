import unittest
from datetime import date

from daily_research_agent.models import Paper
from daily_research_agent.scoring import has_robotics_relevance, is_future_paper, score_paper


class ScoringTests(unittest.TestCase):
    def test_scoring_prefers_target_venues_and_tags(self) -> None:
        config = {
            "ranking": {
                "preferred_venues": ["Science Robotics"],
                "publisher_keywords": ["Science"],
                "method_keywords": ["distributed", "control", "prototype"],
            }
        }
        paper = Paper(
            title="Distributed control for a modular self-reconfigurable robot swarm",
            abstract="We present a prototype and convergence analysis.",
            venue="Science Robotics",
            publisher="Science",
            doi="10.0000/example",
        )

        scored = score_paper(paper, config, "swarm_intelligence_robotics", 1.0)

        self.assertGreaterEqual(scored.score, 7.0)
        self.assertIn("control", scored.tags)
        self.assertIn("swarm", scored.tags)
        self.assertIn("reconfiguration", scored.tags)

    def test_future_papers_are_detected(self) -> None:
        paper = Paper(
            title="A modular robot system",
            published="2026-07-21",
            year=2026,
        )

        self.assertTrue(is_future_paper(paper, date(2026, 7, 20)))

    def test_non_robotics_topics_are_rejected(self) -> None:
        paper = Paper(
            title="Digital twin optimization for building energy systems",
            abstract="This paper studies architecture and control for cyber-physical energy systems.",
        )

        self.assertFalse(has_robotics_relevance(paper))

    def test_robotics_topics_are_accepted(self) -> None:
        paper = Paper(
            title="Distributed control for modular reconfigurable robots",
            abstract="The robot modules coordinate through local communication.",
        )

        self.assertTrue(has_robotics_relevance(paper))


if __name__ == "__main__":
    unittest.main()
