from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

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


def normalize_doi(value: str) -> str:
    doi = str(value or "").strip()
    for prefix in ("https://doi.org/", "http://doi.org/", "doi:"):
        if doi.lower().startswith(prefix):
            doi = doi[len(prefix) :]
            break
    return doi


def is_consensus_url(value: str) -> bool:
    try:
        host = (urlparse(str(value or "")).hostname or "").lower()
    except ValueError:
        return False
    return host == "consensus.app" or host.endswith(".consensus.app")


def original_paper_url(paper: Paper) -> str:
    doi = normalize_doi(paper.doi)
    if doi:
        return f"https://doi.org/{doi}"

    raw = paper.raw or {}
    candidates = (
        paper.url,
        raw.get("original_url"),
        raw.get("paper_url"),
        raw.get("landing_page_url"),
        raw.get("external_url"),
        raw.get("source_url"),
    )
    return next(
        (
            value.strip()
            for value in candidates
            if isinstance(value, str) and value.strip() and not is_consensus_url(value)
        ),
        "",
    )


def sanitize_site_item(item: dict[str, Any]) -> dict[str, Any]:
    doi = normalize_doi(item.get("doi", ""))
    doi_url = f"https://doi.org/{doi}" if doi else ""
    item["doi"] = doi
    item["doi_url"] = doi_url

    candidates = (doi_url, item.get("url", ""), item.get("original_url", ""))
    item["url"] = next(
        (
            value.strip()
            for value in candidates
            if isinstance(value, str) and value.strip() and not is_consensus_url(value)
        ),
        "",
    )
    return item


def paper_to_site_item(paper: Paper, report_id: str) -> dict[str, Any]:
    doi = normalize_doi(paper.doi)
    doi_url = f"https://doi.org/{doi}" if doi else ""
    return sanitize_site_item({
        "id": paper.identity,
        "report_id": report_id,
        "title": paper.title,
        "url": original_paper_url(paper),
        "doi": doi,
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
    })


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
        (sanitize_site_item(item) for item in existing.values()),
        key=lambda item: (item.get("published") or "", item.get("score") or 0),
        reverse=True,
    )
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
