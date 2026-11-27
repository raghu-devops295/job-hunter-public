"""
DETECT HIRING SYSTEMS behind company careers pages.

Many big "own" careers pages are only a front for Greenhouse, Lever, Workday, SmartRecruiters...
For every URL in lists/*_careers_urls.txt this opens the page once, looks in the HTML (and where it
redirected to) for a hiring system the robot can read, checks that it really answers, and adds it
to jobhunter/companies.py. Pages that block bots or need JavaScript are simply skipped.

Run:   py tools\\detect_ats.py            (show what it finds)
       py tools\\detect_ats.py --write    (also add them to jobhunter/companies.py)
"""

import argparse
import re
import sys
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from jobhunter import companies                                    # noqa: E402
from jobhunter.scoring import MY_ROLE_IN_TITLE                     # noqa: E402
from jobhunter.sources.common import HEADERS                       # noqa: E402
from jobhunter.sources.company_boards import FETCHERS              # noqa: E402
from jobhunter.sources import enterprise                           # noqa: E402
from urllib.parse import urlparse                                  # noqa: E402

PATTERNS = [   # (system, regex) - group(1) is the company slug the robot needs
    ("greenhouse", r"(?:boards|job-boards)(?:\.eu)?\.greenhouse\.io/(?:embed/job_board(?:/js)?\?for=)?([a-z0-9_-]+)"),
    ("greenhouse", r"boards-api\.greenhouse\.io/v1/boards/([a-z0-9_-]+)"),
    ("lever", r"(?:jobs|api)(?:\.eu)?\.lever\.co/(?:v0/postings/)?([a-z0-9._-]+)"),
    ("ashby", r"jobs\.ashbyhq\.com/([a-z0-9._%-]+)"),
    ("ashby", r"api\.ashbyhq\.com/posting-api/job-board/([a-z0-9._-]+)"),
    ("recruitee", r"([a-z0-9-]+)\.recruitee\.com"),
    ("smartrecruiters", r"(?:careers|jobs)\.smartrecruiters\.com/([a-z0-9_-]+)"),
    ("smartrecruiters", r"api\.smartrecruiters\.com/v1/companies/([a-z0-9_-]+)"),
    ("personio", r"([a-z0-9-]+)\.jobs\.personio\.(?:de|com)"),
    ("workable", r"apply\.workable\.com/([a-z0-9_-]+)"),
    ("bamboohr", r"([a-z0-9-]+)\.bamboohr\.com"),
    ("teamtailor", r"([a-z0-9-]+)\.teamtailor\.com"),
    ("join", r"join\.com/companies/([a-z0-9_-]+)"),
]
WORKDAY = r"([a-z0-9-]+)\.(wd\d+)\.myworkdayjobs\.com/(?:[a-z]{2}-[A-Z]{2}/)?([A-Za-z0-9_-]+)"
NOT_SLUGS = {"embed", "js", "api", "v1", "jobs", "www", "careers", "static", "assets", "cdn", "v0", "widget"}


def urls() -> list[str]:
    out = []
    for f in sorted((ROOT / "lists").glob("*_careers_urls.txt")):
        for line in f.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line and not line.startswith("#"):
                out.append(line if line.startswith("http") else "https://" + line)
    return list(dict.fromkeys(out))


def detect(url: str) -> list[tuple]:
    try:
        r = requests.get(url, headers={**HEADERS, "Accept": "text/html"}, timeout=15, allow_redirects=True)
    except Exception:
        return []
    if r.status_code >= 400:
        return []
    html = r.url + " " + r.text[:600_000]
    found = set()
    for system, pattern in PATTERNS:
        for slug in re.findall(pattern, html, re.I):
            slug = slug.strip(".") if system == "smartrecruiters" else slug.lower().strip(".")
            if slug and slug not in NOT_SLUGS:
                found.add((system, slug))
    host = urlparse(r.url).netloc.lower()
    if re.search(r"phenompeople|cdn\.phenom|phApp", html, re.I):
        found.add(("phenom", host))
    if re.search(r"successfactors|career\d*\.sapsf|rmkcdn|/talentcommunity/", html, re.I):
        found.add(("successfactors", host))
    for tenant, wd, site in re.findall(WORKDAY, html):
        if site.lower() not in ("wday", "cxs"):
            found.add(("workday", (tenant.lower(), wd.lower(), site)))
    return sorted(found, key=str)


def check(item):
    """Does the hiring system really answer with jobs? -> (system, slug, total, devops) or None."""
    system, slug = item
    try:
        if system == "workday":
            from jobhunter.sources import workday
            jobs, _ = workday.fetch_all([slug])
        elif system in enterprise.FETCHERS:
            jobs = enterprise.FETCHERS[system](slug)
        else:
            jobs = FETCHERS[system](slug)
    except Exception:
        return None
    if not jobs:
        return None
    devops = sum(bool(re.search(MY_ROLE_IN_TITLE, j["title"].lower())) for j in jobs)
    from jobhunter.scoring import find_country
    in_my_countries = sum(bool(find_country(j)) for j in jobs)
    return system, slug, len(jobs), devops if devops else (0.5 if in_my_countries >= 2 else 0)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--write", action="store_true", help="add found companies to jobhunter/companies.py")
    ap.add_argument("--urls", nargs="*", help="only open these careers pages (e.g. from today's job alerts)")
    args = ap.parse_args()

    pages = [u if u.startswith("http") else "https://" + u for u in args.urls] if args.urls else urls()
    print(f"Opening {len(pages)} careers pages...")
    with ThreadPoolExecutor(max_workers=16) as pool:
        hits = [h for page_hits in pool.map(detect, pages) for h in page_hits]
    have = {"workday": {tuple(x) for x in companies.WORKDAY}}
    for system in list(FETCHERS) + list(enterprise.FETCHERS):
        have[system] = set(getattr(companies, system.upper(), []))
    new = sorted({h for h in hits if h[1] not in have.get(h[0], set())}, key=str)
    print(f"Hiring systems found on {len({h for h in hits})} links, {len(new)} not in companies.py yet. Checking them...")

    with ThreadPoolExecutor(max_workers=12) as pool:
        results = [r for r in pool.map(check, new) if r]
    for system, slug, total, devops in sorted(results, key=lambda r: -r[3]):
        print(f"  FOUND  {system:16} {str(slug):40} {total:4} jobs, {devops:3} DevOps/Platform/Cloud titles")

    if not args.write:
        return
    path = ROOT / "jobhunter" / "companies.py"
    text = path.read_text(encoding="utf-8")
    added = 0
    by_system = defaultdict(list)
    for system, slug, _total, devops in results:
        if devops > 0:
            by_system[system].append(slug)
    for system, slugs in by_system.items():
        block = re.search(rf"^{system.upper()} = \[(.*?)^\]", text, re.S | re.M)
        if not block:
            continue
        if system == "workday":
            lines = "".join(f'    ("{t}", "{w}", "{s}"),     # added by detect_ats\n' for t, w, s in slugs)
        else:
            lines = "".join(f'    "{s}",            # added by detect_ats\n' for s in slugs if f'"{s}"' not in block.group(1))
        if lines:
            text = text[:block.end() - 1] + lines + text[block.end() - 1:]
            added += lines.count("\n")
    path.write_text(text, encoding="utf-8")
    print(f"\nAdded {added} companies (with DevOps-type jobs right now) to jobhunter/companies.py")


if __name__ == "__main__":
    main()
