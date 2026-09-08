from dataclasses import dataclass
from urllib.parse import urljoin

from bs4 import BeautifulSoup

from .http_client import FetchedSource


@dataclass(frozen=True)
class SourceInspection:
    requested_url: str
    final_url: str
    status_code: int
    content_type: str
    fetched_at: str
    title: str | None
    links_count: int
    forms_count: int
    pagination_urls: list[str]
    has_next_link: bool
    structured_data_blocks: int
    api_hints: list[str]


def inspect_source(source: FetchedSource) -> SourceInspection:
    soup = BeautifulSoup(source.body, "html.parser")
    pagination_urls: list[str] = []
    for link in soup.select("a[href]"):
        text = link.get_text(" ", strip=True).lower()
        rel = " ".join(link.get("rel", [])).lower()
        href = link.get("href")
        if href and (
            "next" in text
            or "next" in rel
            or "page=" in href.lower()
            or "p=" in href.lower()
        ):
            absolute_url = urljoin(source.final_url, href)
            if absolute_url not in pagination_urls:
                pagination_urls.append(absolute_url)

    api_hints = [
        "json"
        for script in soup.select("script")
        if script.get("type") == "application/ld+json"
    ]
    if soup.select("script[src*='api'], script[src*='graphql']"):
        api_hints.append("script-api-reference")

    title = soup.title.get_text(" ", strip=True) if soup.title else None
    return SourceInspection(
        requested_url=source.requested_url,
        final_url=source.final_url,
        status_code=source.status_code,
        content_type=source.content_type,
        fetched_at=source.fetched_at.isoformat(),
        title=title,
        links_count=len(soup.select("a[href]")),
        forms_count=len(soup.select("form")),
        pagination_urls=pagination_urls,
        has_next_link=any(
            "next" in link.get_text(" ", strip=True).lower()
            or "next" in " ".join(link.get("rel", [])).lower()
            for link in soup.select("a[href]")
        ),
        structured_data_blocks=len(soup.select("script[type='application/ld+json']")),
        api_hints=api_hints,
    )
