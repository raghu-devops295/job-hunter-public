"""
LinkedIn jobs via Apify (optional source).

Your job-alert emails only show the LinkedIn jobs LinkedIn chooses to email you. This source asks an
Apify "Actor" (a ready-made scraper run in Apify's cloud) for PUBLIC LinkedIn job listings - no login,
no cookies, so your own LinkedIn account is never used or put at risk.

Actor: curious_coder/linkedin-jobs-scraper (pay per result, about $1 per 1,000 jobs).

FOCUS (most results go to the role you want most). Exact-phrase searches, jobs from the last 24 hours:
                                  top 3 countries   each other country
    "Azure DevOps"                     13                  5
    "DevOps Engineer"                   8                  3
    "Platform Engineer"                 8                  0
Worst case 3x(13+8+8) + 7x(5+3) = 143 jobs/day = ~$4.30/month, inside Apify's $5 free monthly usage.
Results whose TITLE is not an Azure/DevOps/Platform/SRE/Cloud engineering role are dropped (see TITLE_OK).
Repo variable APIFY_COUNTRIES (e.g. "Netherlands,Germany") limits the search to those countries only.

Turned OFF unless the GitHub secret APIFY_TOKEN exists. Skipped with a warning if Apify fails.
"""
import os
import re
from urllib.parse import quote

import requests

from jobhunter.sources.common import strip_html

ACTOR = os.environ.get("APIFY_ACTOR", "curious_coder~linkedin-jobs-scraper")
# (exact phrase, jobs per search in top-3 countries, jobs per search in other countries) - best first
SEARCHES = [('"Azure DevOps"', 13, 5),
            ('"DevOps Engineer"', 8, 2),
            ('"Platform Engineer"', 8, 0)]

# Keep only real engineering titles in your field; drop the rest (sales, data, support, developers...).
TITLE_OK = re.compile(r"devops|dev ops|platform engineer|site reliability|\bsre\b|azure|cloud (platform |infrastructure )?engineer"
                      r"|kubernetes|infrastructure engineer|cloud architect", re.I)
TITLE_BAD = re.compile(r"sales|account|support|analyst|data (engineer|scientist)|scientist|front.?end|back.?end|full.?stack"
                       r"|java\b|\.net\b|developer|recruit|intern\b|werkstudent|student|trainee|junior|manager(?! .*engineer)"
                       r"|machine learning|\bml\b|ai engineer|security analyst|tester|\bqa\b|sap\b", re.I)


def title_ok(title: str) -> bool:
    return bool(TITLE_OK.search(title or "")) and not TITLE_BAD.search(title or "")


TOP_COUNTRIES = 3   # these get the bigger per-search limit


def apify_countries() -> tuple[list[str], list[str]]:
    """(top countries, other countries) to search on LinkedIn."""
    chosen = [c.strip() for c in (os.environ.get("APIFY_COUNTRIES") or "").split(",") if c.strip()]
    if chosen:
        return chosen, []
    from jobhunter.scoring import TARGET_COUNTRIES
    return TARGET_COUNTRIES[:TOP_COUNTRIES], TARGET_COUNTRIES[TOP_COUNTRIES:]


_TRACKING = re.compile(r"[?&](utm_[a-z]+|src|source|ref|trk|refId|trackingId|gh_src|lever-source(%5B%5D)?)=[^&]*", re.I)


def company_apply_url(url: str | None) -> str:
    """The employer's own apply link from LinkedIn ("Apply on company website"), without tracking bits.
    Empty for Easy Apply jobs (they stay on LinkedIn)."""
    url = (url or "").strip()
    if not url.startswith("http") or "linkedin.com" in url:
        return ""
    url = _TRACKING.sub("", url)
    return url.replace("?&", "?").rstrip("?&")


def search_urls(countries: list[str], keyword: str) -> list[str]:
    # f_TPR=r86400 = posted in the last 24 hours (the robot runs once a day)
    return [f"https://www.linkedin.com/jobs/search/?keywords={quote(keyword)}&location={quote(c)}&f_TPR=r86400"
            for c in countries]


def fetch() -> list[dict]:
    token = os.environ.get("APIFY_TOKEN")
    if not token:
        print("    LinkedIn via Apify: skipped (no APIFY_TOKEN secret)")
        return []
    top, other = apify_countries()
    jobs, report = [], []
    for keyword, top_limit, other_limit in SEARCHES:
        for countries, limit in ((top, top_limit), (other, other_limit)):
            if countries and limit > 0:
                found = _run(token, search_urls(countries, keyword), limit)
                kept = [j for j in found if title_ok(j["title"])]
                jobs += kept
                report.append(f"{keyword} x{len(countries)} countries: {len(kept)}/{len(found)} kept")
    print(f"    LinkedIn via Apify: {len(jobs)} jobs kept ({'; '.join(report)})")
    return jobs


def _run(token: str, urls: list[str], limit: int) -> list[dict]:
    run_input = {"urls": urls, "limitPerSource": limit, "scrapeCompany": False, "autoConvertToAiSearch": True}
    response = requests.post(f"https://api.apify.com/v2/acts/{ACTOR}/run-sync-get-dataset-items",
                             headers={"Authorization": f"Bearer {token}"}, json=run_input, timeout=600)
    response.raise_for_status()
    jobs = []
    for item in response.json():
        raw_id = item.get("id") or (item.get("link") or "").rstrip("/").split("/")[-1].split("?")[0]
        if not raw_id or not item.get("title"):
            continue
        remote = bool(item.get("workRemoteAllowed")) or "remote" in str(item.get("workplaceTypes") or "").lower()
        linkedin_url = (item.get("link") or "").split("?")[0]
        apply_url = company_apply_url(item.get("applyUrl"))
        jobs.append({"id": f"linkedin:{raw_id}", "source": "linkedin", "title": item.get("title") or "",
                     "company": item.get("companyName") or "", "location": item.get("location") or "",
                     # the company's own application page when LinkedIn sends you there, else the LinkedIn ad
                     "remote": remote, "url": apply_url or linkedin_url, "linkedin_url": linkedin_url,
                     "careers_url": apply_url,
                     "description": strip_html(item.get("descriptionText") or item.get("descriptionHtml") or ""),
                     "posted_at": item.get("postedAtTimestamp") or item.get("postedAt")})
    return jobs
