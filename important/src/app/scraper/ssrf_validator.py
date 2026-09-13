import ipaddress
import socket
from urllib.parse import urlsplit


class SSRFValidationError(ValueError):
    """Raised when a URL fails SSRF safety validation."""
    pass


BLOCKED_HOSTNAMES: set[str] = {
    "localhost",
    "metadata.google.internal",
    "instance-data",
    "169.254.169.254",
}


def is_private_or_reserved_ip(ip_str: str) -> bool:
    """Check if an IP address string belongs to private, loopback, link-local, or reserved ranges."""
    try:
        ip = ipaddress.ip_address(ip_str)
    except ValueError:
        return True

    return bool(
        ip.is_private
        or ip.is_loopback
        or ip.is_link_local
        or ip.is_multicast
        or ip.is_reserved
        or ip.is_unspecified
    )


def validate_safe_url(url: str) -> str:
    """Validate that a URL is safe from SSRF before any network request is attempted.

    Ensures:
    1. Scheme is strictly 'http' or 'https'.
    2. Hostname is present and not an internal/cloud metadata name.
    3. Hostname resolves only to publicly-routable, non-private IP addresses.

    Returns the validated URL, or raises SSRFValidationError.
    """
    if not url or not isinstance(url, str):
        raise SSRFValidationError("URL must be a non-empty string.")

    cleaned = url.strip()
    try:
        parts = urlsplit(cleaned)
    except Exception as exc:
        raise SSRFValidationError(f"Malformed URL: {exc}")

    if parts.scheme.lower() not in ("http", "https"):
        raise SSRFValidationError(f"Invalid URL scheme '{parts.scheme}'. Only http and https are permitted.")

    hostname = parts.hostname
    if not hostname:
        raise SSRFValidationError("URL is missing a valid hostname.")

    norm_host = hostname.lower().strip()
    if norm_host in BLOCKED_HOSTNAMES or norm_host.endswith(".local") or norm_host.endswith(".internal"):
        raise SSRFValidationError(f"Forbidden hostname '{hostname}' rejected for security.")

    # If hostname is directly an IP literal
    try:
        if is_private_or_reserved_ip(norm_host):
            raise SSRFValidationError(f"Destination IP '{norm_host}' belongs to a private/reserved network.")
        return cleaned
    except ValueError:
        pass

    # Resolve hostname via DNS
    try:
        addr_info = socket.getaddrinfo(norm_host, parts.port or (443 if parts.scheme == "https" else 80))
    except socket.gaierror as exc:
        raise SSRFValidationError(f"Could not resolve hostname '{norm_host}': {exc}")

    for entry in addr_info:
        sockaddr = entry[4]
        ip_addr = sockaddr[0]
        if is_private_or_reserved_ip(ip_addr):
            raise SSRFValidationError(f"Hostname '{norm_host}' resolved to restricted IP '{ip_addr}'.")

    return cleaned
