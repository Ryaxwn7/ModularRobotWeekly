from __future__ import annotations

import os
import re
import time
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from datetime import date
from typing import Any, Iterable

from .models import Paper


USER_AGENT = "DailyResearchAgent/0.1 (mailto:research-agent@example.local)"


def fetch_json(url: str, headers: dict[str, str] | None = None, timeout: int = 30) -> dict[str, Any]:
    request = urllib.request.Request(url, headers=headers or {"User-Agent": USER_AGENT})
    with urllib.request.urlopen(request, timeout=timeout) as response:
        import json

        return json.loads(response.read().decode("utf-8"))


def fetch_text(url: str, headers: dict[str, str] | None = None, timeout: int = 30) -> str:
    request = urllib.request.Request(url, headers=headers or {"User-Agent": USER_AGENT})
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return response.read().decode("utf-8")


def strip_markup(value: str) -> str:
    value = re.sub(r"<[^>]+>", " ", value or "")
    return " ".join(value.split())


def first(value: Any, default: str = "") -> str:
    if isinstance(value, list) and value:
        return str(value[0])
    if value is None:
        return default
    return str(value)


class SourceClient:
    name = "source"

    def search(self, query: str, since: date, limit: int) -> Iterable[Paper]:
        raise NotImplementedError


class ArxivSource(SourceClient):
    name = "arxiv"

    def search(self, query: str, since: date, limit: int) -> Iterable[Paper]:
        encoded = urllib.parse.quote(f'all:"{query}"')
        url = (
            "https://export.arxiv.org/api/query?"
            f"search_query={encoded}&sortBy=submittedDate&sortOrder=descending&max_results={limit}"
        )
        root = ET.fromstring(fetch_text(url))
        ns = {"atom": "http://www.w3.org/2005/Atom"}
        for entry in root.findall("atom:entry", ns):
            published = entry.findtext("atom:published", default="", namespaces=ns)
            if published[:10] and published[:10] < since.isoformat():
                continue
            title = strip_markup(entry.findtext("atom:title", default="", namespaces=ns))
            abstract = strip_markup(entry.findtext("atom:summary", default="", namespaces=ns))
            authors = [
                strip_markup(author.findtext("atom:name", default="", namespaces=ns))
                for author in entry.findall("atom:author", ns)
            ]
            url_value = entry.findtext("atom:id", default="", namespaces=ns)
            yield Paper(
                title=title,
                abstract=abstract,
                authors=[a for a in authors if a],
                published=published[:10],
                year=int(published[:4]) if published[:4].isdigit() else None,
                venue="arXiv",
                url=url_value,
                source=self.name,
            )
        time.sleep(0.2)


class CrossrefSource(SourceClient):
    name = "crossref"

    def __init__(self, mailto: str = "") -> None:
        self.mailto = mailto

    def search(self, query: str, since: date, limit: int) -> Iterable[Paper]:
        params = {
            "query.bibliographic": query,
            "filter": f"from-pub-date:{since.isoformat()},type:journal-article",
            "sort": "published",
            "order": "desc",
            "rows": str(limit),
        }
        if self.mailto:
            params["mailto"] = self.mailto
        url = "https://api.crossref.org/works?" + urllib.parse.urlencode(params)
        data = fetch_json(url)
        for item in data.get("message", {}).get("items", []):
            title = strip_markup(first(item.get("title")))
            if not title:
                continue
            published_parts = (
                item.get("published-print", {}).get("date-parts")
                or item.get("published-online", {}).get("date-parts")
                or item.get("created", {}).get("date-parts")
                or []
            )
            published = ""
            year = None
            if published_parts and published_parts[0]:
                parts = published_parts[0]
                year = int(parts[0]) if parts[0] else None
                month = int(parts[1]) if len(parts) > 1 else 1
                day = int(parts[2]) if len(parts) > 2 else 1
                published = f"{year:04d}-{month:02d}-{day:02d}" if year else ""
            authors = [
                " ".join([a.get("given", ""), a.get("family", "")]).strip()
                for a in item.get("author", [])
            ]
            yield Paper(
                title=title,
                abstract=strip_markup(item.get("abstract", "")),
                authors=[a for a in authors if a],
                year=year,
                published=published,
                venue=first(item.get("container-title")),
                publisher=item.get("publisher", ""),
                doi=item.get("DOI", ""),
                url=item.get("URL", ""),
                source=self.name,
                raw={"type": item.get("type", "")},
            )
        time.sleep(0.2)


class SemanticScholarSource(SourceClient):
    name = "semantic_scholar"

    def search(self, query: str, since: date, limit: int) -> Iterable[Paper]:
        params = {
            "query": query,
            "limit": str(min(limit, 100)),
            "fields": "title,abstract,year,publicationDate,authors,venue,url,externalIds,publicationTypes",
            "year": f"{since.year}-",
        }
        headers = {"User-Agent": USER_AGENT}
        api_key = os.getenv("SEMANTIC_SCHOLAR_API_KEY")
        if api_key:
            headers["x-api-key"] = api_key
        url = "https://api.semanticscholar.org/graph/v1/paper/search?" + urllib.parse.urlencode(params)
        data = fetch_json(url, headers=headers)
        for item in data.get("data", []):
            published = item.get("publicationDate") or ""
            if published and published[:10] < since.isoformat():
                continue
            yield Paper(
                title=strip_markup(item.get("title", "")),
                abstract=strip_markup(item.get("abstract", "") or ""),
                authors=[a.get("name", "") for a in item.get("authors", []) if a.get("name")],
                year=item.get("year"),
                published=published,
                venue=item.get("venue", ""),
                doi=(item.get("externalIds") or {}).get("DOI", ""),
                url=item.get("url", ""),
                source=self.name,
                raw={"publicationTypes": item.get("publicationTypes", [])},
            )
        time.sleep(0.2)


class IEEESource(SourceClient):
    name = "ieee"

    def search(self, query: str, since: date, limit: int) -> Iterable[Paper]:
        api_key = os.getenv("IEEE_API_KEY")
        if not api_key:
            return []
        params = {
            "apikey": api_key,
            "format": "json",
            "max_records": str(limit),
            "start_record": "1",
            "sort_field": "publication_year",
            "sort_order": "desc",
            "querytext": query,
        }
        url = "https://ieeexploreapi.ieee.org/api/v1/search/articles?" + urllib.parse.urlencode(params)
        data = fetch_json(url)
        papers = []
        for item in data.get("articles", []):
            year = item.get("publication_year")
            if year and int(year) < since.year:
                continue
            papers.append(
                Paper(
                    title=strip_markup(item.get("title", "")),
                    abstract=strip_markup(item.get("abstract", "")),
                    authors=[a.get("full_name", "") for a in item.get("authors", {}).get("authors", [])],
                    year=int(year) if str(year).isdigit() else None,
                    published=item.get("publication_date", ""),
                    venue=item.get("publication_title", ""),
                    publisher="IEEE",
                    doi=item.get("doi", ""),
                    url=item.get("html_url", ""),
                    source=self.name,
                )
            )
        time.sleep(0.2)
        return papers


class ElsevierSource(SourceClient):
    name = "elsevier"

    def search(self, query: str, since: date, limit: int) -> Iterable[Paper]:
        api_key = os.getenv("ELSEVIER_API_KEY")
        if not api_key:
            return []
        params = {
            "query": f'TITLE-ABS-KEY("{query}")',
            "date": str(since.year),
            "count": str(limit),
            "sort": "-coverDate",
        }
        headers = {"X-ELS-APIKey": api_key, "Accept": "application/json", "User-Agent": USER_AGENT}
        url = "https://api.elsevier.com/content/search/scopus?" + urllib.parse.urlencode(params)
        data = fetch_json(url, headers=headers)
        papers = []
        for item in data.get("search-results", {}).get("entry", []):
            papers.append(
                Paper(
                    title=strip_markup(item.get("dc:title", "")),
                    abstract="",
                    authors=[item.get("dc:creator", "")] if item.get("dc:creator") else [],
                    published=item.get("prism:coverDate", ""),
                    year=int(item.get("prism:coverDate", "0000")[:4])
                    if item.get("prism:coverDate", "")[:4].isdigit()
                    else None,
                    venue=item.get("prism:publicationName", ""),
                    publisher="Elsevier",
                    doi=item.get("prism:doi", ""),
                    url=item.get("prism:url", ""),
                    source=self.name,
                )
            )
        time.sleep(0.2)
        return papers


def build_sources(config: dict[str, Any]) -> list[SourceClient]:
    source_config = config.get("sources", {})
    sources: list[SourceClient] = []
    if source_config.get("arxiv", {}).get("enabled", False):
        sources.append(ArxivSource())
    if source_config.get("crossref", {}).get("enabled", False):
        sources.append(CrossrefSource(mailto=source_config.get("crossref", {}).get("mailto", "")))
    if source_config.get("semantic_scholar", {}).get("enabled", False):
        sources.append(SemanticScholarSource())
    if source_config.get("ieee", {}).get("enabled", False):
        sources.append(IEEESource())
    if source_config.get("elsevier", {}).get("enabled", False):
        sources.append(ElsevierSource())
    return sources

