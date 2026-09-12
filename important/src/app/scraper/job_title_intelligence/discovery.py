import re
from typing import Any
from urllib.parse import urljoin, urlparse

from bs4 import BeautifulSoup, Tag

from ...logging import get_logger
from ..orange_parser import JobCandidate
from ..sanitizer import sanitize_html, sanitize_plain_text
from ..url_normalizer import normalize_url
from ..vocabulary import SKILL_SYNONYMS, normalize_employment_type, normalize_remote_type

COMMON_SKILLS = sorted(list(set(SKILL_SYNONYMS.values())))
from .clustering import OpportunityCluster, OpportunityClusterDetector
from .index import get_job_title_index
from .matcher import JobTitleMatcher, TitleMatch
from .scorer import OpportunityScorer

logger = get_logger("scraper.job_title_intelligence.discovery")


def extract_candidate_from_card(
    card: Tag,
    title_match: TitleMatch,
    source_url: str,
    seen_urls: set[str],
) -> JobCandidate | None:
    """Extract a single JobCandidate from a detected card/item element."""
    # 1. Determine title
    raw_title = title_match.raw_text
    title = sanitize_plain_text(raw_title)
    if not title or len(title) < 3:
        return None

    card_text = card.get_text(" ", strip=True)
    slug = re.sub(r"\W+", "-", title.lower()).strip("-")

    # 2. Locate URL
    link = card if card.name == "a" and card.get("href") else card.find("a", href=True)
    href = link.get("href", "").strip() if link else ""

    if href and not href.startswith("javascript:") and not href.startswith("mailto:"):
        if href.startswith("#") or "/contact" in href.lower():
            job_url = f"{normalize_url(source_url)}#{slug}"
        else:
            job_url = normalize_url(urljoin(source_url, href))
    else:
        # User requirement 13: Job title without direct link -> retain candidate with #slug
        job_url = f"{normalize_url(source_url)}#{slug}"

    if job_url in seen_urls:
        return None
    seen_urls.add(job_url)

    # 3. Determine external job ID
    id_match = re.search(r"/(?:job|jobs|position|positions|vacancy|vacancies|offre|offres|postes?)/([a-zA-Z0-9_\-]+)", job_url)
    if id_match:
        ext_id = id_match.group(1)
    else:
        ext_id = slug or re.sub(r"\W+", "_", urlparse(job_url).path.strip("/")) or title[:30]

    # 4. Location extraction
    location = None
    loc_el = card.select_one("[class*='location'], [class*='city'], [class*='place'], [class*='lieu']")
    if loc_el and loc_el != link:
        loc_text = sanitize_plain_text(loc_el.get_text(" ", strip=True))
        if loc_text and loc_text != title:
            location = loc_text
    elif re.search(r"\b(remote|t[eé]l[eé]travail)\b", card_text, re.I):
        location = "Remote"

    # 5. Department extraction
    dept = None
    dept_el = card.select_one("[class*='dept'], [class*='department'], [class*='service'], [class*='team']")
    if dept_el:
        dept = sanitize_plain_text(dept_el.get_text(" ", strip=True))

    # 6. Work types & Skills
    from ..vocabulary import EMPLOYMENT_TYPE_PATTERNS, REMOTE_TYPE_PATTERNS

    emp_type = None
    for pattern, canonical in EMPLOYMENT_TYPE_PATTERNS:
        if pattern.search(card_text):
            emp_type = canonical
            break

    rem_type = None
    for pattern, canonical in REMOTE_TYPE_PATTERNS:
        if pattern.search(card_text):
            rem_type = canonical
            break

    detected_skills: list[str] = []
    card_lower = card_text.lower()
    for skill in COMMON_SKILLS:
        if re.search(rf"\b{re.escape(skill.lower())}\b", card_lower):
            detected_skills.append(skill)

    # 7. Description
    desc_html = card.decode_contents() if hasattr(card, "decode_contents") else f"<p>{card_text}</p>"

    return JobCandidate(
        title=title,
        job_url=job_url,
        external_job_id=ext_id,
        location=location,
        description=sanitize_html(desc_html),
        employment_type=emp_type,
        remote_type=rem_type,
        department=dept,
        skills=detected_skills,
        discovery_source="job_title_intelligence",
    )


def discover_jobs_via_title_intelligence(
    soup: BeautifulSoup,
    source_url: str,
    min_confidence: float = 0.50,
) -> tuple[list[JobCandidate], dict[str, Any]]:
    """
    Main entrypoint for Job Title Intelligence Discovery.
    Executes:
    1. Scan visible DOM nodes for recognized job titles.
    2. Group matched nodes into discrete container clusters.
    3. Score each cluster based on titles count, specificity, links, and repeated layout.
    4. Extract candidates from the highest scoring opportunity section.
    """
    index = get_job_title_index()
    index_stats = index.stats()

    matcher = JobTitleMatcher(index=index)
    detector = OpportunityClusterDetector(matcher=matcher)
    scorer = OpportunityScorer(min_confidence_threshold=min_confidence)

    title_matches = detector.find_title_matches(soup)
    clusters = detector.cluster_matches(soup, title_matches)

    diagnostics: dict[str, Any] = {
        "dataset_stats": index_stats,
        "total_title_matches": len(title_matches),
        "clusters_count": len(clusters),
        "best_cluster_confidence": 0.0,
        "best_cluster_tag": None,
        "best_cluster_titles": [],
        "candidates_count": 0,
    }

    if not clusters:
        return [], diagnostics

    # Score all candidate clusters
    scored_clusters = [(cluster, scorer.score_cluster(cluster)) for cluster in clusters]
    # Filter viable clusters and sort by confidence descending
    viable_clusters = [sc for sc in scored_clusters if sc[1].is_viable]
    viable_clusters.sort(key=lambda sc: sc[1].confidence, reverse=True)

    if not viable_clusters:
        best_unviable = max(scored_clusters, key=lambda sc: sc[1].confidence)
        diagnostics["best_cluster_confidence"] = best_unviable[1].confidence
        diagnostics["best_cluster_tag"] = best_unviable[0].container.name
        diagnostics["best_cluster_titles"] = list(best_unviable[0].unique_matched_titles)
        return [], diagnostics

    winning_cluster, winning_score = viable_clusters[0]

    diagnostics["best_cluster_confidence"] = winning_score.confidence
    diagnostics["best_cluster_tag"] = winning_cluster.container.name
    diagnostics["best_cluster_titles"] = list(winning_cluster.unique_matched_titles)
    diagnostics["winning_signals"] = winning_score.positive_signals

    candidates: list[JobCandidate] = []
    seen_urls: set[str] = set()

    # If the winning cluster has distinct candidate cards, extract each
    for m in winning_cluster.matches:
        card = None
        for c in winning_cluster.candidate_cards:
            if m.element == c or m.element in c.descendants:
                card = c
                break
        if not card:
            card = m.element

        candidate = extract_candidate_from_card(card, m, source_url, seen_urls)
        if candidate:
            candidates.append(candidate)

    diagnostics["candidates_count"] = len(candidates)
    logger.info(
        f"Job Title Intelligence discovered {len(candidates)} candidates with confidence {winning_score.confidence}.",
        extra={
            "event": "TITLE_INTELLIGENCE_SUCCESS",
            "candidates_count": len(candidates),
            "confidence": winning_score.confidence,
            "matched_titles": diagnostics["best_cluster_titles"],
        },
    )

    return candidates, diagnostics
