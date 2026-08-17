#!/usr/bin/env python3
"""Check whether a URL is allowed to be fetched according to robots.txt.

Ported from MadsLorentzen/ai-job-search tools/robots_check.py (upstream fix 8ffe987).

Key improvements over a naive urllib.robotparser approach:
  * Fails CLOSED on a soft HTTP 200 that returns an HTML/JSON error page instead
    of a real robots.txt (is_robots_body guard).
  * Percent-decodes Disallow rules via unquote() so encoded patterns like
    /foo%20bar correctly match the decoded path /foo bar.
  * Hardens curl invocation with '--' argument terminator.
  * Tolerates blank lines inside a robots.txt record (Python's robotparser drops
    rules in that case, which fails open).

Rules (RFC 9309, cautious side):
  * longest-match wins; on equal specificity Disallow wins
  * a Disallow for either "*" or "Claude-User" blocks access
  * 404 means no published policy -> permission
  * any other failure leaves permission unconfirmed -> deny

Usage:
    python tools/robots_check.py <url>
    Exit 0 = allowed. Exit 1 = denied or unconfirmed.
"""

import re
import subprocess
import sys
from urllib.parse import urlsplit, unquote

BROWSER = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/127.0.0.0 Safari/537.36"
)


def _fetch(url, ua):
    """Fetch via curl (more reliable than urllib for robots.txt on some hosts)."""
    r = subprocess.run(
        ["curl", "-sS", "-L", "--max-redirs", "5", "--max-time", "12", "-A", ua,
         "-H", "Accept: text/plain,*/*", "-w", "\n%{http_code}", "--", url],
        capture_output=True, text=True, timeout=20,
    )
    if r.returncode != 0:
        raise RuntimeError("curl exit %d" % r.returncode)
    body, _, code = r.stdout.rpartition("\n")
    return body, int(code or 0)


def is_robots_body(text):
    """Does this body actually look like a robots.txt?

    Guards against soft-200 responses that return an HTML/JSON error page.
    An empty body is a valid allow-all under RFC 9309.
    A non-empty body with no recognised directive is treated as unreadable.
    """
    if not text.strip():
        return True
    for raw in text.splitlines():
        line = raw.split("#", 1)[0].strip().lower()
        if ":" in line and line.split(":", 1)[0].strip() in (
            "user-agent", "allow", "disallow", "sitemap", "crawl-delay", "host",
        ):
            return True
    return False


def _groups(text):
    """Parse robots.txt into {user-agent: [(is_allow, pattern)]}."""
    out, agents, expect = {}, [], True
    for raw in text.splitlines():
        line = raw.split("#", 1)[0].strip()
        if not line or ":" not in line:
            continue
        field, _, value = line.partition(":")
        field, value = field.strip().lower(), value.strip()
        if field == "user-agent":
            if not expect:
                agents, expect = [], True
            agents.append(value.lower())
            out.setdefault(value.lower(), [])
        elif field in ("allow", "disallow") and agents:
            expect = False
            for a in agents:
                out[a].append((field == "allow", value))
    return out


def _match(pattern, path):
    """RFC 9309 wildcard match; returns match length or -1.

    Percent-decodes the pattern before matching so encoded rules like
    /foo%20bar correctly match the decoded path /foo bar.
    """
    if pattern == "":
        return -1
    pattern = unquote(pattern)
    rx = "^" + "".join(
        ".*" if c == "*" else ("$" if c == "$" else re.escape(c))
        for c in pattern
    )
    return len(pattern) if re.match(rx, path) else -1


def allowed(text, agent, path):
    """Return True if agent is allowed to fetch path per robots.txt text."""
    g = _groups(text)
    rules = g.get(agent.lower()) or g.get("*") or []
    best_len, best_allow = -1, True
    for is_allow, pat in rules:
        n = _match(pat, path)
        if n > best_len or (n == best_len and n >= 0 and not is_allow):
            best_len, best_allow = n, is_allow  # ties -> Disallow wins
    return True if best_len < 0 else best_allow


def gate(url):
    """Return (exit_code, message) for whether url may be fetched.

    exit_code 0 = allowed, 1 = denied or unconfirmed.
    Tries Claude-User UA first, then a browser UA, fails closed if neither works.
    """
    parts = urlsplit(url)
    path = unquote(parts.path) or "/"
    if parts.query:
        path += "?" + parts.query
    robots = f"{parts.scheme}://{parts.netloc}/robots.txt"
    body, last = None, "no attempt"
    for ua in ("Claude-User", BROWSER):
        try:
            text, code = _fetch(robots, ua)
        except Exception as e:
            last = type(e).__name__
            continue
        if code == 404:
            return 0, "ALLOWED - no robots.txt published"
        if code == 200:
            if not is_robots_body(text):
                last = "HTTP 200 but the body is not a robots.txt"
                continue
            body = text
            break
        last = "HTTP %d" % code
    if body is None:
        return 1, "UNCONFIRMED (%s) - treating as denied" % last
    for a in ("Claude-User", "*"):
        if not allowed(body, a, path):
            return 1, f"DISALLOWED for {a}"
    return 0, "ALLOWED - robots.txt permits this path"


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("usage: python tools/robots_check.py <url>", file=sys.stderr)
        sys.exit(2)
    rc, msg = gate(sys.argv[1])
    print(msg)
    sys.exit(rc)
