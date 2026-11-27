"""
Small helpers that ALL sources share, so we don't write the same code 5 times.
"""

import html
import re
import time

import requests

HEADERS = {"User-Agent": "job-hunter (personal job search script)"}


RETRY_WAITS = (15, 30)   # seconds to wait before retry 1 and retry 2 when a site says "too many requests" or is busy


def get_json(url: str, params: dict | None = None, headers: dict | None = None):
    """Download a URL and return its JSON. Returns None if the page doesn't exist (404).

    429 (too many requests) and 502/503/504 (busy) are retried, honouring Retry-After when it is shorter.
    """
    import time

    for attempt in range(len(RETRY_WAITS) + 1):
        response = requests.get(url, params=params, headers={**HEADERS, **(headers or {})}, timeout=30)
        if response.status_code in (400, 403, 404, 410):   # unknown company / page gone
            return None
        if response.status_code in (429, 502, 503, 504) and attempt < len(RETRY_WAITS):
            wait = RETRY_WAITS[attempt]
            try:
                wait = min(wait, float(response.headers.get("Retry-After", wait)))
            except ValueError:
                pass
            time.sleep(max(wait, 1))
            continue
        response.raise_for_status()
        return response.json()


def get_json_retry(url: str, params: dict | None = None, headers: dict | None = None,
                   tries: int = 3, wait: int = 15):
    """Like get_json, but waits and tries again on 429 (too many requests) and 503 (service unavailable).
    Waits the Retry-After seconds if the server gives them, else 15s, then 30s."""
    for attempt in range(1, tries + 1):
        response = requests.get(url, params=params, headers={**HEADERS, **(headers or {})}, timeout=30)
        if response.status_code not in (429, 503) or attempt == tries:
            break
        retry_after = response.headers.get("Retry-After", "")
        time.sleep(min(int(retry_after) if retry_after.isdigit() else wait * attempt, 60))
    if response.status_code in (400, 403, 404, 410):   # unknown company / page gone
        return None
    response.raise_for_status()
    return response.json()


def strip_html(text: str) -> str:
    """'&lt;p&gt;Hello &lt;b&gt;world&lt;/b&gt;' -> 'Hello world'"""
    text = html.unescape(html.unescape(text or ""))  # turn &lt; back into < (twice: Greenhouse double-wraps)
    text = re.sub(r"<[^>]+>", " ", text)      # remove <tags>
    return re.sub(r"\s+", " ", text).strip()  # squash extra spaces
