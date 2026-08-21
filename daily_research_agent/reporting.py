from __future__ import annotations

from datetime import date, datetime
from pathlib import Path

from .models import Paper


def paper_markdown(paper: Paper, index: int) -> str:
    authors = ", ".join(paper.authors[:6])
    if len(paper.authors) > 6:
        authors += " et al."
    lines = [
        f"### {index}. {paper.title}",
        "",
        f"- Score: {paper.score}",
        f"- Venue/Source: {paper.venue or 'Unknown'} / {paper.source}",
        f"- Published: {paper.published or paper.year or 'Unknown'}",
        f"- Authors: {authors or 'Unknown'}",
        f"- DOI: {paper.doi or 'N/A'}",
        f"- URL: {paper.url or 'N/A'}",
        f"- Topics: {', '.join(paper.topics) or 'N/A'}",
        f"- Tags: {', '.join(paper.tags) or 'N/A'}",
        f"- Ranking reasons: {'; '.join(paper.reasons) or 'N/A'}",
        "",
        "Abstract:",
        "",
        paper.abstract or "No abstract available.",
        "",
    ]
    return "\n".join(lines)


def write_report(
    report_dir: Path,
    papers: list[Paper],
    executive_summary: str,
    search_since: date | None = None,
    search_until: date | None = None,
) -> Path:
    report_dir.mkdir(parents=True, exist_ok=True)
    now = datetime.now()
    path = report_dir / f"robotics_research_{now.strftime('%Y%m%d_%H%M%S')}.md"

    content = [
        f"# Robotics Research Brief - {now.strftime('%Y-%m-%d')}",
        "",
        "## Collection Window",
        "",
        (
            f"{search_since.isoformat()} through {search_until.isoformat()}"
            if search_since and search_until
            else "Not recorded"
        ),
        "",
        "## Executive Summary",
        "",
        executive_summary,
        "",
        "## Priority Papers",
        "",
    ]
    if papers:
        for index, paper in enumerate(papers, start=1):
            content.append(paper_markdown(paper, index))
    else:
        content.append("No papers passed the configured threshold.")
    content.extend(
        [
            "",
            "## Follow-up Checklist",
            "",
            "- Check whether top-ranked papers have released code, datasets, or videos.",
            "- For modular robots, inspect morphology, connector design, actuation, and reconfiguration planning.",
            "- For swarm intelligence, inspect scalability, communication assumptions, robustness, and real-robot validation.",
            "- Mark papers worth deep reading in a reference manager.",
            "",
        ]
    )
    path.write_text("\n".join(content), encoding="utf-8")
    return path
