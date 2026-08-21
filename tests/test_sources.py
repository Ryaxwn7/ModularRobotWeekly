import unittest
from datetime import date
from unittest.mock import patch

from daily_research_agent.sources import CrossrefSource, OpenAlexSource, abstract_from_inverted_index


class SourceTests(unittest.TestCase):
    def test_crossref_merges_relevance_and_recent_results(self) -> None:
        item = {
            "title": ["Self-reconfiguring modular robotic boats"],
            "DOI": "10.1038/s41467-026-74527-6",
            "URL": "https://doi.org/10.1038/s41467-026-74527-6",
            "container-title": ["Nature Communications"],
            "publisher": "Springer Science and Business Media LLC",
            "published-online": {"date-parts": [[2026, 7, 9]]},
            "published-print": {"date-parts": [[2027, 1, 1]]},
            "author": [{"given": "Wei", "family": "Wang"}],
            "type": "journal-article",
        }

        with patch(
            "daily_research_agent.sources.fetch_json",
            return_value={"message": {"items": [item]}},
        ) as mocked_fetch:
            papers = list(
                CrossrefSource().search(
                    "modular self-reconfigurable robot",
                    since=date(2026, 7, 1),
                    limit=50,
                )
            )

        self.assertEqual(mocked_fetch.call_count, 2)
        self.assertEqual(len(papers), 1)
        self.assertEqual(papers[0].published, "2026-07-09")
        self.assertEqual(papers[0].doi, "10.1038/s41467-026-74527-6")

    def test_openalex_result_is_converted_to_paper(self) -> None:
        response = {
            "results": [
                {
                    "id": "https://openalex.org/W1",
                    "doi": "https://doi.org/10.0000/example",
                    "title": "Robot learning with embodied intelligence",
                    "publication_year": 2026,
                    "publication_date": "2026-08-01",
                    "primary_location": {
                        "landing_page_url": "https://doi.org/10.0000/example",
                        "source": {
                            "display_name": "Nature Machine Intelligence",
                            "host_organization_name": "Springer Nature",
                        },
                    },
                    "authorships": [{"author": {"display_name": "Ada Researcher"}}],
                    "abstract_inverted_index": {"Robot": [0], "learning": [1]},
                    "open_access": {"oa_url": "https://example.com/paper"},
                    "topics": [{"display_name": "Robot Learning"}],
                    "keywords": [{"display_name": "Embodied AI"}],
                    "cited_by_count": 2,
                    "type": "article",
                }
            ]
        }

        with patch("daily_research_agent.sources.fetch_json", return_value=response):
            papers = list(OpenAlexSource().search("robot learning", date(2026, 7, 1), 50))

        self.assertEqual(len(papers), 1)
        self.assertEqual(papers[0].doi, "10.0000/example")
        self.assertEqual(papers[0].abstract, "Robot learning")
        self.assertEqual(papers[0].venue, "Nature Machine Intelligence")

    def test_abstract_from_inverted_index_handles_missing_values(self) -> None:
        self.assertEqual(abstract_from_inverted_index(None), "")


if __name__ == "__main__":
    unittest.main()
