"""Fill missing site abstracts from OpenAlex in small DOI batches.

This is intentionally a maintenance tool rather than a requirement for a
weekly collection: Crossref records can be valid even when their metadata does
not deposit an abstract.  The script never invents text; records without a
returned OpenAlex abstract retain the transparent site fallback summary.
"""

from __future__ import annotations

import argparse
import json
import sys
import urllib.parse
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from daily_research_agent.sources import abstract_from_inverted_index, fetch_openalex_json


def normalize_doi(value: str) -> str:
    value = str(value or "").strip().lower()
    for prefix in ("https://doi.org/", "http://doi.org/", "doi:"):
        if value.startswith(prefix):
            return value[len(prefix) :]
    return value


def chunks(values: list[str], size: int) -> list[list[str]]:
    return [values[index : index + size] for index in range(0, len(values), size)]


def backfill(data_path: Path, batch_size: int = 20) -> tuple[int, int]:
    data: dict[str, Any] = json.loads(data_path.read_text(encoding="utf-8"))
    candidates = [
        paper
        for paper in data.get("papers", [])
        if not str(paper.get("abstract") or "").strip() and normalize_doi(paper.get("doi", ""))
    ]
    found: dict[str, str] = {}
    for batch in chunks([normalize_doi(paper["doi"]) for paper in candidates], batch_size):
        params = {
            "filter": "doi:" + "|".join(batch),
            "per-page": str(len(batch)),
            "select": "doi,abstract_inverted_index",
        }
        url = "https://api.openalex.org/works?" + urllib.parse.urlencode(params)
        for work in fetch_openalex_json(url).get("results", []):
            abstract = abstract_from_inverted_index(work.get("abstract_inverted_index"))
            doi = normalize_doi(work.get("doi", ""))
            if doi and abstract:
                found[doi] = abstract

    for paper in candidates:
        abstract = found.get(normalize_doi(paper["doi"]))
        if abstract:
            paper["abstract"] = abstract
            paper["summary"] = abstract[:419].rstrip() + ("..." if len(abstract) > 420 else "")
    data_path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return len(found), len(candidates) - len(found)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--data", default="site/data/papers.json")
    args = parser.parse_args()
    found, unavailable = backfill(Path(args.data))
    print(f"Abstracts backfilled: {found}; source abstracts unavailable: {unavailable}")


if __name__ == "__main__":
    main()
