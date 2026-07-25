from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


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
    score: float = 0.0
    reasons: list[str] = field(default_factory=list)
    raw: dict[str, Any] = field(default_factory=dict)

    @property
    def identity(self) -> str:
        if self.doi:
            return f"doi:{self.doi.lower().strip()}"
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

