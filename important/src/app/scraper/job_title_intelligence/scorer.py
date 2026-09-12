import re
from dataclasses import dataclass, field

from bs4 import Tag

from ..universal_parser import CAREER_PATH_INDICATORS, is_plausible_job_link
from .clustering import OpportunityCluster

# Multilingual career terms to look for in headings, IDs, classes, and container text
CAREER_KEYWORDS_REGEX = re.compile(
    r"\b(?:careers?|jobs?|opportunities|vacanc(?:y|ies)|openings?|positions?|join\s+us|work\s+with\s+us|"
    r"recrutements?|emplois?|postes?|offres?|opportunit[eé]s?|carri[eè]re|karriere|stellen)\b",
    re.IGNORECASE,
)

# Unrelated section keywords that indicate non-job content
UNRELATED_SECTION_KEYWORDS_REGEX = re.compile(
    r"\b(?:blog|news|articles?|press|publications?|author|team|leadership|executives?|directors?|"
    r"services?|solutions?|products?|case[-_ ]?studies|testimonials?|clients?|customers?|faq)\b",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class ClusterScore:
    confidence: float  # 0.0 to 1.0
    is_viable: bool
    positive_signals: list[str] = field(default_factory=list)
    negative_signals: list[str] = field(default_factory=list)


class OpportunityScorer:
    """
    Evaluates confidence score for an OpportunityCluster to determine whether
    it represents a legitimate job opportunity container.
    """

    def __init__(self, min_confidence_threshold: float = 0.50) -> None:
        self.min_confidence_threshold = min_confidence_threshold

    def score_cluster(self, cluster: OpportunityCluster) -> ClusterScore:
        score = 0.0
        positives: list[str] = []
        negatives: list[str] = []

        unique_titles = cluster.unique_matched_titles
        title_count = len(unique_titles)
        matches_count = len(cluster.matches)

        # 1. Title count and diversity signals
        if title_count == 0:
            return ClusterScore(0.0, False, [], ["No job titles matched"])
        elif title_count == 1:
            first_match = cluster.matches[0]
            if first_match.specificity <= 0.30:
                score += 0.10
                negatives.append(f"Only 1 generic title detected ('{first_match.matched_title}') with low specificity.")
            else:
                score += 0.30
                positives.append(f"1 specific multi-token title detected ('{first_match.matched_title}').")
        elif title_count == 2:
            score += 0.40
            positives.append(f"2 distinct job titles detected: {list(unique_titles)}.")
        elif 3 <= title_count <= 5:
            score += 0.55
            positives.append(f"{title_count} distinct job titles detected in shared container.")
        else:
            score += 0.70
            positives.append(f"High-density title cluster with {title_count} distinct job titles.")

        # 2. Average Specificity bonus
        avg_spec = cluster.total_specificity / max(matches_count, 1)
        if avg_spec >= 0.70:
            score += 0.15
            positives.append(f"High average title specificity: {avg_spec:.2f}.")
        elif avg_spec <= 0.30 and title_count == 1:
            score -= 0.20
            negatives.append(f"Low average title specificity: {avg_spec:.2f}.")

        # 3. Heading & Container Career Terminology
        container_text = cluster.container.get_text(" ", strip=True)
        container_classes = " ".join(cluster.container.get("class", [])) if hasattr(cluster.container, "get") and cluster.container.get("class") else ""
        container_id = cluster.container.get("id", "") if hasattr(cluster.container, "get") and cluster.container.get("id") else ""
        container_tag = cluster.container.name

        # Check headings within or immediately preceding the container
        headings = cluster.container.find_all(["h1", "h2", "h3", "h4", "h5"])
        headings_text = " ".join(h.get_text(" ", strip=True) for h in headings)

        has_career_heading = bool(CAREER_KEYWORDS_REGEX.search(headings_text))
        has_career_attr = bool(CAREER_KEYWORDS_REGEX.search(f"{container_classes} {container_id}"))

        if has_career_heading or has_career_attr:
            score += 0.25
            positives.append("Container heading or attributes contain career terminology.")

        # 4. Clickable Links and URL Signals
        links_found: list[str] = []
        for card in cluster.candidate_cards:
            link = card if card.name == "a" else card.find("a", href=True)
            if link and link.get("href"):
                href = link["href"]
                text = link.get_text(" ", strip=True)
                if is_plausible_job_link(href, text):
                    links_found.append(href)

        unique_links = set(links_found)
        if len(unique_links) >= 2:
            score += 0.20
            positives.append(f"{len(unique_links)} unique candidate job links detected.")
        elif len(unique_links) == 1:
            score += 0.10
            positives.append("Candidate job link detected.")

        # 5. Repeated Card / Sibling Layout Structure
        if len(cluster.candidate_cards) >= 2:
            card_tags = {c.name for c in cluster.candidate_cards}
            if len(card_tags) == 1:
                score += 0.10
                positives.append(f"Repeated structural cards ({list(card_tags)[0]}) among candidates.")

        # 6. Negative Context Penalties
        # Unrelated section keywords (blog, news, team bios, services, etc.)
        if UNRELATED_SECTION_KEYWORDS_REGEX.search(f"{container_classes} {container_id}"):
            score -= 0.40
            negatives.append("Container marked with unrelated content patterns (e.g. blog, team, services).")

        # If heading explicitly mentions team / leadership rather than careers
        if UNRELATED_SECTION_KEYWORDS_REGEX.search(headings_text) and not has_career_heading:
            score -= 0.35
            negatives.append("Headings indicate team bios or article content rather than career openings.")

        # Single isolated title with no links and no career headings
        if title_count == 1 and not unique_links and not has_career_heading:
            score -= 0.30
            negatives.append("Single isolated title with no direct links and no career headings.")

        final_score = round(max(0.0, min(1.0, score)), 2)
        is_viable = final_score >= self.min_confidence_threshold

        return ClusterScore(
            confidence=final_score,
            is_viable=is_viable,
            positive_signals=positives,
            negative_signals=negatives,
        )
