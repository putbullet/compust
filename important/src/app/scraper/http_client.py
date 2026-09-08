from dataclasses import dataclass
from datetime import datetime, timezone

import httpx


class SourceFetchError(RuntimeError):
    def __init__(self, message: str, status_code: int | None = None) -> None:
        super().__init__(message)
        self.status_code = status_code


@dataclass(frozen=True)
class FetchedSource:
    requested_url: str
    final_url: str
    status_code: int
    content_type: str
    body: str
    fetched_at: datetime


def fetch_source(
    url: str,
    *,
    timeout_seconds: float = 20.0,
    client: httpx.Client | None = None,
) -> FetchedSource:
    owns_client = client is None
    http_client = client or httpx.Client(
        follow_redirects=True,
        timeout=timeout_seconds,
        headers={"User-Agent": "Compust/0.1 (+local career research)"},
    )
    try:
        try:
            response = http_client.get(url)
        except httpx.TimeoutException as exc:
            raise SourceFetchError(f"Request timed out for {url}") from exc
        except httpx.HTTPError as exc:
            raise SourceFetchError(f"Request failed for {url}: {exc}") from exc

        if response.status_code != 200:
            category = {
                403: "source restricted",
                404: "source not found",
                429: "source rate limited",
            }.get(response.status_code, "source returned an error")
            raise SourceFetchError(
                f"{category}: HTTP {response.status_code} for {url}",
                status_code=response.status_code,
            )

        return FetchedSource(
            requested_url=url,
            final_url=str(response.url),
            status_code=response.status_code,
            content_type=response.headers.get("content-type", ""),
            body=response.text,
            fetched_at=datetime.now(timezone.utc),
        )
    finally:
        if owns_client:
            http_client.close()
