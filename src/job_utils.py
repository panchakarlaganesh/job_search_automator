import hashlib
from urllib.parse import urljoin, urlsplit, urlunsplit


def normalize_job_url(href, base_url):
    """Return an absolute job URL without query/fragment noise."""
    if not href:
        return None

    absolute_url = urljoin(base_url, href.strip())
    parts = urlsplit(absolute_url)
    return urlunsplit((parts.scheme, parts.netloc, parts.path, "", ""))


def stable_job_id(source, url=None, title="", company=""):
    """Create a deterministic external ID for dedupe across runs."""
    identity = url or f"{title}|{company}|{source}"
    digest = hashlib.sha256(identity.encode("utf-8")).hexdigest()[:16]
    return f"{source}_{digest}"
