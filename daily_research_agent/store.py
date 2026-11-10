from __future__ import annotations

import json
from pathlib import Path

from .models import Paper, retain_richer_abstract


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
        if current is None:
            merged[key] = paper
        else:
            preferred, supplement = (paper, current) if paper.score > current.score else (current, paper)
            retain_richer_abstract(preferred, supplement)
            preferred.topics = sorted(set(preferred.topics + supplement.topics))
            preferred.tags = sorted(set(preferred.tags + supplement.tags))
            preferred.reasons = sorted(set(preferred.reasons + supplement.reasons))
            merged[key] = preferred
    return merged

