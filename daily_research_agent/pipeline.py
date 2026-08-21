from __future__ import annotations

from datetime import date, datetime
from pathlib import Path
from typing import Any

from .llm import build_summarizer
from .models import Paper, PipelineResult
from .reporting import write_report
from .run_state import iter_date_chunks, resolve_search_window, save_successful_run
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
        overlap_days = int(agent_config.get("cursor_overlap_days", 2))
        chunk_days = int(agent_config.get("date_chunk_days", 14))
        limit = int(agent_config.get("max_results_per_query", 15))
        max_report_items = int(agent_config.get("max_report_items", 25))
        min_score = float(agent_config.get("min_score", 4.0))
        report_date = date.today()

        storage = self.config.get("storage", {})
        cursor_path = self.root / storage.get("cursor_file", "outputs/state/collection_cursor.json")
        site_data_file = storage.get("site_data_file")
        site_data_path = self.root / site_data_file if site_data_file else None
        window = resolve_search_window(
            cursor_path=cursor_path,
            site_data_path=site_data_path,
            report_date=report_date,
            bootstrap_days=lookback_days,
            overlap_days=overlap_days,
        )

        collected = self.collect(
            since=window.since,
            report_date=window.until,
            limit=limit,
            chunk_days=chunk_days,
        )
        source_error_count = sum("source_error" in paper.tags for paper in collected)
        unique = self.dedupe(collected)
        selected = [
            paper
            for paper in sorted(unique.values(), key=lambda item: item.score, reverse=True)
            if paper.score >= min_score
        ][:max_report_items]

        summarizer = build_summarizer(self.config)
        executive_summary = summarizer.summarize(selected, self.config)

        report_dir = self.root / storage.get("report_dir", "outputs/reports")
        report_path = write_report(
            report_dir,
            selected,
            executive_summary,
            search_since=window.since,
            search_until=window.until,
        )
        report_id = Path(report_path).stem

        completed_successfully = not dry_run and source_error_count == 0
        site_data_file = storage.get("site_data_file")
        if site_data_file and completed_successfully:
            upsert_site_papers(
                self.root / site_data_file,
                selected,
                report_id=report_id,
                repository_url=storage.get("repository_url", ""),
            )

        state_file = self.root / storage.get("state_file", "outputs/state/papers.json")
        store = PaperStore(state_file)
        if completed_successfully:
            existing = store.load()
            store.save(merge_papers(existing, selected))

        cursor_advanced = completed_successfully
        if cursor_advanced:
            save_successful_run(
                cursor_path,
                completed_at=datetime.now(),
                search_since=window.since,
                search_until=window.until,
                report_id=report_id,
            )

        return PipelineResult(
            collected_count=len(collected),
            unique_count=len(unique),
            selected_count=len(selected),
            report_path=str(report_path),
            search_since=window.since.isoformat(),
            search_until=window.until.isoformat(),
            cursor_advanced=cursor_advanced,
            source_error_count=source_error_count,
        )

    def collect(self, since: date, report_date: date, limit: int, chunk_days: int = 14) -> list[Paper]:
        sources = build_sources(self.config)
        papers: list[Paper] = []
        for chunk_since, chunk_until in iter_date_chunks(since, report_date, chunk_days):
            papers.extend(self._collect_chunk(sources, chunk_since, chunk_until, limit))
        return papers

    def _collect_chunk(
        self,
        sources: list[Any],
        since: date,
        until: date,
        limit: int,
    ) -> list[Paper]:
        papers: list[Paper] = []
        for topic in self.config.get("topics", []):
            topic_name = topic.get("name", "unknown")
            topic_weight = float(topic.get("weight", 1.0))
            for query in topic.get("queries", []):
                for source in sources:
                    try:
                        results = source.search(query=query, since=since, until=until, limit=limit)
                        for paper in results:
                            if self._outside_window(paper, since, until):
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
                    results = source.search_venue(
                        venue=venue, since=since, until=until, limit=venue_limit
                    )
                    for paper in results:
                        if self._outside_window(paper, since, until):
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
    def _outside_window(paper: Paper, since: date, until: date) -> bool:
        if not paper.title or is_future_paper(paper, until):
            return True
        published = parse_published_date(paper.published)
        return published is not None and not since <= published <= until

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
