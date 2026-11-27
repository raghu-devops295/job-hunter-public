"""
More free job boards (no key needed). Each is optional: if a site is down or changes format,
it prints a warning and the run carries on.

    NoFluffJobs   (Poland)   https://nofluffjobs.com/api/posting          all postings, we keep DevOps/cloud ones
    JustJoin.it   (Poland)   https://api.justjoin.it/v2/user-panel/offers  newest DevOps offers
    WeWorkRemotely (remote)  RSS feed of the DevOps/Sysadmin category
    Working Nomads (remote)  https://www.workingnomads.com/api/exposed_jobs/
"""

import re
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime

import requests

from jobhunter.sources.common import HEADERS, get_json, get_json_retry, strip_html

DEVOPS_WORDS = r"devops|platform|site reliability|\bsre\b|cloud|kubernetes|azure|infrastructure"


def _job(source, raw_id, title, company, location, url, description, posted_at, remote=False):
    return {"id": f"{source}:{raw_id}", "source": source, "title": title or "", "company": company or "",
            "location": location or "", "remote": remote, "url": url or "",
            "description": strip_html(description or ""), "posted_at": posted_at}


def nofluffjobs() -> list[dict]:
    data = get_json("https://nofluffjobs.com/api/posting") or {}
    jobs = []
    for p in data.get("postings", []):
        if not re.search(DEVOPS_WORDS, (p.get("title") or "").lower()) and p.get("category") != "devops":
            continue
        loc = p.get("location") or {}
        places = [x.get("city") for x in loc.get("places") or [] if x.get("city")]
        remote = bool(loc.get("fullyRemote"))
        where = ", ".join(dict.fromkeys(places)) + ", Poland" if places else "Poland"
        posted = p.get("posted")
        posted = datetime.fromtimestamp(posted / 1000, timezone.utc).isoformat() if isinstance(posted, (int, float)) else None
        job = _job("nofluffjobs", p.get("id"), p.get("title"), p.get("name"),
                   ("Remote - Poland, " if remote else "") + where,
                   f"https://nofluffjobs.com/job/{p.get('url')}", "", posted, remote)
        kind = (p.get("salary") or {}).get("type")
        job["contracts"] = [kind] if kind else []     # the list shows one type; the ad page shows all of them
        jobs.append(job)
    return jobs


def add_nofluff_description(job: dict) -> None:
    """Read the ad page: full description, must/nice skills, and ALL contract types (b2b, permanent...)."""
    x = get_json("https://nofluffjobs.com/api/posting/" + job["id"].split(":", 1)[1]) or {}
    types = ((x.get("essentials") or {}).get("originalSalary") or {}).get("types") or {}
    if types:
        job["contracts"] = list(types)
    req = x.get("requirements") or {}
    musts = ", ".join(m.get("value", "") for m in req.get("musts") or [])
    nices = ", ".join(m.get("value", "") for m in req.get("nices") or [])
    parts = [(x.get("details") or {}).get("description") or "", req.get("description") or ""]
    text = strip_html(" ".join(parts))
    if musts:
        text += f"\nMust have: {musts}"
    if nices:
        text += f"\nNice to have: {nices}"
    if text.strip():
        job["description"] = text


def justjoin() -> list[dict]:
    jobs = []
    for category in ("devops", "admin"):
        data = get_json_retry("https://api.justjoin.it/v2/user-panel/offers",
                        params={"categories[]": category, "perPage": 100, "sortBy": "published", "orderBy": "DESC"},
                        headers={"Version": "2"})
        if data is None:   # 400/403/404 -> get_json returns None; say so instead of 0 jobs
            raise RuntimeError(f"API page for category '{category}' not found (endpoint or parameters changed?)")
        for o in data.get("data", []):
            remote = (o.get("workplaceType") or "") == "remote"
            job = _job("justjoin", o.get("slug"), o.get("title"), o.get("companyName"),
                       ("Remote - Poland, " if remote else "") + f"{o.get('city') or ''}, Poland",
                       f"https://justjoin.it/job-offer/{o.get('slug')}", "", o.get("publishedAt"), remote)
            job["contracts"] = [t.get("type") for t in o.get("employmentTypes") or [] if t.get("type")]
            jobs.append(job)
    return jobs


def weworkremotely() -> list[dict]:
    r = requests.get("https://weworkremotely.com/categories/remote-devops-sysadmin-jobs.rss", headers=HEADERS, timeout=30)
    r.raise_for_status()
    jobs = []
    for item in ET.fromstring(r.content).iter("item"):
        text = lambda tag: (item.findtext(tag) or "").strip()
        company, _, title = text("title").partition(": ")
        try:
            posted = parsedate_to_datetime(text("pubDate")).isoformat()
        except (TypeError, ValueError):
            posted = None
        jobs.append(_job("weworkremotely", text("guid") or text("link"), title or company, company if title else "",
                         "Remote - " + (text("region") or "Worldwide"), text("link"), text("description"), posted, True))
    return jobs


def workingnomads() -> list[dict]:
    data = get_json("https://www.workingnomads.com/api/exposed_jobs/") or []
    return [_job("workingnomads", j.get("url"), j.get("title"), j.get("company_name"),
                 "Remote - " + (j.get("location") or "Worldwide"), j.get("url"), j.get("description"),
                 j.get("pub_date"), True)
            for j in data if re.search(DEVOPS_WORDS, f"{j.get('title')} {j.get('category_name')}".lower())]


def fetch_all() -> list[dict]:
    jobs = []
    # (Jaabz is not scanned: the site blocks automated access - use its free email alerts instead.)
    from jobhunter.scoring import TARGET_COUNTRIES
    # (name, function, the ONE country the board covers - None = many countries). Boards for a country that is
    # not in lists/countries.txt are not called at all: their jobs would all be filtered out anyway.
    boards = (("CVonline.lt + CV.ee", cvonline, None), ("Jobly.fi", jobly, "Finland"), ("Magnet.me", magnetme, "Netherlands"),
              ("Jobindex.dk", jobindex, "Denmark"), ("IT-jobbank.dk", itjobbank, "Denmark"), ("The Hub", thehub, None),
              ("relocate.me", relocateme, None), ("NoFluffJobs", nofluffjobs, "Poland"),
              ("JustJoin.it", justjoin, "Poland"), ("WeWorkRemotely", weworkremotely, None), ("Working Nomads", workingnomads, None))
    for name, fn, country in boards:
        if country and country not in TARGET_COUNTRIES:
            print(f"    {name}: skipped ({country} is not in lists/countries.txt)")
            continue
        try:
            found = fn()
            print(f"    {name}: {len(found)} jobs")
            if not found:
                print(f"    ! WARNING {name} returned 0 jobs - check the source")
            jobs += found
        except Exception as error:
            print(f"    ! {name} failed: {str(error)[:120]}")
    return jobs


# ---------------- relocate.me: only jobs that offer relocation (visa, flight, housing help) ----------------
RELOCATE_SEARCHES = ["devops", "platform-engineer", "site-reliability-engineer", "azure", "kubernetes", "cloud-engineer"]
_RELOC_LINK = re.compile(r'href="(?:https://relocate\.me)?/([a-z-]+)/([a-z0-9-]+)/([a-z0-9-]+)/([a-z0-9-]+)-(\d+)"')


def relocateme() -> list[dict]:
    jobs, seen = [], set()
    for term in RELOCATE_SEARCHES:
        r = requests.get("https://relocate.me/international-jobs", params={"query": term},
                         headers={**HEADERS, "Accept": "text/html"}, timeout=30)
        r.raise_for_status()
        for country, city, company, slug, job_id in _RELOC_LINK.findall(r.text):
            if job_id in seen or country in ("companies-hiring", "international-jobs", "blog"):
                continue
            seen.add(job_id)
            nice = lambda s: s.replace("-", " ").title()
            jobs.append(_job("relocateme", job_id, nice(slug), nice(company), f"{nice(city)}, {nice(country)}",
                             f"https://relocate.me/{country}/{city}/{company}/{slug}-{job_id}", "", None))
    return jobs


def add_relocateme_description(job: dict) -> None:
    r = requests.get(job["url"], headers={**HEADERS, "Accept": "text/html"}, timeout=30)
    r.raise_for_status()
    text = strip_html(re.sub(r"(?is)<(script|style|nav|footer|header)[^>]*>.*?</\1>", " ", r.text))
    job["description"] = text[:8000]
    if re.search(r"archive vacancy|position (is )?closed|no longer accepting", text, re.I):
        job["description"] += " [closed]"


# ---------------- Jobindex.dk (Denmark's biggest job board) - public RSS ----------------
JOBINDEX_SEARCHES = ["devops", "platform engineer", "site reliability engineer", "azure", "kubernetes", "cloud engineer"]


def _jobindex_rss(base: str, source: str) -> list[dict]:
    """Jobindex and IT-jobbank (same company, same RSS format): one feed per search word."""
    jobs, seen = [], set()
    for term in JOBINDEX_SEARCHES:
        r = requests.get(f"{base}/jobsoegning.rss", params={"q": term}, headers=HEADERS, timeout=30)
        r.raise_for_status()
        for item in ET.fromstring(r.content).iter("item"):
            text = lambda tag: (item.findtext(tag) or "").strip()
            link = text("link")
            if not link or link in seen:
                continue
            seen.add(link)
            title, _, company = text("title").rpartition(", ")
            try:
                posted = parsedate_to_datetime(text("pubDate")).isoformat()
            except (TypeError, ValueError):
                posted = None
            jobs.append(_job(source, link.rstrip("/").split("/")[-1], title or text("title"), company,
                             "Denmark", link, text("description"), posted))
    return jobs


def jobindex() -> list[dict]:
    return _jobindex_rss("https://www.jobindex.dk", "jobindex")


def itjobbank() -> list[dict]:
    """Computerworld IT-jobbank.dk - Denmark's IT-only job board (part of Jobindex, but many ads only here)."""
    return _jobindex_rss("https://www.it-jobbank.dk", "itjobbank")


# ---------------- The Hub (thehub.io) - Nordic startup / scale-up jobs - public JSON API ----------------
THEHUB_COUNTRIES = {"Denmark": "DK", "Sweden": "SE", "Finland": "FI"}
THEHUB_SEARCHES = ["devops", "platform engineer", "site reliability", "azure", "kubernetes", "cloud engineer"]


def thehub() -> list[dict]:
    from jobhunter.scoring import TARGET_COUNTRIES
    jobs, seen = [], set()
    for country, code in THEHUB_COUNTRIES.items():
        if country not in TARGET_COUNTRIES:
            continue
        for term in THEHUB_SEARCHES:
            for page in (1, 2):
                data = get_json("https://thehub.io/api/v2/jobsandfeatured",
                                params={"countryCode": code, "search": term, "page": page}) or {}
                block = data.get("jobs") or {}
                for j in block.get("docs") or []:
                    if j.get("id") in seen:
                        continue
                    seen.add(j.get("id"))
                    loc = j.get("location") or {}
                    where = ", ".join(x for x in (loc.get("locality"), loc.get("country") or country) if x)
                    if j.get("isRemote"):
                        where = f"Remote - {where}"
                    jobs.append(_job("thehub", j.get("id"), j.get("title"), (j.get("company") or {}).get("name"),
                                     where, f"https://thehub.io/jobs/{j.get('id')}", "", None, bool(j.get("isRemote"))))
                if page >= (block.get("pages") or 1):
                    break
    return jobs


# (Not used yet: EURES has no public API - its website endpoint answered 404. Kept for a future fix.)
# ---------------- EURES (EU's official job portal: public employment services of all EU countries) ----------------
EURES_URL = "https://europa.eu/eures/eures-apps/searchengine/page/jv-search/search"
EURES_COUNTRIES = ["nl", "ie", "fi", "lt", "dk", "de", "se", "ee"]


def eures() -> list[dict]:
    jobs, seen = [], set()
    session = requests.Session()
    session.headers.update({**HEADERS, "Accept": "application/json", "Content-Type": "application/json"})
    session.get("https://europa.eu/eures/portal/jv-se/search", timeout=30)        # sets the session cookies
    for term in ("devops", "platform engineer", "site reliability", "azure", "kubernetes"):
        body = {"resultsPerPage": 50, "page": 1, "sortSearch": "MOST_RECENT",
                "keywords": [{"keyword": term, "specificSearchCode": "EVERYWHERE"}],
                "publicationPeriod": "LAST_WEEK", "occupationUris": [], "skillUris": [], "requiredExperienceCodes": [],
                "positionScheduleCodes": [], "sectorCodes": [], "educationAndQualificationLevelCodes": [],
                "positionOfferingCodes": [], "locationCodes": EURES_COUNTRIES, "euresFlagCodes": [],
                "otherBenefitsCodes": [], "requiredLanguages": [], "minNumberPost": None, "sessionId": "jobhunter"}
        xsrf = session.cookies.get("XSRF-TOKEN")
        r = session.post(EURES_URL, json=body, timeout=30, headers={"X-XSRF-TOKEN": xsrf} if xsrf else None)
        r.raise_for_status()
        for jv in r.json().get("jvs", []):
            if jv.get("id") in seen:
                continue
            seen.add(jv.get("id"))
            places = []
            for country, cities in (jv.get("locationMap") or {}).items():
                names = {"NL": "Netherlands", "IE": "Ireland", "FI": "Finland", "LT": "Lithuania", "DK": "Denmark",
                         "DE": "Germany", "SE": "Sweden", "EE": "Estonia"}
                places.append(", ".join([*(c for c in (cities or []) if isinstance(c, str))][:2] + [names.get(country, country)]))
            jobs.append(_job("eures", jv.get("id"), jv.get("title"), (jv.get("employer") or {}).get("name"),
                             "; ".join(places), f"https://europa.eu/eures/portal/jv-se/jv-details/{jv.get('id')}?lang=en",
                             jv.get("description"), jv.get("creationDate")))
    return jobs


# ---------------- Jaabz.com: tech jobs that offer visa sponsorship / relocation (from the AIH list) ----------------
JAABZ_SEARCHES = ["devops", "platform engineer", "site reliability", "sre", "kubernetes", "azure", "cloud engineer"]
_JC = re.compile(r'<article class="jc[^"]*"(.*?)</article>', re.S)


def _jc(pattern, block):
    m = re.search(pattern, block, re.S)
    return strip_html(m.group(1)).strip() if m else ""


def _ago_to_iso(text: str) -> str | None:
    m = re.search(r"(\d+)\s*(m|h|d|w|mo)\w*\s+ago", text)
    if not m:
        return None
    n, unit = int(m.group(1)), m.group(2)
    minutes = n * {"m": 1, "h": 60, "d": 1440, "w": 10080, "mo": 43200}[unit]
    return datetime.fromtimestamp(datetime.now(timezone.utc).timestamp() - minutes * 60, timezone.utc).isoformat()


def jaabz() -> list[dict]:
    jobs, seen = [], set()
    for term in JAABZ_SEARCHES:
        r = requests.get("https://jaabz.com/jobs", params={"keyword": term},
                         headers={**HEADERS, "Accept": "text/html"}, timeout=30)
        r.raise_for_status()
        for block in _JC.findall(r.text):
            link = re.search(r'href="(https://jaabz\.com/jobs/(\d+)-[^"]+)"', block)
            if not link or link.group(2) in seen:
                continue
            seen.add(link.group(2))
            perks = " ".join(re.findall(r"jc-perk--(\w+)", block))           # visa / relocation / remote
            where = _jc(r'class="jc-where"[^>]*>(.*?)</p>', block)
            remote = "remote" in perks.split()
            jobs.append(_job("jaabz", link.group(2), _jc(r'class="jc-title"[^>]*>(.*?)</h3>', block),
                             _jc(r'class="jc-company"[^>]*>(.*?)</p>', block),
                             ("Remote - " if remote else "") + where, link.group(1),
                             "Perks: " + perks.replace("visa", "visa sponsorship").replace("relocation", "relocation support")
                             + ". Skills: " + ", ".join(strip_html(x) for x in re.findall(r"<li[^>]*>(.*?)</li>", block, re.S)),
                             _ago_to_iso(_jc(r'class="jc-facts"[^>]*>(.*?)</p>', block)), remote))
    return jobs


def add_jaabz_description(job: dict) -> None:
    r = requests.get(job["url"], headers={**HEADERS, "Accept": "text/html"}, timeout=30)
    r.raise_for_status()
    text = strip_html(re.sub(r"(?is)<(script|style|nav|footer|header)[^>]*>.*?</\1>", " ", r.text))
    job["description"] = (job.get("description", "") + "\n" + text)[:9000]


# ---------------- CVonline.lt (Lithuania's biggest job board) + CV.ee (Estonia) - search results are in the page JSON ----------------
CVONLINE_SITES = [("cvonline.lt", "Lithuania"), ("cv.ee", "Estonia")]
CVONLINE_SEARCHES = ["devops", "platform engineer", "site reliability", "kubernetes", "azure", "cloud engineer"]


def _next_data(html: str) -> dict:
    m = re.search(r'<script id="__NEXT_DATA__"[^>]*>(.*?)</script>', html, re.S)
    import json
    return json.loads(m.group(1)) if m else {}


def cvonline() -> list[dict]:
    jobs, seen = [], set()
    for site, country in CVONLINE_SITES:
        for term in CVONLINE_SEARCHES:
            r = requests.get(f"https://www.{site}/en/search", params={"keywords[0]": term},
                             headers={**HEADERS, "Accept": "text/html"}, timeout=30)
            if r.status_code != 200:
                continue
            props = (_next_data(r.text).get("props") or {}).get("pageProps") or {}
            towns = {t.get("id"): t.get("name") for t in ((props.get("initialReduxState") or {}).get("locations") or {}).get("towns") or []}
            for v in (props.get("searchResults") or {}).get("vacancies") or []:
                if v.get("id") in seen:
                    continue
                seen.add(v.get("id"))
                remote = bool(v.get("remoteWork"))
                where = ", ".join(filter(None, [towns.get(v.get("townId")), country]))
                langs = ", ".join(str(x) for x in (v.get("languages") or []))
                jobs.append(_job("cvonline", v.get("id"), v.get("positionTitle"), v.get("employerName"),
                                 ("Remote - " if remote else "") + where, f"https://www.{site}/en/vacancy/{v.get('id')}",
                                 f"{v.get('positionContent') or ''}\nLanguages: {langs}",
                                 v.get("renewedDate") or v.get("publishDate"), remote))
    return jobs


# ---------------- Jobly.fi (Finland) and Magnet.me (NL) - list pages with links; details read per job (JSON-LD) ----------------
def jobly() -> list[dict]:
    jobs, seen = [], set()
    for term in ["devops", "platform engineer", "site reliability", "kubernetes", "azure", "cloud engineer"]:
        r = requests.get("https://www.jobly.fi/tyopaikat", params={"search": term}, headers={**HEADERS, "Accept": "text/html"}, timeout=30)
        if r.status_code != 200:
            continue
        for href, job_id, title in re.findall(
                r'<a href="(https://www\.jobly\.fi/tyopaikka/[^"]+-(\d+))"[^>]*class="recruiter-job-link" title="([^"]+)"', r.text):
            if href in seen:
                continue
            seen.add(href)
            jobs.append(_job("jobly", job_id, title, "", "Finland", href, "", None))
    return jobs


def magnetme() -> list[dict]:
    jobs, seen = [], set()
    for term in ["devops", "platform engineer", "site reliability", "kubernetes", "cloud engineer"]:
        r = requests.get("https://magnet.me/en/opportunities", params={"query": term}, headers={**HEADERS, "Accept": "text/html"}, timeout=30)
        if r.status_code != 200:
            continue
        for path, job_id, slug in re.findall(r'href="(/en/opportunity/(\d+)/([a-z0-9-]+))"', r.text):
            if job_id in seen:
                continue
            seen.add(job_id)
            jobs.append(_job("magnetme", job_id, slug.replace("-", " ").title(), "", "Netherlands", "https://magnet.me" + path, "", None))
    return jobs
