"""
Big-company career sites (banks, corporates) that don't use the start-up hiring systems:

    Phenom          careers.allianz.com, careers.mastercard.com, careers.philips.com ...
                    The search page carries its results as JSON (phApp.ddo) - we read that.
    SuccessFactors  SAP "Career Site Builder" sites like basf.jobs, careers.eon.com ...
                    They offer an RSS feed per search (/services/rss/job/), else a plain HTML result list.

We only search for our role words, so each site costs a few requests.
"""

import json
import re
import xml.etree.ElementTree as ET
from email.utils import parsedate_to_datetime

import requests

from jobhunter.sources.common import HEADERS, strip_html

SEARCH_WORDS = ["devops", "platform engineer", "site reliability", "cloud engineer", "kubernetes", "azure"]
PHENOM_PREFIXES = ["global/en", "us/en", "en", "de/de", "nl/en", "ie/en"]


def company_name(host: str) -> str:
    """careers.allianz.com -> allianz, jobs.kuehne-nagel.com -> kuehne-nagel, basf.jobs -> basf"""
    parts = [p for p in host.lower().split(".") if p not in ("www", "careers", "career", "jobs", "job", "karriere")]
    return parts[0] if parts else host


def _job(source, host, raw_id, title, location, url, description, posted_at, remote=False):
    return {"id": f"{source}:{host}:{raw_id}", "source": source, "title": strip_html(title or ""), "company": company_name(host),
            "location": location or "", "remote": remote, "url": url, "tags": [],
            "description": strip_html(description or ""), "posted_at": posted_at}


# ---------------------------------------------------------------- Phenom

def _ddo(html: str) -> dict:
    m = re.search(r"phApp\.ddo\s*=\s*(\{.*?\});\s*phApp", html, re.S)
    return json.loads(m.group(1)) if m else {}


def fetch_phenom(site) -> list[dict] | None:
    """site = "careers.allianz.com" or ("careers.allianz.com", "global/en")."""
    host, prefixes = (site, PHENOM_PREFIXES) if isinstance(site, str) else (site[0], [site[1]])
    prefix, jobs, seen = None, [], set()
    for word in SEARCH_WORDS:
        for start in (0, 10):
            data, fallback = {}, None
            for p in ([prefix] if prefix else prefixes):
                r = requests.get(f"https://{host}/{p}/search-results", params={"keywords": word, "from": start},
                                 headers={**HEADERS, "Accept": "text/html"}, timeout=30)
                d = _ddo(r.text) if r.status_code == 200 else {}
                if d and ((d.get("eagerLoadRefineSearch") or {}).get("data") or {}).get("jobs"):
                    data, prefix = d, p
                    break
                if d and fallback is None:
                    fallback = (p, d)
            if not data:
                if fallback is None:
                    return None if prefix is None else jobs
                if prefix is None:
                    prefix, data = fallback
            found = ((data.get("eagerLoadRefineSearch") or {}).get("data") or {}).get("jobs") or []
            for j in found:
                if j.get("jobId") in seen:
                    continue
                seen.add(j.get("jobId"))
                where = ", ".join(filter(None, [j.get("city"), j.get("country")])) or j.get("cityStateCountry") or ""
                remote = "remote" in f"{j.get('remote')} {j.get('type')} {where}".lower()
                jobs.append(_job("phenom", host, j.get("jobId"), j.get("title"), ("Remote - " if remote else "") + where,
                                 f"https://{host}/{prefix}/job/{j.get('jobId')}", j.get("descriptionTeaser"),
                                 j.get("postedDate") or j.get("dateCreated"), remote))
            if len(found) < 10:
                break
    return jobs


def add_phenom_description(job: dict) -> None:
    r = requests.get(job["url"], headers={**HEADERS, "Accept": "text/html"}, timeout=30)
    r.raise_for_status()
    detail = ((_ddo(r.text).get("jobDetail") or {}).get("data") or {}).get("job") or {}
    text = detail.get("description") or ""
    if text:
        job["description"] = strip_html(text)


# ---------------------------------------------------------------- SAP SuccessFactors (Career Site Builder)

_LOC_IN_TITLE = re.compile(r"\(([^()]*,[^()]*)\)\s*$")     # "DevOps Engineer (m/f/d) (Berlin, DE, 10557)"
_ROW = re.compile(r'<a[^>]+class="jobTitle-link"[^>]+href="(/job/[^"]+)"[^>]*>(.*?)</a>.*?class="jobLocation"[^>]*>(.*?)</span>', re.S)


def fetch_successfactors(host: str) -> list[dict] | None:
    jobs, seen, any_ok = [], set(), False
    for word in SEARCH_WORDS:
        try:
            r = requests.get(f"https://{host}/services/rss/job/", params={"locale": "en_US", "keywords": f"({word})"},
                             headers=HEADERS, timeout=30)
        except requests.exceptions.ConnectionError:   # host unreachable (e.g. connect timeout): don't try the other words
            break
        if r.status_code == 200 and b"<rss" in r.content[:300]:
            try:
                items = list(ET.fromstring(r.content).iter("item"))
            except ET.ParseError:
                items = []
            any_ok = True
            for item in items:
                link = (item.findtext("link") or "").strip().split("?")[0]
                title = (item.findtext("title") or "").strip()
                if not link or link in seen or "no jobs currently available" in title.lower():
                    continue
                seen.add(link)
                m = _LOC_IN_TITLE.search(title)
                try:
                    posted = parsedate_to_datetime(item.findtext("pubDate") or "").isoformat()
                except (TypeError, ValueError):
                    posted = None
                where = m.group(1) if m else ""
                where = re.sub(r",\s*[\d -]{4,}$", "", where)                     # drop the postcode
                where = re.sub(r",\s*Other/Not Applicable", "", where)
                jobs.append(_job("successfactors", host, link.rstrip("/").split("/")[-1],
                                 _LOC_IN_TITLE.sub("", title).strip(), where, link,
                                 item.findtext("description"), posted))
            continue
        r = requests.get(f"https://{host}/search/", params={"q": word, "locale": "en_US"},
                         headers={**HEADERS, "Accept": "text/html"}, timeout=30)
        if r.status_code != 200 or "jobTitle-link" not in r.text:
            continue
        any_ok = True
        for href, title, where in _ROW.findall(r.text):
            link = f"https://{host}{href}"
            if link in seen:
                continue
            seen.add(link)
            jobs.append(_job("successfactors", host, href.rstrip("/").split("/")[-1], title, strip_html(where), link, "", None))
    return jobs if any_ok else None


def add_successfactors_description(job: dict) -> None:
    r = requests.get(job["url"], headers={**HEADERS, "Accept": "text/html"}, timeout=30)
    r.raise_for_status()
    m = re.search(r'class="jobdescription"[^>]*>(.*?)</span>\s*</span>', r.text, re.S) or \
        re.search(r'itemprop="description"[^>]*>(.*?)</(?:span|div)>\s*</(?:span|div)>', r.text, re.S)
    text = strip_html(m.group(1)) if m else ""
    if len(text) > len(job.get("description") or ""):
        job["description"] = text
    date = re.search(r'itemprop="datePosted"[^>]*content="([^"]+)"', r.text)
    if date and not job.get("posted_at"):
        job["posted_at"] = date.group(1)


FETCHERS = {"phenom": fetch_phenom, "successfactors": fetch_successfactors}
