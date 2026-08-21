from __future__ import annotations

from datetime import date, timedelta
from pathlib import Path
from typing import Any

from .llm import build_summarizer
from .models import Paper, PipelineResult
from .reporting import write_report
from .scoring import has_robotics_relevance, is_future_paper, parse_published_date, score_paper
from .site_export import upsert_site_papers
from .sources import build_sources
from .store import PaperStore, merge_papers


class ResearchPipeline:
    def __init__(self, config: dict[str, Any], root: Path) -> None:
        self.config = config
        self.root = root

    def run(self, dry_run: bool = False) -> PipelineResult:
        agent_config = self.config.get("agent", {})
        lookback_days = int(agent_config.get("lookback_days", 14))
        limit = int(agent_config.get("max_results_per_query", 15))
        max_report_items = int(agent_config.get("max_report_items", 25))
        min_score = float(agent_config.get("min_score", 4.0))
        report_date = date.today()
        since = report_date - timedelta(days=lookback_days)

        collected = self.collect(since=since, report_date=report_date, limit=limit)
        unique = self.dedupe(collected)
        selected = [
            paper
            for paper in sorted(unique.values(), key=lambda item: item.score, reverse=True)
            if paper.score >= min_score
        ][:max_report_items]

        summarizer = build_summarizer(self.config)
        executive_summary = summarizer.summarize(selected, self.config)

        storage = self.config.get("storage", {})
        report_dir = self.root / storage.get("report_dir", "outputs/reports")
        report_path = write_report(report_dir, selected, executive_summary)
        report_id = Path(report_path).stem

        site_data_file = storage.get("site_data_file")
        if site_data_file:
            upsert_site_papers(
                self.root / site_data_file,
                selected,
                report_id=report_id,
                repository_url=storage.get("repository_url", ""),
            )

        state_file = self.root / storage.get("state_file", "outputs/state/papers.json")
        store = PaperStore(state_file)
        if not dry_run:
            existing = store.load()
            store.save(merge_papers(existing, selected))

        return PipelineResult(
            collected_count=len(collected),
            unique_count=len(unique),
            selected_count=len(selected),
            report_path=str(report_path),
        )

    def collect(self, since: date, report_date: date, limit: int) -> list[Paper]:
        sources = build_sources(self.config)
        papers: list[Paper] = []
        for topic in self.config.get("topics", []):
            topic_name = topic.get("name", "unknown")
            topic_weight = float(topic.get("weight", 1.0))
            for query in topic.get("queries", []):
                for source in sources:
                    try:
                        results = source.search(query=query, since=since, limit=limit)
                        for paper in results:
                            if not paper.title:
                                continue
                            if is_future_paper(paper, report_date):
                                continue
                            published = parse_published_date(paper.published)
                            if published is not None and published < since:
                                continue
                            if not has_robotics_relevance(paper):
                                continue
                            papers.append(score_paper(paper, self.config, topic_name, topic_weight))
                    except Exception as exc:
                        papers.append(
                            Paper(
                                title=f"[source error] {source.name}: {query}",
                                abstract=str(exc),
                                source=source.name,
                                topics=[topic_name],
                                tags=["source_error"],
                                score=0.0,
                                reasons=["source request failed"],
                            )
                        )
        venue_watch = self.config.get("ranking", {}).get("venue_watch", [])
        venue_limit = int(self.config.get("agent", {}).get("max_venue_results", limit))
        for venue in venue_watch:
            for source in sources:
                try:
                    results = source.search_venue(venue=venue, since=since, limit=venue_limit)
                    for paper in results:
                        if not paper.title or is_future_paper(paper, report_date):
                            continue
                        published = parse_published_date(paper.published)
                        if published is not None and published < since:
                            continue
                        if not has_robotics_relevance(paper):
                            continue
                        papers.append(
                            score_paper(paper, self.config, "high_impact_venue_watch", 1.2)
                        )
                except Exception as exc:
                    papers.append(
                        Paper(
                            title=f"[source error] {source.name}: venue {venue}",
                            abstract=str(exc),
                            source=source.name,
                            topics=["high_impact_venue_watch"],
                            tags=["source_error"],
                            score=0.0,
                            reasons=["source request failed"],
                        )
                    )
        return papers

    @staticmethod
    def dedupe(papers: list[Paper]) -> dict[str, Paper]:
        unique: dict[str, Paper] = {}
        for paper in papers:
            key = paper.identity
            current = unique.get(key)
            if current is None:
                unique[key] = paper
                continue
            if paper.score > current.score:
                paper.topics = sorted(set(paper.topics + current.topics))
                paper.tags = sorted(set(paper.tags + current.tags))
                paper.reasons = sorted(set(paper.reasons + current.reasons))
                unique[key] = paper
            else:
                current.topics = sorted(set(current.topics + paper.topics))
                current.tags = sorted(set(current.tags + paper.tags))
                current.reasons = sorted(set(current.reasons + paper.reasons))
        return unique
