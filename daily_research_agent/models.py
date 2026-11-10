from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


def normalized_doi(value: str) -> str:
    value = str(value or "").strip().lower()
    for prefix in ("https://doi.org/", "http://doi.org/", "doi:"):
        if value.startswith(prefix):
            return value[len(prefix):].strip()
    return value


def same_paper(left: "Paper", right: "Paper") -> bool:
    left_doi, right_doi = normalized_doi(left.doi), normalized_doi(right.doi)
    if left_doi and right_doi:
        return left_doi == right_doi
    # Without two matching persistent identifiers, require exact normalized
    # titles and corroborating author/year metadata; never use fuzzy similarity.
    title = " ".join(left.title.casefold().split())
    if not title or title != " ".join(right.title.casefold().split()):
        return False
    left_year = left.year or left.published[:4]
    right_year = right.year or right.published[:4]
    authors_left = {" ".join(name.casefold().split()) for name in left.authors}
    authors_right = {" ".join(name.casefold().split()) for name in right.authors}
    return bool(left_year and str(left_year) == str(right_year) and authors_left & authors_right)


def retain_richer_abstract(preferred: "Paper", supplement: "Paper") -> None:
    if same_paper(preferred, supplement) and len(supplement.abstract.strip()) > len(preferred.abstract.strip()):
        preferred.abstract = supplement.abstract
        preferred.raw["abstract_source"] = supplement.raw.get("abstract_source") or supplement.source
        preferred.raw["abstract_source_url"] = supplement.raw.get("abstract_source_url") or supplement.url


@dataclass
class Paper:
    title: str
    abstract: str = ""
    authors: list[str] = field(default_factory=list)
    year: int | None = None
    published: str = ""
    venue: str = ""
    publisher: str = ""
    doi: str = ""
    url: str = ""
    source: str = ""
    topics: list[str] = field(default_factory=list)
    tags: list[str] = field(default_factory=list)
    content_types: list[str] = field(default_factory=list)
    score: float = 0.0
    reasons: list[str] = field(default_factory=list)
    raw: dict[str, Any] = field(default_factory=dict)

    @property
    def identity(self) -> str:
        if self.doi:
            return f"doi:{normalized_doi(self.doi)}"
        normalized = " ".join(self.title.lower().split())
        return f"title:{normalized}"

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Paper":
        fields = cls.__dataclass_fields__.keys()
        return cls(**{key: value for key, value in data.items() if key in fields})


@dataclass
class PipelineResult:
    collected_count: int
    unique_count: int
    selected_count: int
    report_path: str
    search_since: str
    search_until: str
    cursor_advanced: bool
    source_error_count: int
    blocking_source_error_count: int
