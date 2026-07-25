from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any

from .models import Paper


def paper_summary(paper: Paper, max_chars: int = 420) -> str:
    summary = paper.raw.get("summary") or paper.raw.get("tldr") or paper.abstract
    summary = " ".join(str(summary or "").split())
    if len(summary) <= max_chars:
        return summary
    return summary[: max_chars - 1].rstrip() + "..."


def figure_url(paper: Paper) -> str:
    raw = paper.raw or {}
    for key in ("figure_url", "image_url", "thumbnail_url", "thumbnail", "og_image"):
        value = raw.get(key)
        if isinstance(value, str) and value:
            return value
    return ""


def paper_to_site_item(paper: Paper, report_id: str) -> dict[str, Any]:
    doi_url = f"https://doi.org/{paper.doi}" if paper.doi else ""
    return {
        "id": paper.identity,
        "report_id": report_id,
        "title": paper.title,
        "url": paper.url or doi_url,
        "doi": paper.doi,
        "doi_url": doi_url,
        "summary": paper_summary(paper),
        "abstract": paper.abstract,
        "figure_url": figure_url(paper),
        "figure_alt": f"Main figure for {paper.title}",
        "authors": paper.authors,
        "published": paper.published or (str(paper.year) if paper.year else ""),
        "venue": paper.venue,
        "publisher": paper.publisher,
        "source": paper.source,
        "topics": paper.topics,
        "tags": paper.tags,
        "score": paper.score,
    }


def load_site_data(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {"updated_at": "", "repository_url": "", "papers": []}
    return json.loads(path.read_text(encoding="utf-8"))


def upsert_site_papers(
    path: Path,
    papers: list[Paper],
    report_id: str,
    repository_url: str = "",
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    data = load_site_data(path)
    existing = {item["id"]: item for item in data.get("papers", []) if item.get("id")}
    for paper in papers:
        item = paper_to_site_item(paper, report_id=report_id)
        current = existing.get(item["id"])
        if current:
            current.update({key: value for key, value in item.items() if value not in ("", [], None)})
        else:
            existing[item["id"]] = item

    data["updated_at"] = datetime.now().isoformat(timespec="seconds")
    if repository_url:
        data["repository_url"] = repository_url
    data["papers"] = sorted(
        existing.values(),
        key=lambda item: (item.get("published") or "", item.get("score") or 0),
        reverse=True,
    )
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

