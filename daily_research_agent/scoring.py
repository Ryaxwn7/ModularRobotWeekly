from __future__ import annotations

import re
from datetime import date
from typing import Any

from .models import Paper


def contains(text: str | None, phrase: str | None) -> bool:
    return (phrase or "").lower() in (text or "").lower()


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
    excluded_patterns = [
        r"\bhumanoid(?: robot| robotics|s)?\b",
        r"\bbipedal humanoid\b",
        r"\banthropomorphic robot",
    ]
    if any(re.search(pattern, text) for pattern in excluded_patterns):
        return False

    target_robotics_patterns = [
        r"\bmulti[- ]robot\b",
        r"\bswarm[- ]robot",
        r"\brobot(?:ic)? swarms?\b",
        r"\bswarm robotics\b",
        r"\bcollective robotic(?:s| systems?)\b",
        r"\bmodular[- ]robot",
        r"\brobot(?:ic)? modules?\b",
        r"\breconfigurable[- ]robot",
        r"\bself[- ]reconfigurable[- ]robot",
        r"\bself[- ]reconfiguring[- ]robot",
        r"\bmorphological reconfiguration\b.{0,40}\brobot",
    ]
    if any(re.search(pattern, text) for pattern in target_robotics_patterns):
        return True

    collective_theory = re.search(
        r"\b(?:self[- ]organi[sz](?:ation|ing)|collective behavior|collective dynamics|"
        r"emergent collective|swarm intelligence|mean[- ]field|phase transition)\b",
        text,
    )
    robotic_agent_context = re.search(
        r"\b(?:robotic agents?|robot agents?|distributed robots?)\b",
        text,
    )
    return bool(collective_theory and robotic_agent_context)


def classify_tags(paper: Paper) -> list[str]:
    text = f"{paper.title} {paper.abstract}".lower()
    tags: list[str] = []
    tag_keywords = {
        "review": ["review", "survey", "meta-analysis", "bibliometric analysis"],
        "algorithm": ["algorithm", "planning", "optimization", "learning", "policy", "estimation"],
        "control": ["control", "controller", "distributed", "consensus", "coordination"],
        "structure": ["mechanism", "morphology", "module", "hardware", "actuator", "lattice"],
        "system": ["system", "prototype", "platform", "architecture", "experiment"],
        "theory": [
            "theorem",
            "proof",
            "model",
            "stability",
            "convergence",
            "analysis",
            "mean-field",
            "graph theory",
            "dynamical system",
            "phase transition",
            "order parameter",
            "statistical mechanics",
        ],
        "swarm": ["swarm", "collective", "multi-robot", "multi robot"],
        "self_organization": ["self-organization", "self-organizing", "self-organised"],
        "emergence": ["emergence", "emergent behavior", "emergent collective"],
        "collective_dynamics": [
            "collective dynamics",
            "mean-field",
            "phase transition",
            "order parameter",
            "statistical mechanics",
        ],
        "reconfiguration": ["reconfigurable", "reconfiguration", "self-reconfigurable", "modular"],
        "perception": ["perception", "vision", "visual", "slam", "localization", "mapping"],
        "embodied_ai": ["embodied", "vision-language-action", "vision language action", "foundation model"],
    }
    for tag, keywords in tag_keywords.items():
        if any(keyword in text for keyword in keywords):
            tags.append(tag)
    return tags


def classify_scope_topics(paper: Paper) -> list[str]:
    text = f"{paper.title} {paper.abstract}".lower()
    topics: list[str] = []
    modular = re.search(
        r"\b(?:modular[- ]robot(?:s|ic)?|modular (?:robotic )?(?:systems?|arms?|boats?|"
        r"cubes?|millibots?|structures?|units?)|robot(?:ic)? modules?|"
        r"self[- ]reconfigur(?:able|ing|ation)[- ]robot(?:s|ic)?|"
        r"reconfigurable[- ]robots?|morphological reconfiguration)\b",
        text,
    )
    swarm = re.search(
        r"\b(?:robot(?:ic)? swarms?|swarm[- ]robots?|swarm robotics|multi[- ]robots?|"
        r"collective robotic(?:s| systems?))\b",
        text,
    )
    collective_theory = re.search(
        r"\b(?:self[- ]organi[sz](?:ation|ing)|emergen(?:ce|t)|collective dynamics|"
        r"mean[- ]field|phase transition|order parameter|statistical mechanics)\b",
        text,
    )
    engineering = re.search(
        r"\b(?:system design|co[- ]design|architecture|hardware|prototype|task allocation|"
        r"coordination|formation|distributed control)\b",
        text,
    )
    bio = re.search(r"\b(?:biomimetic|bio[- ]inspired|bioinspired|bionic|nature[- ]inspired)\b", text)
    algorithm = re.search(r"\b(?:algorithm|planning|control|optimization|learning|decision making)\b", text)
    structure = re.search(r"\b(?:structure|mechanism|morphology|connector|actuator|module)\b", text)

    if modular:
        topics.append("modular_reconfigurable_robotics")
    if swarm:
        topics.append("swarm_intelligence_robotics")
    if swarm and collective_theory:
        topics.append("swarm_self_organization_emergence")
    if (modular or swarm) and engineering:
        topics.append("engineering_system_design")
    if bio and structure and (modular or swarm):
        topics.append("biomimetic_structure_design")
    if bio and algorithm and swarm:
        topics.append("bioinspired_swarm_algorithms")
    return topics


def classify_content_types(paper: Paper) -> list[str]:
    title = (paper.title or "").lower()
    text = f"{paper.title or ''} {paper.abstract or ''}".lower()

    review_pattern = (
        r"\b(?:review|survey|systematic review|scoping review|meta-analysis|"
        r"bibliometric analysis|taxonomy|state of the art)\b"
    )
    abstract_review_pattern = r"\b(?:this|the|a|an|comprehensive|systematic|scoping) review\b"
    if (
        re.search(review_pattern, title)
        or re.search(abstract_review_pattern, (paper.abstract or "").lower())
        or any(tag in paper.tags for tag in ("review", "综述"))
    ):
        return ["review"]

    content_types: list[str] = []
    structure_pattern = (
        r"\b(?:structur(?:e|al) design|mechanism design|mechanical design|morphology|"
        r"actuator|artificial muscle|hardware|fabrication|prototype|docking|connector|"
        r"gripper|module design|soft robotic body|material design)\b"
    )
    algorithm_pattern = (
        r"\b(?:algorithm|control(?:ler)?|planning|planner|optimization|learning|policy|"
        r"coordination|consensus|estimation|perception|localization|mapping|navigation|"
        r"task allocation|formation|mean-field|graph theory|dynamical system|stability|"
        r"convergence|phase transition|order parameter|statistical mechanics)\b"
    )
    if re.search(structure_pattern, text):
        content_types.append("structure_design")
    if re.search(algorithm_pattern, text):
        content_types.append("algorithm_design")
    return content_types


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
    paper.content_types = classify_content_types(paper)
    paper.topics = sorted(set(paper.topics + classify_scope_topics(paper)))
    return paper
