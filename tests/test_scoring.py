import unittest
from datetime import date

from daily_research_agent.models import Paper
from daily_research_agent.scoring import (
    classify_content_types,
    classify_scope_topics,
    has_robotics_relevance,
    is_future_paper,
    score_paper,
)


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

    def test_generic_biomimetic_structure_is_rejected_without_target_scope(self) -> None:
        paper = Paper(
            title="Bio-inspired soft robot structure design",
            abstract="A biomimetic morphology improves locomotion and adaptive contact.",
        )

        self.assertFalse(has_robotics_relevance(paper))

    def test_biomimetic_modular_structure_is_accepted(self) -> None:
        paper = Paper(
            title="Bio-inspired connector design for modular robots",
            abstract="The robot modules self-assemble into adaptive morphologies.",
        )

        self.assertTrue(has_robotics_relevance(paper))

    def test_bioinspired_material_without_robotics_context_is_rejected(self) -> None:
        paper = Paper(
            title="Bio-inspired cementitious composites",
            abstract="Organic-inorganic copolymers self-assemble into strong construction materials.",
        )

        self.assertFalse(has_robotics_relevance(paper))

    def test_generic_swarm_optimizer_is_rejected(self) -> None:
        paper = Paper(
            title="Particle swarm optimization for symbolic logic",
            abstract="The optimizer tunes a neural network for satisfiability problems.",
        )

        self.assertFalse(has_robotics_relevance(paper))

    def test_robot_swarm_emergence_theory_is_tagged(self) -> None:
        config = {
            "ranking": {
                "preferred_venues": [],
                "publisher_keywords": [],
                "method_keywords": [
                    "self-organization",
                    "emergence",
                    "mean-field",
                    "phase transition",
                ],
            }
        }
        paper = Paper(
            title="Self-organization and emergent collective behavior in robot swarms",
            abstract=(
                "A mean-field model identifies a phase transition and order parameter "
                "for decentralized robotic agents."
            ),
        )

        self.assertTrue(has_robotics_relevance(paper))
        scored = score_paper(paper, config, "swarm_self_organization_emergence", 1.2)
        self.assertIn("self_organization", scored.tags)
        self.assertIn("emergence", scored.tags)
        self.assertIn("collective_dynamics", scored.tags)
        self.assertIn("theory", scored.tags)

    def test_non_robotic_active_matter_emergence_is_rejected(self) -> None:
        paper = Paper(
            title="Emergent phase transitions in active matter",
            abstract="Self-organizing particles exhibit a collective order parameter.",
        )

        self.assertFalse(has_robotics_relevance(paper))

    def test_review_is_classified_without_design_labels(self) -> None:
        paper = Paper(
            title="A systematic review of modular robot control algorithms",
            abstract="This survey covers mechanisms, planning, and learning.",
            tags=["structure", "algorithm"],
        )

        self.assertEqual(classify_content_types(paper), ["review"])

    def test_hybrid_hardware_and_control_paper_has_two_content_types(self) -> None:
        paper = Paper(
            title="Docking mechanism and distributed control for modular robots",
            abstract="The prototype combines a connector with a planning algorithm.",
        )

        self.assertEqual(
            classify_content_types(paper),
            ["structure_design", "algorithm_design"],
        )

    def test_embodied_robot_learning_topics_are_rejected(self) -> None:
        paper = Paper(
            title="Vision-language-action foundation model for embodied intelligence",
            abstract="The policy transfers to robotic manipulation tasks.",
        )

        self.assertFalse(has_robotics_relevance(paper))

    def test_humanoid_robot_is_rejected_even_with_swarm_language(self) -> None:
        paper = Paper(
            title="Coordination policies for a humanoid robot team",
            abstract="Multiple humanoid robots perform collective transport.",
        )

        self.assertFalse(has_robotics_relevance(paper))

    def test_scope_topics_are_inferred_from_content_not_query_history(self) -> None:
        paper = Paper(
            title="Bio-inspired decision making in robot swarms",
            abstract="A collective control algorithm produces emergent behavior.",
            topics=["robot_learning_embodied_ai"],
        )

        self.assertEqual(
            classify_scope_topics(paper),
            [
                "swarm_intelligence_robotics",
                "swarm_self_organization_emergence",
                "bioinspired_swarm_algorithms",
            ],
        )

    def test_venue_tier_bonus_is_applied(self) -> None:
        config = {
            "ranking": {
                "preferred_venues": [],
                "publisher_keywords": [],
                "method_keywords": [],
                "venue_tiers": [
                    {"name": "top_tier", "bonus": 3.5, "venues": ["Nature Communications"]}
                ],
            }
        }
        paper = Paper(title="A modular robotic platform", venue="Nature Communications")

        scored = score_paper(paper, config, "modular_reconfigurable_robotics", 1.0)

        self.assertEqual(scored.score, 5.5)
        self.assertIn("top_tier venue: Nature Communications", scored.reasons)


if __name__ == "__main__":
    unittest.main()
