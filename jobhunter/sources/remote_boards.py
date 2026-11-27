"""
Remote-job boards with free, key-less JSON feeds.

    Remotive   https://remotive.com/api/remote-jobs?search=devops
    RemoteOK   https://remoteok.com/api                       (all jobs; the title gate keeps ours)
    Himalayas  https://himalayas.app/jobs/api?q=devops
    Jobicy     https://jobicy.com/api/v2/remote-jobs?tag=devops

The location filter (filters.py) then drops "Remote - US only" etc. and keeps Remote / Europe / worldwide.
Each board is wrapped in try/except: if one is down, the others still work.
"""

from jobhunter.sources.common import get_json, strip_html

SEARCHES = ["devops", "platform engineer", "site reliability", "azure", "kubernetes", "cloud engineer"]


def _job(source, raw_id, title, company, location, url, description, posted_at):
    return {"id": f"{source}:{raw_id}", "source": source, "title": title or "", "company": company or "",
            "location": location or "Remote", "remote": True, "url": url or "",
            "description": strip_html(description or ""), "posted_at": posted_at}


def remotive() -> list[dict]:
    jobs = []
    for term in SEARCHES:
        data = get_json("https://remotive.com/api/remote-jobs", params={"search": term, "limit": 100}) or {}
        jobs += [_job("remotive", j.get("id"), j.get("title"), j.get("company_name"),
                      "Remote - " + (j.get("candidate_required_location") or "Worldwide"), j.get("url"),
                      j.get("description"), j.get("publication_date")) for j in data.get("jobs", [])]
    return jobs


def remoteok() -> list[dict]:
    data = get_json("https://remoteok.com/api") or []
    return [_job("remoteok", j.get("id"), j.get("position"), j.get("company"),
                 "Remote - " + (j.get("location") or "Worldwide"), j.get("url"), j.get("description"), j.get("date"))
            for j in (data[1:] if isinstance(data, list) else [])]          # item 0 is a legal notice


def himalayas() -> list[dict]:
    jobs = []
    for term in SEARCHES:
        data = get_json("https://himalayas.app/jobs/api", params={"q": term, "limit": 100}) or {}
        for j in data.get("jobs", []):
            where = ", ".join(j.get("locationRestrictions") or []) or "Worldwide"
            jobs.append(_job("himalayas", j.get("guid") or j.get("applicationLink"), j.get("title"),
                             j.get("companyName"), "Remote - " + where, j.get("applicationLink"),
                             j.get("description"), j.get("pubDate")))
    return jobs


def jobicy() -> list[dict]:
    jobs = []
    for tag in ("devops", "kubernetes", "azure", "sre"):
        data = get_json("https://jobicy.com/api/v2/remote-jobs", params={"count": 50, "tag": tag}) or {}
        jobs += [_job("jobicy", j.get("id"), j.get("jobTitle"), j.get("companyName"),
                      "Remote - " + (j.get("jobGeo") or "Worldwide"), j.get("url"), j.get("jobDescription"),
                      j.get("pubDate")) for j in data.get("jobs", [])]
    return jobs


def fetch_all() -> list[dict]:
    jobs = []
    for name, fn in (("Remotive", remotive), ("RemoteOK", remoteok), ("Himalayas", himalayas), ("Jobicy", jobicy)):
        try:
            found = fn()
            print(f"    {name}: {len(found)} jobs")
            jobs += found
        except Exception as error:
            print(f"    ! {name} failed: {error}")
    return jobs
