"""
INDIA HUNTER - its own scheduled run, kept apart from the Europe robot (run.py).

Rules (from you):
  - Only jobs in India, or fully remote jobs open to India.
  - Only the last 7 days.
  - Salary NOT mentioned  -> accept (marked "salary not shown").
  - Salary mentioned      -> accept only if above 40 LPA (40 lakh rupees a year).
    Salary in another currency cannot be compared safely -> not accepted, but listed in the reason.
  - Every accepted job becomes a GitHub issue with the label `india` (never `job`, so the Europe run ignores it).

Sources:
  - Adzuna India  (needs the repository secrets ADZUNA_APP_ID and ADZUNA_APP_KEY; free sign-up at developer.adzuna.com)
  - Remotive     (remote jobs, no key; kept only if India is an allowed location)
"""

import json
import os
import re
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import requests

from jobhunter.sources.common import HEADERS
from jobhunter.scoring import MY_ROLE_IN_TITLE

REPO = os.environ.get("DATA_REPO") or os.environ.get("GITHUB_REPOSITORY", "")
API = "https://api.github.com"
SEEN_FILE = Path("data/india_seen.json")
MIN_LPA = 40.0
MAX_AGE_DAYS = 7
SEARCHES = ["devops engineer", "platform engineer", "site reliability engineer", "cloud engineer azure", "kubernetes engineer"]


# ---------------------------------------------------------------- salary rule

def to_lpa(amount: float) -> float:
    """Rupees a year -> lakh per annum (LPA)."""
    return amount / 100_000


def salary_decision(salary_text: str | None, amount_max: float | None = None, currency: str = "INR") -> tuple[bool, str]:
    """Returns (accept, reason). Implements: no salary -> accept; salary -> accept only if above 40 LPA."""
    if amount_max:                                   # structured number from the source
        if currency != "INR":
            return False, f"salary in {currency} (cannot compare safely to 40 LPA)"
        lpa = to_lpa(amount_max)
        return (lpa > MIN_LPA), f"salary {lpa:.1f} LPA ({'above' if lpa > MIN_LPA else 'not above'} 40 LPA)"
    if not salary_text or not salary_text.strip():
        return True, "salary not shown"
    text = salary_text.replace(",", "")
    if re.search(r"₹|inr|rs\.?|rupee|lpa|lakh|lac", text, re.I):
        numbers = [float(n) for n in re.findall(r"\d+(?:\.\d+)?", text)]
        if not numbers:
            return True, "salary shown but not readable - check the ad"
        top = max(numbers)
        lpa = top if re.search(r"lpa|lakh|lac", text, re.I) else to_lpa(top)
        return (lpa > MIN_LPA), f"salary up to {lpa:.1f} LPA ({'above' if lpa > MIN_LPA else 'not above'} 40 LPA)"
    return False, f"salary in another currency ({salary_text.strip()[:40]}) - cannot compare safely"


# ---------------------------------------------------------------- sources

def adzuna_jobs() -> list[dict]:
    app_id, app_key = os.environ.get("ADZUNA_APP_ID"), os.environ.get("ADZUNA_APP_KEY")
    if not (app_id and app_key):
        print("   (Adzuna skipped: ADZUNA_APP_ID / ADZUNA_APP_KEY not set)")
        return []
    jobs = []
    for what in SEARCHES:
        r = requests.get("https://api.adzuna.com/v1/api/jobs/in/search/1", headers=HEADERS, timeout=30, params={
            "app_id": app_id, "app_key": app_key, "what": what, "results_per_page": 50,
            "max_days_old": MAX_AGE_DAYS, "content-type": "application/json"})
        if not r.ok:
            print(f"   ! Adzuna '{what}': HTTP {r.status_code}")
            continue
        for item in r.json().get("results", []):
            jobs.append({
                "source": "adzuna-in", "id": f"adzuna-{item.get('id')}",
                "title": item.get("title", ""), "company": (item.get("company") or {}).get("display_name", ""),
                "location": (item.get("location") or {}).get("display_name", "India"),
                "url": item.get("redirect_url", ""), "description": item.get("description", ""),
                "posted": (item.get("created") or "")[:10],
                "amount_max": item.get("salary_max") if item.get("salary_is_predicted") != "1" else None,
                "salary_text": "",
            })
    return jobs


def remotive_jobs() -> list[dict]:
    r = requests.get("https://remotive.com/api/remote-jobs", headers=HEADERS, timeout=30,
                     params={"category": "devops-sysadmin"})
    if not r.ok:
        print(f"   ! Remotive: HTTP {r.status_code}")
        return []
    cutoff = datetime.now(timezone.utc) - timedelta(days=MAX_AGE_DAYS)
    jobs = []
    for item in r.json().get("jobs", []):
        posted = datetime.fromisoformat(item["publication_date"].replace("Z", "+00:00"))
        where = item.get("candidate_required_location", "")
        if posted < cutoff or not re.search(r"india|asia|worldwide|anywhere|global", where, re.I):
            continue
        jobs.append({
            "source": "remotive", "id": f"remotive-{item['id']}", "title": item["title"],
            "company": item.get("company_name", ""), "location": f"Remote ({where})", "url": item["url"],
            "description": re.sub(r"<[^>]+>", " ", item.get("description", "")), "posted": posted.date().isoformat(),
            "amount_max": None, "salary_text": item.get("salary", ""),
        })
    return jobs


# ---------------------------------------------------------------- GitHub issues

def _gh_headers() -> dict:
    return {"Authorization": f"Bearer {os.environ['GITHUB_TOKEN']}", "Accept": "application/vnd.github+json"}


def norm(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", (text or "").lower())


def job_key(title: str, company: str) -> str:
    """Same job from two sources = same key (title + company), whatever the source id is."""
    return f"{norm(title)}|{norm(company)}"


def existing_ids() -> set[str]:
    """Every id marker AND every title|company key of the india issues already on GitHub."""
    ids, page = set(), 1
    while True:
        r = requests.get(f"{API}/repos/{REPO}/issues", headers=_gh_headers(), timeout=30,
                         params={"labels": "india", "state": "all", "per_page": 100, "page": page})
        r.raise_for_status()
        batch = r.json()
        for issue in batch:
            ids.update(re.findall(r"<!-- india-id: (.+?) -->", issue.get("body") or ""))
            m = re.match(r"\[india\]\s*(.+?)\s+[–-]\s+(.+?)\s*\(", issue.get("title") or "")
            if m:
                ids.add(job_key(m.group(1), m.group(2)))
        if len(batch) < 100:
            return ids
        page += 1


def ensure_label() -> None:
    requests.post(f"{API}/repos/{REPO}/labels", headers=_gh_headers(), timeout=30,
                  json={"name": "india", "color": "0e8a16", "description": "India job search run"})


def issue_body(job: dict, reason: str) -> str:
    return (f"**[Open the job ad]({job['url']})**\n\n"
            f"| | |\n|---|---|\n| Company | {job['company']} |\n| Location | {job['location']} |\n"
            f"| Posted | {job['posted']} |\n| Source | {job['source']} |\n\n"
            f"**Salary:** {reason}\n\n"
            "Apply yourself: this run only lists jobs. Nothing is sent or applied for you.\n\n"
            f"<!-- india-id: {job['id']} -->\n")


def main() -> None:
    if not os.environ.get("GITHUB_TOKEN"):
        sys.exit("GITHUB_TOKEN is not set.")
    jobs = adzuna_jobs() + remotive_jobs()
    print(f"{len(jobs)} India-related jobs from the sources.")
    jobs = [j for j in jobs if re.search(MY_ROLE_IN_TITLE, j["title"].lower())]
    seen = existing_ids()
    ensure_label()
    created = skipped_salary = 0
    for job in jobs:
        if job["id"] in seen or job_key(job["title"], job["company"]) in seen:
            continue
        accept, reason = salary_decision(job["salary_text"], job["amount_max"],
                                         currency="INR" if job["source"] == "adzuna-in" else "OTHER")
        if not accept:
            skipped_salary += 1
            continue
        title = f"[india] {job['title']} – {job['company']} ({job['location']})"
        r = requests.post(f"{API}/repos/{REPO}/issues", headers=_gh_headers(), timeout=30,
                          json={"title": title, "body": issue_body(job, reason), "labels": ["india", "new"]})
        if r.ok:
            created += 1
            seen.add(job_key(job["title"], job["company"]))
    print(f"created {created} issues; skipped {skipped_salary} for salary (not above 40 LPA or not comparable).")


if __name__ == "__main__":
    main()
