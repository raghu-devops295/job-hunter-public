"""
Workday career sites (used by many banks and big tech: Kyndryl, Mastercard, Citi, PayPal, Philips...).

Every Workday site has a public JSON search behind its careers page:
    POST https://<tenant>.<wdN>.myworkdayjobs.com/wday/cxs/<tenant>/<site>/jobs   {"searchText": "devops", ...}
The list gives title, location and "Posted 3 Days Ago"; the description is fetched later
(only for jobs that pass the title gate, see add_description).

Add a company: open its careers page, copy <tenant>, <wdN> and <site> from the URL, e.g.
    https://kyndryl.wd5.myworkdayjobs.com/en-US/KyndrylProfessionalCareers  ->  ("kyndryl", "wd5", "KyndrylProfessionalCareers")
Sites that don't answer are listed at the end of the run so you can delete them.
"""

import re
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone

import requests

from jobhunter.sources.common import HEADERS, strip_html

SEARCHES = ["devops", "platform engineer", "cloud engineer", "site reliability", "azure", "kubernetes"]
PAGES_PER_SEARCH = 2          # 20 jobs per page


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
                              headers={**HEADERS, "Accept": "application/json"}, timeout=30)
            if r.status_code in (400, 403, 404, 422, 500):
                return None if not jobs and term == SEARCHES[0] and page == 0 else jobs
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
    r = requests.get(job["wd_ref"], headers={**HEADERS, "Accept": "application/json"}, timeout=30)
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
    jobs, not_found = [], []

    def one(site):
        try:
            return site, fetch_company(*site)
        except Exception:
            return site, None

    with ThreadPoolExecutor(max_workers=6) as pool:
        for site, found in pool.map(one, sites):
            if found is None:
                not_found.append(site[0])
            else:
                jobs += found
    return jobs, not_found
