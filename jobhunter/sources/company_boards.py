"""
Company career pages on 10 hiring systems:
    Greenhouse, Lever, Ashby, Recruitee, SmartRecruiters, Personio, Workable, BambooHR, Teamtailor, Join.com.

Many tech companies don't build their own careers site - they rent one from a
"hiring system". These three systems publish every company's jobs as free JSON.
So one small function per system lets us read MANY companies.
"""

import json
import re
import xml.etree.ElementTree as ET
from datetime import datetime, timezone

import requests

from jobhunter.sources.common import HEADERS, get_json, get_json_retry, strip_html


def _job(source, company, raw_id, title, location, remote, url, description, posted_at):
    """Build our standard job shape (same as arbeitnow.py)."""
    return {
        "id": f"{source}:{company}:{raw_id}",
        "source": source,
        "title": title or "",
        "company": company,
        "location": location or "",
        "remote": bool(remote),
        "url": url or "",
        "tags": [],
        "description": description or "",
        "posted_at": posted_at,
    }


def fetch_greenhouse(company: str) -> list[dict] | None:
    data = get_json(f"https://boards-api.greenhouse.io/v1/boards/{company}/jobs", params={"content": "true"})
    if data is None:
        return None
    return [
        _job("greenhouse", company, j.get("id"), j.get("title"),
             (j.get("location") or {}).get("name"),
             "remote" in ((j.get("location") or {}).get("name") or "").lower(),
             j.get("absolute_url"), strip_html(j.get("content")), j.get("updated_at"))
        for j in data.get("jobs", [])
    ]


def fetch_lever(company: str) -> list[dict] | None:
    # Some companies live on Lever's EU server, so try both.
    data = None
    for host in ("api.lever.co", "api.eu.lever.co"):
        data = get_json(f"https://{host}/v0/postings/{company}", params={"mode": "json"})
        if data is not None:
            break
    if data is None:
        return None
    jobs = []
    for j in data:
        cats = j.get("categories") or {}
        created = j.get("createdAt")
        jobs.append(_job(
            "lever", company, j.get("id"), j.get("text"), cats.get("location"),
            j.get("workplaceType") == "remote", j.get("hostedUrl"),
            (j.get("descriptionPlain") or "") + " " + strip_html(" ".join(
                (lst.get("content") or "") for lst in (j.get("lists") or []))),
            datetime.fromtimestamp(created / 1000, tz=timezone.utc).isoformat() if created else None,
        ))
    return jobs


def fetch_ashby(company: str) -> list[dict] | None:
    data = get_json(f"https://api.ashbyhq.com/posting-api/job-board/{company}")
    if data is None:
        return None
    return [
        _job("ashby", company, j.get("id"), j.get("title"), j.get("location"),
             j.get("isRemote"), j.get("jobUrl"),
             j.get("descriptionPlain") or strip_html(j.get("descriptionHtml")), j.get("publishedAt"))
        for j in data.get("jobs", [])
    ]


def fetch_recruitee(company: str) -> list[dict] | None:
    """Recruitee (popular in the Netherlands): https://COMPANY.recruitee.com/api/offers/"""
    data = get_json_retry(f"https://{company}.recruitee.com/api/offers/")
    if data is None:
        return None
    jobs = []
    for j in data.get("offers", []):
        where = ", ".join(filter(None, [j.get("city"), j.get("country")])) or j.get("location") or ""
        jobs.append(_job("recruitee", company, j.get("id"), j.get("title"), where, j.get("remote"),
                         j.get("careers_url"),
                         strip_html((j.get("description") or "") + " " + (j.get("requirements") or "")),
                         j.get("published_at") or j.get("created_at")))
    return jobs


def fetch_smartrecruiters(company: str) -> list[dict] | None:
    """SmartRecruiters (large EU employers). The list has no description, so we fetch it later
    only for jobs whose title passes the title gate (see add_smartrecruiters_description)."""
    jobs, offset = [], 0
    while True:
        data = get_json(f"https://api.smartrecruiters.com/v1/companies/{company}/postings",
                        params={"limit": 100, "offset": offset})
        if data is None:
            return None
        content = data.get("content", [])
        if offset == 0 and not content and not data.get("totalFound"):
            return None                       # unknown company -> treat as "not found"
        for j in content:
            loc = j.get("location") or {}
            where = ", ".join(filter(None, [loc.get("city"), (loc.get("country") or "").upper()]))
            job = _job("smartrecruiters", company, j.get("id"), j.get("name"), where, loc.get("remote"),
                       f"https://jobs.smartrecruiters.com/{company}/{j.get('id')}", "", j.get("releasedDate"))
            job["sr_ref"] = j.get("ref")      # API link to the full posting
            jobs.append(job)
        offset += len(content)
        if not content or offset >= data.get("totalFound", 0) or offset >= 1000:
            return jobs


def add_smartrecruiters_description(job: dict) -> None:
    data = get_json(job["sr_ref"]) if job.get("sr_ref") else None
    sections = ((data or {}).get("jobAd") or {}).get("sections") or {}
    job["description"] = strip_html(" ".join((sec or {}).get("text") or "" for sec in sections.values()))


def fetch_personio(company: str) -> list[dict] | None:
    """Personio (thousands of German/EU companies): XML feed at COMPANY.jobs.personio.de/xml"""
    for domain in ("de", "com"):
        r = requests.get(f"https://{company}.jobs.personio.{domain}/xml", params={"language": "en"},
                         headers=HEADERS, timeout=30)
        if r.status_code == 200 and b"<position" in r.content:
            break
        if r.status_code == 200 and b"workzag-jobs" in r.content:
            return []                         # company exists, no open jobs right now
    else:
        return None
    root = ET.fromstring(r.content)
    jobs = []
    for p in root.iter("position"):
        text = lambda tag: (p.findtext(tag) or "").strip()
        offices = [text("office")] + [o.text.strip() for o in p.iter("office") if o.text and o.text.strip() != text("office")]
        description = " ".join(strip_html(d.findtext("value") or "") for d in p.iter("jobDescription"))
        jobs.append(_job("personio", company, text("id"), text("name"), "; ".join(filter(None, offices)),
                         "remote" in " ".join(offices).lower(),
                         f"https://{company}.jobs.personio.{domain}/job/{text('id')}?language=en",
                         description, text("createdAt") or None))
    return jobs


def fetch_workable(company: str) -> list[dict] | None:
    """Workable (many EU start-ups): public widget API."""
    data = get_json(f"https://apply.workable.com/api/v1/widget/accounts/{company}", params={"details": "true"})
    if data is None:
        return None
    jobs = []
    for j in data.get("jobs", []):
        where = ", ".join(filter(None, [j.get("city"), j.get("country")]))
        jobs.append(_job("workable", company, j.get("shortcode"), j.get("title"), where, j.get("telecommuting"),
                         j.get("url") or j.get("application_url"), strip_html(j.get("description")),
                         j.get("published_on") or j.get("created_at")))
    return jobs


def fetch_bamboohr(company: str) -> list[dict] | None:
    """BambooHR (small/mid EU companies): COMPANY.bamboohr.com/careers/list (JSON). Description fetched later."""
    data = get_json(f"https://{company}.bamboohr.com/careers/list")
    if not isinstance(data, dict) or "result" not in data:
        return None
    jobs = []
    for j in data.get("result") or []:
        loc, ats = j.get("location") or {}, j.get("atsLocation") or {}
        where = ", ".join(dict.fromkeys(filter(None, [loc.get("city") or ats.get("city"),
                                                      ats.get("country") or loc.get("state")])))
        jobs.append(_job("bamboohr", company, j.get("id"), j.get("jobOpeningName"), where,
                         j.get("isRemote") or "remote" in where.lower(),
                         f"https://{company}.bamboohr.com/careers/{j.get('id')}", "", None))
    return jobs


def add_bamboohr_description(job: dict) -> None:
    company, raw_id = job["id"].split(":")[1], job["id"].split(":")[2]
    data = get_json(f"https://{company}.bamboohr.com/careers/{raw_id}/detail") or {}
    opening = (data.get("result") or {}).get("jobOpening") or {}
    job["description"] = strip_html(opening.get("description") or "")
    job["posted_at"] = opening.get("datePosted") or job.get("posted_at")


def fetch_teamtailor(company: str) -> list[dict] | None:
    """Teamtailor (popular in the Nordics/NL): COMPANY.teamtailor.com/jobs.rss"""
    r = requests.get(f"https://{company}.teamtailor.com/jobs.rss", headers=HEADERS, timeout=30)
    if r.status_code != 200 or b"<rss" not in r.content[:500]:
        return None
    jobs = []
    for item in ET.fromstring(r.content).iter("item"):
        fields = {}
        for el in item.iter():
            tag = el.tag.split("}")[-1].lower()
            if el.text and el.text.strip():
                fields.setdefault(tag, []).append(el.text.strip())
        first = lambda tag: (fields.get(tag) or [""])[0]
        where = ", ".join(dict.fromkeys(fields.get("city", []) + fields.get("country", [])))
        try:
            from email.utils import parsedate_to_datetime
            posted = parsedate_to_datetime(first("pubdate")).isoformat()
        except (TypeError, ValueError):
            posted = None
        link = first("link")
        jobs.append(_job("teamtailor", company, link.rstrip("/").split("/")[-1], first("title"), where,
                         "remote" in (where + first("remotestatus")).lower(), link, strip_html(first("description")),
                         posted))
    return jobs


def fetch_join(company: str) -> list[dict] | None:
    """Join.com (many German start-ups): job links on join.com/companies/COMPANY. Description fetched later."""
    r = requests.get(f"https://join.com/companies/{company}", headers={**HEADERS, "Accept": "text/html"}, timeout=30)
    if r.status_code != 200:
        return None
    jobs, seen = [], set()
    for href, job_id, inner in re.findall(
            rf'<a[^>]+href="((?:https://join\.com)?/companies/{re.escape(company)}/(\d+)-[^"]+)"[^>]*>(.*?)</a>', r.text, re.S):
        if job_id in seen:
            continue
        seen.add(job_id)
        text = strip_html(inner).strip()
        title = text.split("  ")[0] if text else href.split(f"{job_id}-")[-1].replace("-", " ").title()
        url = href if href.startswith("http") else "https://join.com" + href
        jobs.append(_job("join", company, job_id, title[:150], "", False, url, "", None))
    return jobs


def _required_language(html: str) -> str:
    """Boards like Magnet.me show the language rule in a separate field: 'Required language Dutch ( Fluent )'."""
    text = strip_html(html)
    i = text.find("Required language")
    if i < 0:
        return ""
    found = re.findall(r"([A-Z][a-z]+)\s*\(\s*([A-Za-z ]+?)\s*\)", text[i:i + 160])    # "English ( Fluent ) Dutch ( Fluent )"
    return "".join(f"\nRequired language: {lang} ({level})" for lang, level in found)


def add_jsonld_description(job: dict) -> None:
    """Most job pages carry a schema.org JobPosting (JSON-LD): description, date, location."""
    r = requests.get(job["url"], headers={**HEADERS, "Accept": "text/html"}, timeout=30)
    r.raise_for_status()
    extra = _required_language(r.text)
    for block in re.findall(r'<script[^>]+application/ld\+json[^>]*>(.*?)</script>', r.text, re.S):
        try:
            data = json.loads(block)
        except ValueError:
            continue
        items = data if isinstance(data, list) else data.get("@graph", [data]) if isinstance(data, dict) else []
        for item in items:
            if isinstance(item, dict) and "JobPosting" in str(item.get("@type")):
                job["title"] = strip_html(item.get("title") or "") or job["title"]
                job["description"] = strip_html(item.get("description") or "") + extra
                job["posted_at"] = item.get("datePosted") or job.get("posted_at")
                org = item.get("hiringOrganization") or {}
                if isinstance(org, dict) and org.get("name") and not job.get("company"):
                    job["company"] = strip_html(org["name"])
                places = item.get("jobLocation") or []
                places = places if isinstance(places, list) else [places]
                where = []
                for place in places:
                    addr = (place or {}).get("address") or {}
                    if isinstance(addr, dict):
                        country = addr.get("addressCountry")
                        country = country.get("name") if isinstance(country, dict) else country
                        where.append(", ".join(filter(None, [addr.get("addressLocality"), country])))
                if any(where) and not job.get("location"):
                    job["location"] = "; ".join(filter(None, where))
                if "TELECOMMUTE" in str(item.get("jobLocationType", "")).upper():
                    job["remote"] = True
                    job["location"] = "Remote - " + (job.get("location") or "")
                return
    # no JSON-LD: keep the plain page text as description
    job["description"] = strip_html(re.sub(r"(?is)<(script|style|nav|footer|header)[^>]*>.*?</\1>", " ", r.text))[:8000] + extra


FETCHERS = {"greenhouse": fetch_greenhouse, "lever": fetch_lever, "ashby": fetch_ashby,
            "recruitee": fetch_recruitee, "smartrecruiters": fetch_smartrecruiters,
            "personio": fetch_personio, "workable": fetch_workable,
            "bamboohr": fetch_bamboohr, "teamtailor": fetch_teamtailor, "join": fetch_join}


class SkipCompany(Exception):
    """Raised instead of downloading when a hiring system was paused for this run."""


# Wait this many seconds between two requests to the same hiring system (Recruitee rate-limits
# when many companies are read at once).
THROTTLE_SECONDS = {"recruitee": 1.5}
# After this many errors from one hiring system in one run, skip its remaining companies.
MAX_ERRORS_PER_SYSTEM = 4


def fetch_all(companies_by_system: dict[str, list[str]]) -> tuple[list[dict], list[str]]:
    """
    Read every company. Returns (all jobs, list of companies that were not found).
    Runs 8 downloads AT THE SAME TIME (like 8 browser tabs) instead of one by one.
    Per hiring system: requests are spaced out (THROTTLE_SECONDS), and after
    MAX_ERRORS_PER_SYSTEM errors the rest of that system is skipped for this run.
    """
    import threading
    import time
    from collections import defaultdict
    from concurrent.futures import ThreadPoolExecutor

    tasks = [(system, company) for system, companies in companies_by_system.items() for company in companies]
    lock = threading.Lock()
    next_slot: dict[str, float] = defaultdict(float)   # earliest time the next request may start
    errors: dict[str, int] = defaultdict(int)
    paused: set[str] = set()

    def run_one(task):
        system, company = task
        with lock:
            if system in paused:
                return task, [], SkipCompany(f"{system} paused after repeated errors")
            # reserve a start time, so requests to this system are spaced out
            start = max(time.monotonic(), next_slot[system])
            next_slot[system] = start + THROTTLE_SECONDS.get(system, 0)
        time.sleep(max(0.0, start - time.monotonic()))
        try:
            return task, FETCHERS[system](company), None
        except Exception as error:          # one broken company must not stop the robot
            with lock:
                errors[system] += 1
                if errors[system] >= MAX_ERRORS_PER_SYSTEM and system not in paused:
                    paused.add(system)
                    print(f"   ! {system}: {errors[system]} errors - skipping the rest of {system} this run")
            return task, [], error

    all_jobs, not_found = [], []
    with ThreadPoolExecutor(max_workers=8) as pool:
        for (system, company), jobs, error in pool.map(run_one, tasks):
            if isinstance(error, SkipCompany):
                continue
            if error:
                print(f"   ! {system}/{company}: error {error}")
            elif jobs is None:
                not_found.append(f"{system}/{company}")
            else:
                all_jobs.extend(jobs)
    return all_jobs, not_found
