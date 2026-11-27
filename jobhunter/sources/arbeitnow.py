"""
Source #1: Arbeitnow (https://www.arbeitnow.com)

A free job board focused on Germany and Europe.
Its API needs NO key and returns jobs as JSON.

Big idea of this file:
    1. Ask the website for a page of jobs.
    2. Turn each job into our own standard shape (a Python dict).
    3. Return the list.
"""

import re
from datetime import datetime, timezone

import requests

API_URL = "https://www.arbeitnow.com/api/job-board-api"

# Be polite: tell the website who is calling.
HEADERS = {"User-Agent": "job-hunter (personal job search script)"}


def _strip_html(html: str) -> str:
    """The description comes as HTML (<p>, <li>...). Remove tags so we keep plain text."""
    text = re.sub(r"<[^>]+>", " ", html or "")
    return re.sub(r"\s+", " ", text).strip()


def _to_standard_job(raw: dict) -> dict:
    """Convert one Arbeitnow job into OUR standard job shape."""
    posted = raw.get("created_at")
    return {
        "id": f"arbeitnow:{raw.get('slug')}",  # unique id -> used later to skip duplicates
        "source": "arbeitnow",
        "title": raw.get("title", ""),
        "company": raw.get("company_name", ""),
        "location": raw.get("location", ""),
        "remote": bool(raw.get("remote")),
        "url": raw.get("url", ""),
        "tags": raw.get("tags", []),
        "description": _strip_html(raw.get("description", "")),
        "posted_at": (
            datetime.fromtimestamp(posted, tz=timezone.utc).isoformat() if posted else None
        ),
    }


def fetch(max_pages: int = 3, visa_sponsorship_only: bool = False) -> list[dict]:
    """
    Download up to `max_pages` pages of the newest jobs.

    visa_sponsorship_only=True asks Arbeitnow to return only jobs
    that say they sponsor visas (a filter their API supports).
    """
    jobs = []
    for page in range(1, max_pages + 1):
        params = {"page": page}
        if visa_sponsorship_only:
            params["visa_sponsorship"] = "true"

        response = requests.get(API_URL, params=params, headers=HEADERS, timeout=30)
        response.raise_for_status()  # if the website returns an error, stop loudly

        page_jobs = response.json().get("data", [])
        if not page_jobs:  # no more jobs -> stop asking
            break
        jobs.extend(_to_standard_job(j) for j in page_jobs)

    return jobs
