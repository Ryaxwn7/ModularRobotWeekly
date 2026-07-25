from __future__ import annotations

import re
from datetime import date
from typing import Any

from .models import Paper


def contains(text: str, phrase: str) -> bool:
    return phrase.lower() in text.lower()


def tokenize(text: str) -> set[str]:
    return set(re.findall(r"[a-zA-Z][a-zA-Z0-9-]+", text.lower()))


def parse_published_date(value: str) -> date | None:
    value = (value or "").strip()
    if not value:
        return None
    match = re.match(r"^(\d{4})(?:-(\d{1,2}))?(?:-(\d{1,2}))?", value)
    if not match:
        return None
    year = int(match.group(1))
    month = int(match.group(2) or "1")
    day = int(match.group(3) or "1")
    try:
        return date(year, month, day)
    except ValueError:
        return None


def is_future_paper(paper: Paper, report_date: date) -> bool:
    published = parse_published_date(paper.published)
    if published is not None:
        return published > report_date
    if paper.year is not None:
        return paper.year > report_date.year
    return False


def has_robotics_relevance(paper: Paper) -> bool:
    text = f"{paper.title} {paper.abstract}".lower()
    robotics_patterns = [
        r"\brobot\b",
        r"\brobots\b",
        r"\brobotic\b",
        r"\brobotics\b",
        r"\bmulti[- ]robot\b",
        r"\bswarm[- ]robot",
        r"\bmodular[- ]robot",
        r"\breconfigurable[- ]robot",
        r"\bself[- ]reconfigurable[- ]robot",
    ]
    return any(re.search(pattern, text) for pattern in robotics_patterns)


def classify_tags(paper: Paper) -> list[str]:
    text = f"{paper.title} {paper.abstract}".lower()
    tags: list[str] = []
    tag_keywords = {
        "algorithm": ["algorithm", "planning", "optimization", "learning", "policy", "estimation"],
        "control": ["control", "controller", "distributed", "consensus", "coordination"],
        "structure": ["mechanism", "morphology", "module", "hardware", "actuator", "lattice"],
        "system": ["system", "prototype", "platform", "architecture", "experiment"],
        "theory": ["theorem", "proof", "model", "stability", "convergence", "analysis"],
        "swarm": ["swarm", "collective", "multi-robot", "multi robot"],
        "reconfiguration": ["reconfigurable", "reconfiguration", "self-reconfigurable", "modular"],
    }
    for tag, keywords in tag_keywords.items():
        if any(keyword in text for keyword in keywords):
            tags.append(tag)
    return tags


def score_paper(paper: Paper, config: dict[str, Any], topic_name: str, topic_weight: float) -> Paper:
    ranking = config.get("ranking", {})
    preferred_venues = ranking.get("preferred_venues", [])
    publisher_keywords = ranking.get("publisher_keywords", [])
    method_keywords = ranking.get("method_keywords", [])

    text = f"{paper.title} {paper.abstract} {paper.venue} {paper.publisher}"
    tokens = tokenize(text)
    score = 0.0
    reasons: list[str] = []

    score += 2.0 * topic_weight
    reasons.append(f"matches topic {topic_name}")

    for venue in preferred_venues:
        if contains(paper.venue, venue):
            score += 3.0
            reasons.append(f"preferred venue: {venue}")
            break

    for keyword in publisher_keywords:
        if contains(paper.publisher, keyword) or contains(paper.venue, keyword):
            score += 1.5
            reasons.append(f"preferred publisher signal: {keyword}")
            break

    generic_terms = {"system", "architecture", "optimization", "control", "modular", "swarm"}
    method_hits = [keyword for keyword in method_keywords if keyword.lower() in tokens or contains(text, keyword)]
    if method_hits:
        specific_hits = [keyword for keyword in method_hits if keyword.lower() not in generic_terms]
        generic_hits = [keyword for keyword in method_hits if keyword.lower() in generic_terms]
        score += min(1.5, 0.3 * len(specific_hits) + 0.08 * len(generic_hits))
        reasons.append("method/system keywords: " + ", ".join(method_hits[:5]))

    if paper.doi:
        score += 0.5
        reasons.append("has DOI")

    if paper.abstract:
        score += 0.5
        reasons.append("has abstract")

    if paper.source in {"ieee", "elsevier"}:
        score += 1.0
        reasons.append(f"publisher API source: {paper.source}")

    paper.score = round(score, 2)
    paper.reasons = reasons
    paper.tags = classify_tags(paper)
    if topic_name not in paper.topics:
        paper.topics.append(topic_name)
    return paper
