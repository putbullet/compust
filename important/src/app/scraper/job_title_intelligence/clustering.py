import re
from dataclasses import dataclass, field
from typing import Any

from bs4 import BeautifulSoup, NavigableString, Tag

from .matcher import JobTitleMatcher, TitleMatch

# Excluded tags that should never be considered candidate job containers
EXCLUDED_CONTAINER_TAGS = {"nav", "header", "footer", "aside", "script", "style", "noscript", "svg", "form", "iframe"}

# Excluded class or ID substring patterns
EXCLUDED_CONTAINER_PATTERNS = re.compile(
    r"\b(?:nav|menu|navbar|footer|header|sidebar|comments?|testimonials?|author[-_]?bio|team[-_]?member|related[-_]?posts?|social[-_]?share|breadcrumbs?|cookie|banner)\b",
    re.IGNORECASE,
)

# Potential job card candidate tags
CARD_TAGS = {"li", "tr", "article", "div", "section"}


@dataclass
class OpportunityCluster:
    container: Tag
    matches: list[TitleMatch] = field(default_factory=list)
    candidate_cards: list[Tag] = field(default_factory=list)

    @property
    def unique_matched_titles(self) -> set[str]:
        return {m.matched_title for m in self.matches}

    @property
    def total_specificity(self) -> float:
        return sum(m.specificity for m in self.matches)


def is_excluded_context(element: Tag) -> bool:
    """Determine if a DOM node resides inside navigation, footer, sidebar, or metadata."""
    current: Any = element
    while current and hasattr(current, "name") and current.name:
        if current.name in EXCLUDED_CONTAINER_TAGS:
            return True
        class_str = " ".join(current.get("class", [])) if hasattr(current, "get") and current.get("class") else ""
        id_str = current.get("id", "") if hasattr(current, "get") and current.get("id") else ""
        combined = f"{class_str} {id_str}".strip()
        if EXCLUDED_CONTAINER_PATTERNS.search(combined):
            return True
        # If element is explicitly hidden
        style = current.get("style", "").lower() if hasattr(current, "get") and current.get("style") else ""
        if "display: none" in style or "visibility: hidden" in style:
            return True
        current = current.parent
    return False


def find_candidate_card(title_node: Tag, container: Tag) -> Tag:
    """
    Find the item/card node wrapping the title node within the container.
    Typically a child `li`, `tr`, `article`, or `div` inside the container.
    """
    curr = title_node
    while curr and curr.parent and curr != container and curr.parent != container:
        curr = curr.parent
    return curr if curr != container else title_node


def find_semantic_container(node: Tag) -> Tag:
    """
    Find the nearest enclosing semantic section container (e.g., <section>, <article>,
    <div class="...jobs...">, <ul>, <table>, or first major block below <body>).
    """
    curr = node.parent
    last_block = node

    while curr and curr.name not in ("body", "html", "[document]"):
        # Check for explicit section / article tags
        if curr.name in ("section", "article"):
            return curr

        # Check for list or table containers with multiple items
        if curr.name in ("ul", "ol", "table", "tbody"):
            return curr

        # Check for career/job related class or ID on container (excluding card/row/item elements)
        if curr.name not in ("li", "tr", "span", "p", "a", "strong", "b", "h1", "h2", "h3", "h4", "h5", "h6"):
            c_str = " ".join(curr.get("class", [])) if hasattr(curr, "get") and curr.get("class") else ""
            i_str = curr.get("id", "") if hasattr(curr, "get") and curr.get("id") else ""
            combined_attr = f"{c_str} {i_str}"
            if not re.search(r"\b(?:card|item|row|entry|single)\b", combined_attr, re.I):
                if re.search(r"career|job|opening|position|vacanc|opportunit|recrut|emploi", combined_attr, re.I):
                    return curr

        last_block = curr
        curr = curr.parent

    # If reached body without hitting an explicit section, return the last major block below body
    return last_block


def find_lowest_common_ancestor(nodes: list[Tag]) -> Tag | None:
    """Find the lowest common ancestor of a list of DOM nodes."""
    if not nodes:
        return None
    if len(nodes) == 1:
        return nodes[0]

    # Get ancestry chain for first node
    ancestor_chains = []
    for node in nodes:
        chain = []
        curr: Any = node
        while curr:
            chain.append(curr)
            curr = curr.parent
        ancestor_chains.append(list(reversed(chain)))

    common = None
    min_len = min(len(c) for c in ancestor_chains)
    for i in range(min_len):
        cand = ancestor_chains[0][i]
        if all(c[i] == cand for c in ancestor_chains):
            common = cand
        else:
            break

    return common


class OpportunityClusterDetector:
    """
    Detects candidate job title matches in visible DOM nodes and groups them
    into coherent opportunity section clusters.
    """

    def __init__(self, matcher: JobTitleMatcher | None = None) -> None:
        self.matcher = matcher or JobTitleMatcher()

    def find_title_matches(self, soup: BeautifulSoup) -> list[TitleMatch]:
        """Scan candidate leaf and near-leaf text elements in the DOM for job titles."""
        matches: list[TitleMatch] = []
        candidate_tags = soup.find_all(
            ["h1", "h2", "h3", "h4", "h5", "h6", "a", "li", "p", "span", "div", "strong", "b", "td"]
        )

        seen_nodes: set[int] = set()

        for el in candidate_tags:
            # Skip if inside excluded navigation, footer, sidebar, or metadata
            if is_excluded_context(el):
                continue

            # Only inspect elements with short, direct text
            direct_text = el.get_text(" ", strip=True)
            if not direct_text or len(direct_text) < 3 or len(direct_text) > 120:
                continue

            # Avoid duplicating parent if child already matched identical text
            text_hash = hash((id(el), direct_text))
            if text_hash in seen_nodes:
                continue

            match = self.matcher.match_text(direct_text, el)
            if match:
                # If this element contains child tags that also match the same text, prefer the leaf-most
                seen_nodes.add(text_hash)
                matches.append(match)

        # De-duplicate matches where parent and child matched the exact same title
        filtered_matches: list[TitleMatch] = []
        for m in matches:
            # If any other match is a descendant of m with the same matched_title, skip m
            has_child_match = any(
                other != m
                and other.matched_title == m.matched_title
                and other.element in m.element.descendants
                for other in matches
            )
            if not has_child_match:
                filtered_matches.append(m)

        return filtered_matches

    def cluster_matches(self, soup: BeautifulSoup, matches: list[TitleMatch]) -> list[OpportunityCluster]:
        """
        Group title matches into discrete clusters based on their shared container.
        Prevents merging disparate sections (e.g. About Us vs Careers).
        """
        if not matches:
            return []

        # Map each match to its nearest semantic container
        container_groups: dict[int, tuple[Tag, list[TitleMatch]]] = {}

        for m in matches:
            container = find_semantic_container(m.element)
            c_id = id(container)
            if c_id not in container_groups:
                container_groups[c_id] = (container, [])
            container_groups[c_id][1].append(m)

        clusters: list[OpportunityCluster] = []

        for container, group_matches in container_groups.values():
            # If multiple matches share a container, find if a tighter LCA exists within it
            if len(group_matches) > 1:
                elements = [m.element for m in group_matches]
                lca = find_lowest_common_ancestor(elements)
                if lca and lca.name not in ("body", "html", "[document]"):
                    container = lca

            # Identify candidate card items inside this container
            cards: list[Tag] = []
            for m in group_matches:
                card = find_candidate_card(m.element, container)
                if card not in cards:
                    cards.append(card)

            clusters.append(
                OpportunityCluster(
                    container=container,
                    matches=group_matches,
                    candidate_cards=cards,
                )
            )

        return clusters
