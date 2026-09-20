"""Canonical URL normalization and deduplication for PersonProbe.

Handles:
- Domain aliases (e.g. icar.gov.in <-> icar.org.in, timesofindia.com <-> timesofindia.indiatimes.com)
- Mobile subdomains (m.* stripped or mapped)
- DOI canonicalization (https://doi.org/10.xxxx/...)
- Tracking / analytics query parameter stripping (utm_*, _tp, fbclid, gclid, ref, etc.)
- AMP path & parameter stripping (/amp/, /amp_articleshow/, ?amp)
- Scheme (http/https) and trailing slash normalization
"""
from __future__ import annotations

import re
import urllib.parse

DOMAIN_ALIAS_MAP: dict[str, str] = {
    "icar.gov.in": "icar.org.in",
    "timesofindia.com": "timesofindia.indiatimes.com",
    "m.timesofindia.com": "timesofindia.indiatimes.com",
    "m.timesofindia.indiatimes.com": "timesofindia.indiatimes.com",
    "m.jagran.com": "jagran.com",
    "m.bhaskar.com": "bhaskar.com",
    "m.punjabkesari.in": "punjabkesari.in",
    "m.haryana.punjabkesari.in": "punjabkesari.in",
    "m.amarujala.com": "amarujala.com",
    "m.ndtv.com": "ndtv.com",
    "m.hindustantimes.com": "hindustantimes.com",
    "m.thehindu.com": "thehindu.com"
}

TRACKING_PARAM_PREFIXES: tuple[str, ...] = (
    "utm_", "_tp", "fbclid", "gclid", "ref", "source", "amp", "srsltid", "ved", "usqp"
)


def canonical_url(url: str | None) -> str:
    """Return the normalized canonical representation of a URL."""
    if not url:
        return ""
    u = url.strip()
    try:
        p = urllib.parse.urlparse(u)
    except Exception:
        return u.lower().rstrip("/")

    netloc = p.netloc.lower()
    if netloc.startswith("www."):
        netloc = netloc[4:]

    # Map domain aliases and mobile mirrors
    if netloc in DOMAIN_ALIAS_MAP:
        netloc = DOMAIN_ALIAS_MAP[netloc]
    elif netloc.startswith("m.") and netloc[2:] in DOMAIN_ALIAS_MAP:
        netloc = DOMAIN_ALIAS_MAP[netloc[2:]]
    elif netloc.startswith("m."):
        netloc = netloc[2:]

    path = p.path.rstrip("/")

    # Normalize DOIs to canonical https://doi.org/10.xxxx/...
    if "doi.org" in netloc:
        doi_match = re.search(r"(10\.\d{4,9}/[-._;()/:A-Za-z0-9]+)", path)
        if doi_match:
            return f"https://doi.org/{doi_match.group(1).lower()}"

    # Strip tracking and analytics parameters
    clean_params: list[tuple[str, str]] = []
    if p.query:
        try:
            params = urllib.parse.parse_qsl(p.query)
            for k, v in params:
                k_low = k.lower()
                if not any(k_low.startswith(prefix) for prefix in TRACKING_PARAM_PREFIXES):
                    clean_params.append((k, v))
        except Exception:
            pass
    query_str = urllib.parse.urlencode(clean_params)

    # Normalize AMP path variants
    clean_path = path.replace("/amp/", "/").replace("/amp_articleshow/", "/articleshow/")
    if clean_path.endswith("/amp"):
        clean_path = clean_path[:-4]

    scheme = "https" if p.scheme in ("http", "https") else p.scheme or "https"
    res = f"{scheme}://{netloc}{clean_path}"
    if query_str:
        res += f"?{query_str}"
    return res.lower()


def is_same_url(url1: str | None, url2: str | None) -> bool:
    """Check if two URLs point to the same canonical resource."""
    if not url1 or not url2:
        return False
    return canonical_url(url1) == canonical_url(url2)
