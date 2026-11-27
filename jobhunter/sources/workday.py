"""
Workday career sites (used by many banks and big tech: Kyndryl, Mastercard, Citi, PayPal, Philips...).

Every Workday site has a public JSON search behind its careers page:
    POST https://<tenant>.<wdN>.myworkdayjobs.com/wday/cxs/<tenant>/<site>/jobs   {"searchText": "devops", ...}
The list gives title, location and "Posted 3 Days Ago"; the description is fetched later
(only for jobs that pass the title gate, see add_description).

Add a company: open its careers page, copy <tenant>, <wdN> and <site> from the URL, e.g.
    https://kyndryl.wd5.myworkdayjobs.com/en-US/KyndrylProfessionalCareers  ->  ("kyndryl", "wd5", "KyndrylProfessionalCareers")
Sites that don't exist (404) are listed at the end of the run so you can delete them.

BLOCKED (since 16 Nov 2026): Workday's Cloudflare answers HTTP 429 to every request from GitHub's
servers (Azure IPs), with any User-Agent and also after waiting. That is not a dead site, so blocked
sites are reported separately and never as "not found". To get Workday jobs again, send the requests
through another IP: set the secret WORKDAY_PROXY (e.g. http://user:pass@host:port) or run the
job hunter on a self-hosted runner (your own PC).
"""

import os
import re
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone

import requests

from jobhunter.sources.common import HEADERS, strip_html

SEARCHES = ["devops", "platform engineer", "cloud engineer", "site reliability", "azure", "kubernetes"]
PAGES_PER_SEARCH = 2          # 20 jobs per page
NOT_FOUND = (400, 404, 410, 422)   # unknown tenant / site
BLOCKED = (403, 429)               # Cloudflare refuses this IP

_proxy = os.environ.get("WORKDAY_PROXY", "").strip()
PROXIES = {"http": _proxy, "https": _proxy} if _proxy else None

blocked: list[str] = []            # filled by fetch_all: "tenant (HTTP 429)" - shown in the run log


class Blocked(Exception):
    pass


def _base(tenant, wd):
    return f"https://{tenant}.{wd}.myworkdayjobs.com"


def _posted(text: str) -> str | None:
    """'Posted Today' / 'Posted Yesterday' / 'Posted 5 Days Ago' / 'Posted 30+ Days Ago' -> ISO date"""
    text = (text or "").lower()
    now = datetime.now(timezone.utc)
    if "today" in text:
        days = 0
    elif "yesterday" in text:
        days = 1
    else:
        m = re.search(r"(\d+)\+? days? ago", text)
        if not m:
            return None
        days = int(m.group(1)) + (1 if "+" in text else 0)
    return (now - timedelta(days=days)).isoformat()


def fetch_company(tenant: str, wd: str, site: str) -> list[dict] | None:
    url = f"{_base(tenant, wd)}/wday/cxs/{tenant}/{site}/jobs"
    jobs, seen = [], set()
    for term in SEARCHES:
        for page in range(PAGES_PER_SEARCH):
            r = requests.post(url, json={"appliedFacets": {}, "limit": 20, "offset": page * 20, "searchText": term},
                              headers={**HEADERS, "Accept": "application/json"}, proxies=PROXIES, timeout=30)
            first = not jobs and term == SEARCHES[0] and page == 0
            if r.status_code in BLOCKED:
                if first:
                    raise Blocked(f"HTTP {r.status_code}")
                return jobs              # blocked half-way: keep what we have
            if r.status_code in NOT_FOUND:
                return None if first else jobs
            r.raise_for_status()
            postings = r.json().get("jobPostings") or []
            for p in postings:
                path = p.get("externalPath")
                if not path or path in seen:
                    continue
                seen.add(path)
                jobs.append({"id": f"workday:{tenant}:{path}", "source": "workday", "company": tenant,
                             "title": p.get("title") or "", "location": p.get("locationsText") or "",
                             "remote": "remote" in (p.get("remoteType") or "").lower(),
                             "url": f"{_base(tenant, wd)}/en-US/{site}{path}", "description": "",
                             "posted_at": _posted(p.get("postedOn")),
                             "wd_ref": f"{_base(tenant, wd)}/wday/cxs/{tenant}/{site}{path}"})
            if len(postings) < 20:
                break
    return jobs


def add_description(job: dict) -> None:
    """Fetch full description + exact location for one job (called only for title-gate survivors)."""
    r = requests.get(job["wd_ref"], headers={**HEADERS, "Accept": "application/json"}, proxies=PROXIES, timeout=30)
    r.raise_for_status()
    info = r.json().get("jobPostingInfo") or {}
    job["description"] = strip_html(info.get("jobDescription") or "")
    extra = info.get("additionalLocations") or []
    country = (info.get("country") or {}).get("descriptor") or ""
    parts = [info.get("location") or job["location"], *extra]
    if country and country.lower() not in " ".join(parts).lower():
        parts.append(country)
    job["location"] = ", ".join(x for x in parts if x)
    if "remote" in (info.get("remoteType") or "").lower():
        job["remote"] = True
    if info.get("startDate"):
        job["posted_at"] = info["startDate"]
    hiring = (r.json().get("hiringOrganization") or {}).get("name")
    if hiring:
        hiring = re.sub(r"^\d+\s*", "", hiring)
        job["company"] = f"{job['company']} ({hiring})"


def fetch_all(sites: list[tuple[str, str, str]]) -> tuple[list[dict], list[str]]:
    """Returns (jobs, not_found). not_found = only sites that really don't exist (404 etc.).
    Sites that refused us (429/403) or errored go to the module list `blocked` instead."""
    jobs, not_found = [], []
    blocked.clear()

    def one(site):
        try:
            return site, fetch_company(*site), None
        except Blocked as e:
            return site, None, str(e)
        except Exception as e:           # timeout, 5xx, bad JSON...
            return site, None, f"{type(e).__name__}: {str(e)[:80]}"

    # Probe one site first: if Workday blocks this IP, all sites are blocked - don't hammer 66 of them.
    if sites:
        site, found, err = one(sites[0])
        if err and err.startswith("HTTP 4"):
            blocked.extend(f"{s[0]} ({err})" for s in sites)
            return jobs, not_found
        results = [(site, found, err)]
        with ThreadPoolExecutor(max_workers=6) as pool:
            results += list(pool.map(one, sites[1:]))
        for site, found, err in results:
            if err:
                blocked.append(f"{site[0]} ({err})")
            elif found is None:
                not_found.append(site[0])
            else:
                jobs += found
    return jobs, not_found
