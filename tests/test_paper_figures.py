import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from scripts.discover_paper_figures import FigureParser, discover_paper, supported_image


class PaperFigureTests(unittest.TestCase):
    def test_selects_article_figure_and_excludes_related_paper_and_logo(self):
        parser = FigureParser("https://www.nature.com/articles/s41467-test", "10.1038/s41467-test")
        parser.feed('''<img src="/logo.png" alt="Logo">
            <img src="https://media.springernature.com/image/art%3A10.1038%2Fother/MediaObjects/other_Fig1_HTML.png">
            <figure><img src="https://media.springernature.com/image/art%3A10.1038%2Fs41467-test/MediaObjects/test_Fig1_HTML.png" alt="Fig. 1: Robot platform."></figure>''')
        self.assertEqual(len(parser.candidates), 1)
        self.assertIn("test_Fig1", parser.candidates[0]["url"])

    def test_lazy_loaded_relative_figure_is_resolved(self):
        parser = FigureParser("https://publisher.test/papers/42")
        parser.feed('<figure><img src="data:image/gif;base64,x" data-src="/images/architecture.png" alt="Robot architecture"></figure>')
        self.assertEqual(parser.candidates[0]["url"], "https://publisher.test/images/architecture.png")

    def test_does_not_accept_html_disguised_as_image(self):
        self.assertEqual(supported_image(b"<html>Access denied</html>", "image/png"), "")

    def test_mismatched_publisher_doi_is_not_used(self):
        content = b'<meta name="citation_doi" content="10.1000/other"><figure><img src="/fig1.png"></figure>'
        with tempfile.TemporaryDirectory() as temp, patch(
            "scripts.discover_paper_figures.read_url", return_value=(content, "https://publisher.test/paper")
        ) as fetch:
            result = discover_paper({"doi": "10.1000/target", "title": "Target paper"}, Path(temp), 1)
        self.assertEqual(result["status"], "unavailable")
        self.assertEqual(fetch.call_count, 1)
        self.assertIn("does not match", result["attempts"][0]["error"])


if __name__ == "__main__":
    unittest.main()
