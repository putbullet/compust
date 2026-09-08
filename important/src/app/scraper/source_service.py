from .http_client import fetch_source
from .inspection import SourceInspection, inspect_source


def inspect_url(url: str) -> SourceInspection:
    return inspect_source(fetch_source(url))
