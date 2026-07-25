from __future__ import annotations

import json
from pathlib import Path

from .models import Paper


class PaperStore:
    def __init__(self, path: Path) -> None:
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def load(self) -> dict[str, Paper]:
        if not self.path.exists():
            return {}
        data = json.loads(self.path.read_text(encoding="utf-8"))
        papers = [Paper.from_dict(item) for item in data.get("papers", [])]
        return {paper.identity: paper for paper in papers}

    def save(self, papers: dict[str, Paper]) -> None:
        payload = {
            "papers": [
                paper.to_dict()
                for paper in sorted(papers.values(), key=lambda item: (item.published, item.score), reverse=True)
            ]
        }
        self.path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def merge_papers(existing: dict[str, Paper], incoming: list[Paper]) -> dict[str, Paper]:
    merged = dict(existing)
    for paper in incoming:
        key = paper.identity
        current = merged.get(key)
        if current is None or paper.score > current.score:
            merged[key] = paper
        else:
            current.topics = sorted(set(current.topics + paper.topics))
            current.tags = sorted(set(current.tags + paper.tags))
            current.reasons = sorted(set(current.reasons + paper.reasons))
    return merged

