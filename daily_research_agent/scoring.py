from __future__ import annotations

import re
from datetime import date
from typing import Any

from .models import Paper


def contains(text: str, phrase: str) -> bool:
    return phrase.lower() in text.lower()


def normalized_venue(value: str) -> str:
    return " ".join(re.findall(r"[a-z0-9]+", (value or "").lower()))


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
    direct_robotics_patterns = [
        r"\brobot\b",
        r"\brobots\b",
        r"\brobotic\b",
        r"\brobotics\b",
        r"\bmulti[- ]robot\b",
        r"\bswarm[- ]robot",
        r"\bmodular[- ]robot",
        r"\breconfigurable[- ]robot",
        r"\bself[- ]reconfigurable[- ]robot",
        r"\brobot learning\b",
        r"\brobot foundation model",
        r"\bvision[- ]language[- ]action\b",
        r"\bautonomous mobile robot",
        r"\bsimultaneous localization and mapping\b",
        r"\bsoft robot",
        r"\bmedical robot",
        r"\bmicro[- ]robot",
        r"\bnano[- ]robot",
    ]
    if any(re.search(pattern, text) for pattern in direct_robotics_patterns):
        return True

    bio_signal = re.search(
        r"\b(?:biomimetic|bio[- ]inspired|bioinspired|bionic|nature[- ]inspired)\b",
        text,
    )
    bio_robotics_context = re.search(
        r"\b(?:actuator|artificial muscle|gripper|manipulator|soft machine|"
        r"flapping wing mechanism|morphing mechanism|locomotion mechanism)\b",
        text,
    )
    if bio_signal and bio_robotics_context:
        return True

    swarm_signal = re.search(
        r"\b(?:swarm intelligence|ant colony|particle swarm|bee colony)\b",
        text,
    )
    multi_agent_context = re.search(
        r"\b(?:multi[- ]agent|path planning|motion planning|formation control|"
        r"cooperative navigation|collective transport|task allocation)\b",
        text,
    )
    if swarm_signal and multi_agent_context:
        return True

    embodied_signal = re.search(r"\b(?:embodied intelligence|embodied ai)\b", text)
    embodied_context = re.search(
        r"\b(?:agent|action|policy|control|learning|manipulation|navigation)\b",
        text,
    )
    return bool(embodied_signal and embodied_context)


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
        "perception": ["perception", "vision", "visual", "slam", "localization", "mapping"],
        "embodied_ai": ["embodied", "vision-language-action", "vision language action", "foundation model"],
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

    venue_bonus_applied = False
    paper_venue = normalized_venue(paper.venue)
    for tier in ranking.get("venue_tiers", []):
        for venue in tier.get("venues", []):
            if paper_venue and paper_venue == normalized_venue(venue):
                bonus = float(tier.get("bonus", 0))
                score += bonus
                reasons.append(f"{tier.get('name', 'priority')} venue: {venue}")
                venue_bonus_applied = True
                break
        if venue_bonus_applied:
            break

    if not venue_bonus_applied:
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
