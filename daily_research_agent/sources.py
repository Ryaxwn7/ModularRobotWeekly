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

    def search_venue(self, venue: str, since: date, limit: int) -> Iterable[Paper]:
        return []


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

    def _request(self, params: dict[str, str]) -> list[dict[str, Any]]:
        if self.mailto:
            params["mailto"] = self.mailto
        url = "https://api.crossref.org/works?" + urllib.parse.urlencode(params)
        data = fetch_json(url)
        return data.get("message", {}).get("items", [])

    @staticmethod
    def _to_paper(item: dict[str, Any]) -> Paper | None:
        title = strip_markup(first(item.get("title")))
        if not title:
            return None
        published_parts = (
            item.get("published-online", {}).get("date-parts")
            or item.get("published", {}).get("date-parts")
            or item.get("issued", {}).get("date-parts")
            or item.get("published-print", {}).get("date-parts")
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
        return Paper(
            title=title,
            abstract=strip_markup(item.get("abstract", "")),
            authors=[a for a in authors if a],
            year=year,
            published=published,
            venue=first(item.get("container-title")),
            publisher=item.get("publisher", ""),
            doi=item.get("DOI", ""),
            url=item.get("URL", ""),
            source="crossref",
            raw={"type": item.get("type", "")},
        )

    @staticmethod
    def _dedupe_items(items: Iterable[dict[str, Any]]) -> list[Paper]:
        papers: dict[str, Paper] = {}
        for item in items:
            paper = CrossrefSource._to_paper(item)
            if paper is None:
                continue
            current = papers.get(paper.identity)
            if current is None or len(paper.abstract) > len(current.abstract):
                papers[paper.identity] = paper
        return list(papers.values())

    def search(self, query: str, since: date, limit: int) -> Iterable[Paper]:
        common = {
            "filter": (
                f"from-pub-date:{since.isoformat()},"
                f"until-pub-date:{date.today().isoformat()},type:journal-article"
            ),
            "rows": str(limit),
        }
        result_sets = [
            self._request({**common, "query.title": query}),
            self._request(
                {
                    **common,
                    "query.bibliographic": query,
                    "sort": "published",
                    "order": "desc",
                }
            ),
        ]
        time.sleep(0.2)
        return self._dedupe_items(item for result in result_sets for item in result)

    def search_venue(self, venue: str, since: date, limit: int) -> Iterable[Paper]:
        params = {
            "filter": (
                f"from-pub-date:{since.isoformat()},"
                f"until-pub-date:{date.today().isoformat()},"
                f"type:journal-article,container-title:{venue}"
            ),
            "sort": "published",
            "order": "desc",
            "rows": str(limit),
        }
        papers = self._dedupe_items(self._request(params))
        time.sleep(0.2)
        return papers


def abstract_from_inverted_index(index: Any) -> str:
    if not isinstance(index, dict) or not index:
        return ""
    positions = [position for values in index.values() for position in values if isinstance(position, int)]
    if not positions:
        return ""
    words = [""] * (max(positions) + 1)
    for word, values in index.items():
        for position in values:
            if isinstance(position, int) and 0 <= position < len(words):
                words[position] = word
    return " ".join(word for word in words if word)


class OpenAlexSource(SourceClient):
    name = "openalex"

    def __init__(self, mailto: str = "") -> None:
        self.mailto = mailto

    def search(self, query: str, since: date, limit: int) -> Iterable[Paper]:
        params = {
            "search": query,
            "filter": f"from_publication_date:{since.isoformat()},type:article",
            "sort": "relevance_score:desc",
            "per-page": str(min(limit, 100)),
            "select": (
                "id,doi,title,publication_year,publication_date,primary_location,"
                "authorships,abstract_inverted_index,open_access,topics,keywords,"
                "cited_by_count,type"
            ),
        }
        if self.mailto:
            params["mailto"] = self.mailto
        url = "https://api.openalex.org/works?" + urllib.parse.urlencode(params)
        data = fetch_json(url)
        for item in data.get("results", []):
            title = strip_markup(item.get("title", ""))
            if not title:
                continue
            location = item.get("primary_location") or {}
            source = location.get("source") or {}
            doi = str(item.get("doi") or "")
            if doi.lower().startswith("https://doi.org/"):
                doi = doi[len("https://doi.org/") :]
            authors = [
                (authorship.get("author") or {}).get("display_name", "")
                for authorship in item.get("authorships", [])
            ]
            topics = [topic.get("display_name", "") for topic in item.get("topics", [])]
            keywords = [keyword.get("display_name", "") for keyword in item.get("keywords", [])]
            yield Paper(
                title=title,
                abstract=abstract_from_inverted_index(item.get("abstract_inverted_index")),
                authors=[author for author in authors if author],
                year=item.get("publication_year"),
                published=item.get("publication_date") or "",
                venue=source.get("display_name", ""),
                publisher=source.get("host_organization_name", ""),
                doi=doi,
                url=doi and f"https://doi.org/{doi}" or location.get("landing_page_url", ""),
                source=self.name,
                raw={
                    "openalex_id": item.get("id", ""),
                    "cited_by_count": item.get("cited_by_count", 0),
                    "openalex_topics": topics,
                    "openalex_keywords": keywords,
                    "oa_url": (item.get("open_access") or {}).get("oa_url", ""),
                },
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
    if source_config.get("openalex", {}).get("enabled", False):
        sources.append(OpenAlexSource(mailto=source_config.get("openalex", {}).get("mailto", "")))
    if source_config.get("ieee", {}).get("enabled", False):
        sources.append(IEEESource())
    if source_config.get("elsevier", {}).get("enabled", False):
        sources.append(ElsevierSource())
    return sources
