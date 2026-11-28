"""
Step 9: the TRACKER - each strong new job becomes a GitHub Issue in your repo.

Why GitHub Issues?
    - free, private (your repo is private), works on your phone (GitHub app)
    - labels = status:  new -> applied -> interview -> offer / rejected
    - a GitHub Projects board can show them as a Kanban board (like Jira)

Needs GITHUB_TOKEN. Inside GitHub Actions this is provided AUTOMATICALLY (no setup).
On your laptop it is normally not set, so the robot simply skips this step.
"""

import json
import os
import re
from pathlib import Path

import requests

import time

from jobhunter import outreach, salary, skill_fit

API = "https://api.github.com"
REPO = os.environ.get("DATA_REPO") or os.environ.get("GITHUB_REPOSITORY", "")   # Actions sets this
AGGREGATORS = {"jobgether"}   # job boards that repost other employers' jobs
MAX_PER_AGGREGATOR = int(os.environ.get("MAX_PER_AGGREGATOR") or 0)   # reposting boards: off (Nov 2026 review)
# Recruitment agencies / staffing firms: their ads rarely lead to a sponsored hire, so they are skipped.
AGENCY = re.compile(r"recruit|staffing|personalberatung|personaldienst|headhunt|executive search|talent agency"
                    r"|\bhays\b|^randstad(?! global)|michael page|harvey nash|computer futures|nigel frank|jefferson frank"
                    r"|huxley|brightwater|morgan mckinley|\bcpl\b|fruition|haystack people|asta agency|it search"
                    r"|hamilton barnes|darwin recruitment|angeheuert|nordkind|iq staffing", re.I)
SKIP_AGENCIES = os.environ.get("SKIP_AGENCIES", "1") == "1"
# Some employers (banks, big corporates) hire ONLY through agencies. An agency ad is kept when it says the
# employer helps with visa / relocation (VISA_HELP words) - max MAX_AGENCY_PER_RUN per run, labelled via-agency.
MAX_AGENCY_PER_RUN = int(os.environ.get("MAX_AGENCY_PER_RUN") or 2)


def is_agency(job: dict) -> bool:
    return bool(AGENCY.search(job.get("company") or ""))


def agency_ok(job: dict) -> bool:
    """Agency ad worth sending: it mentions visa sponsorship / relocation help."""
    from jobhunter.scoring import VISA_HELP
    return bool(re.search(VISA_HELP, (job.get("description") or "").lower()))
STRONG_RANK = 60             # rank 60+          -> issue labelled "fit-strong"
STRETCH_RANK = 50            # rank 50-59        -> issue labelled "fit-stretch"
TARGET_PER_RUN = 6           # if a run gives fewer than 8 issues, top up with the next best jobs...
STRETCH_FLOOR = 50           # ...but never below rank 50 (below that it's noise)
MAX_ISSUES_PER_RUN = 10      # never flood your inbox
MAX_NON_ENGLISH_PER_RUN = int(os.environ.get("MAX_NON_ENGLISH") or 0)  # German/Dutch/Danish ads: off (Nov 2026 review)
MIN_FIT = int(os.environ.get("MIN_FIT") or 70)   # SKILL GATE: Gemini skill fit 70+ for ANY issue (was 55; raised Nov 2026)
STRONG_FIT = 70              # "fit-strong" needs rank 60+ AND skill fit 70+

LABELS = {   # name: colour (hex, no #)
    "job": "5319e7", "new": "0e8a16", "applied": "1d76db", "interview": "fbca04",
    "offer": "b60205", "rejected": "cccccc",
    "fit-strong": "0e8a16", "fit-stretch": "fbca04", "nomad-remote": "1d76db",
    "tailor": "c5def5", "tailored": "0052cc", "needs-review": "d93f0b",
    "ad-not-english": "f9d0c4", "via-agency": "c5def5",
}


def _headers():
    return {"Authorization": f"Bearer {os.environ['GITHUB_TOKEN']}",
            "Accept": "application/vnd.github+json"}


def _ensure_labels():
    """Create our labels once (GitHub answers 422 if a label already exists - that's fine)."""
    for name, colour in LABELS.items():
        requests.post(f"{API}/repos/{REPO}/labels", headers=_headers(), timeout=30,
                      json={"name": name, "color": colour})


def same_job_key(title: str, company: str) -> str:
    """'Senior SRE (f/m/x)' + 'kyndryl (Kyndryl Nederland B.V.)' -> 'seniorsrefmx|kyndryl' - the same job posted
    for several cities, or found again by another source, gets the same key."""
    company = re.split(r" \(", company or "")[0]
    norm = lambda t: re.sub(r"[^a-z0-9]", "", (t or "").lower())
    return f"{norm(title)}|{norm(company)[:12]}"


def _key_from_issue_title(issue_title: str) -> str | None:
    t = re.sub(r"^\[[^\]]*\]\s*", "", issue_title or "")
    if " – " not in t:
        return None
    job_title, company = t.rsplit(" – ", 1)
    return same_job_key(job_title, company)


def _existing_job_ids() -> set[str]:
    """Read ALL job issues (open + closed) and collect the hidden job-id marker from each body,
    plus a title|company key so the same job in another city / from another source isn't added twice."""
    ids, page = set(), 1
    while True:
        r = requests.get(f"{API}/repos/{REPO}/issues", headers=_headers(), timeout=30,
                         params={"labels": "job", "state": "all", "per_page": 100, "page": page})
        r.raise_for_status()
        batch = r.json()
        for issue in batch:
            ids.update(re.findall(r"<!-- job-id: (.+?) -->", issue.get("body") or ""))
            key = _key_from_issue_title(issue.get("title"))
            if key:
                ids.add(key)
        if len(batch) < 100:
            return ids
        page += 1


def _issue_text(job: dict) -> tuple[str, str, list[str]]:
    fit = job.get("fit") or {}
    where = job["location"] or ("Remote" if job.get("remote") else "")
    title = f"[{job['rank']}] {job['title']} – {job['company']} ({where})"[:250]

    lines = [f"**[Open the job ad]({job['url']})**", ""]
    if job.get("linkedin_url") and job["linkedin_url"] != job["url"]:
        lines[-1:] = [f"<sub>Seen on [LinkedIn]({job['linkedin_url']}) – the link above is the company's own application page.</sub>", ""]
    lines += [
             f"| | |", f"|---|---|",
             f"| Company | {job['company']} |",
             f"| Location | {where} |",
             f"| Rank | **{job['rank']}** (fit {fit.get('fit', '?')}, rules {job['score']}) |"]
    sal = job.get("salary")
    if sal:
        lines.append(f"| Salary | {sal['currency']} {sal['min'] or '?':,.0f} – {sal['max'] or '?':,.0f} per {sal['period']} |")
    lines.append(f"| Source | {job['source']} |")
    lines += ["", salary.markdown(job)]
    if job.get("nomad"):
        lines += ["", "🌍 **Nomad-visa remote job.** Fully remote and open to India/anywhere, so no work permit is needed. "
                  "With it you can apply for a digital nomad visa and live in Europe (Schengen = free travel to Wroclaw). "
                  "The pay must reach the visa minimum (gross): Spain €2,849/month (~₹36 lakh/yr), Croatia ~€3,622, "
                  "Portugal ~€3,680, Estonia ~€4,500. The employer must be based OUTSIDE the country you move to, "
                  "and must allow you to work from abroad - ask before applying."]
    lines += ["", f"**Fit:** {fit.get('verdict', '')}",
              f"**Matched:** {', '.join(fit.get('matched', []))}",
              f"**Missing:** {', '.join(fit.get('missing', [])) or '–'}",
              "", f"<sub>Rule points: {', '.join(job['reasons'])}</sub>",
              "", "---",
              "**Want a tailored resume?** Add the label `tailor` → in ~3 min a comment with the ATS score and the PDF appears here.",
              "Status: change the label `new` → `applied` → `interview` → `offer` / `rejected`. Close when done.",
              f"<!-- job-id: {job['id']} -->"]
    text = (job.get("description") or "").strip()
    if len(text) > 300:
        # Full ad text kept in the issue itself (folded), so the tailor and the Claude tasks never need to
        # open the job page again. GitHub allows 65,536 characters per issue body; 12,000 is plenty for an ad.
        lines[-1:-1] = ["", "<details><summary>Full job ad text</summary>", "", "<!-- job-text -->",
                        text[:12000], "<!-- /job-text -->", "</details>", ""]

    strong = job["rank"] >= STRONG_RANK and fit.get("fit", 0) >= STRONG_FIT
    labels = ["job", "new", "fit-strong" if strong else "fit-stretch"]
    if job.get("nomad"):
        labels.append("nomad-remote")
    if is_agency(job):
        labels.append("via-agency")   # posted by a recruiter: ask them who the employer is and whether they sponsor
    if job.get("ad_language") not in (None, "", "english"):
        labels.append("ad-not-english")   # the ad is not in English: check the language rule before applying
    return title, "\n".join(lines), labels


JOB_STORE = Path("data/job_store.json")   # full job text for every issue -> used by the tailor


def remember_jobs(jobs: list[dict]) -> None:
    store = json.loads(JOB_STORE.read_text(encoding="utf-8")) if JOB_STORE.exists() else {}
    for job in jobs:
        store[job["id"]] = {k: job.get(k) for k in ("id", "title", "company", "location", "url", "description", "source")}
    JOB_STORE.parent.mkdir(exist_ok=True)
    JOB_STORE.write_text(json.dumps(store, ensure_ascii=False), encoding="utf-8")


def pick(jobs: list[dict], already: set[str]) -> list[dict]:
    """
    Choose which jobs become issues this run:
      0. only jobs whose Gemini SKILL FIT is MIN_FIT (70)+, not from a recruitment agency, - titles and keywords can't carry a weak match
      1. every job with rank >= STRETCH_RANK (50)                      (strong + stretch)
      2. if that's fewer than TARGET_PER_RUN (8), add the next best jobs down to STRETCH_FLOOR (45)
    Jobs that already have an issue are ignored. Best first, max MAX_ISSUES_PER_RUN.
    """
    candidates, seen = [], set(already)
    for j in sorted((j for j in jobs if (j.get("fit") or {}).get("fit", 0) >= MIN_FIT), key=lambda j: j["rank"], reverse=True):
        if SKIP_AGENCIES and is_agency(j) and not agency_ok(j):
            continue
        key = same_job_key(j["title"], j["company"])
        if j["id"] in seen or key in seen:
            continue
        seen.add(key)
        candidates.append(j)
    chosen = [j for j in candidates if j["rank"] >= STRETCH_RANK]
    if len(chosen) < TARGET_PER_RUN:
        extra = [j for j in candidates if STRETCH_FLOOR <= j["rank"] < STRETCH_RANK]
        chosen += extra[:TARGET_PER_RUN - len(chosen)]
    chosen = _cap_non_english(chosen)
    agency = [j for j in chosen if is_agency(j)][:MAX_AGENCY_PER_RUN]
    chosen = [j for j in chosen if not is_agency(j) or j in agency]
    return _cap_aggregators(chosen)[:MAX_ISSUES_PER_RUN]


def _cap_aggregators(jobs: list[dict]) -> list[dict]:
    """Aggregators post the same employer's jobs many times over. Keep at most MAX_PER_AGGREGATOR per run;
    the rest stay judged and become issues in a later run (they are not marked as done)."""
    count, kept = {}, []
    for j in jobs:
        company = (j.get("company") or "").strip().lower()
        if company in AGGREGATORS:
            if count.get(company, 0) >= MAX_PER_AGGREGATOR:
                continue
            count[company] = count.get(company, 0) + 1
        kept.append(j)
    return kept


def _cap_non_english(jobs: list[dict]) -> list[dict]:
    """Keep at most MAX_NON_ENGLISH_PER_RUN jobs whose ad is not in English (best first)."""
    out, non_english = [], 0
    for j in jobs:
        if j.get("ad_language") not in (None, "", "english"):
            if non_english >= MAX_NON_ENGLISH_PER_RUN:
                continue
            non_english += 1
        out.append(j)
    return out


def publish(jobs: list[dict]) -> None:
    """Create one issue per chosen job (never twice for the same job)."""
    if not os.environ.get("GITHUB_TOKEN"):
        return   # on your laptop: nothing to do

    _ensure_labels()
    chosen = pick(jobs, _existing_job_ids())
    if not chosen:
        print("Tracker: no new matches for GitHub Issues this time.")
        return

    created, auto_tailor = 0, []
    for job in chosen:
        title, body, labels = _issue_text(job)
        extra = outreach.markdown(job, outreach.draft(job))   # why-fit, cover letter, recruiter email
        if extra:
            body = body.replace("\n---\n", f"\n{extra}\n\n---\n", 1)
            time.sleep(skill_fit.PAUSE_SECONDS)
        r = requests.post(f"{API}/repos/{REPO}/issues", headers=_headers(), timeout=30,
                          json={"title": title, "body": body, "labels": labels})
        if r.ok:
            created += 1
            print(f"   issue #{r.json()['number']} ({labels[-1]}): {title}")
            if "fit-strong" in labels:   # nomad-remote is appended last, so labels[-1] is not always the fit label
                auto_tailor.append(str(r.json()["number"]))
        else:
            print(f"   ! could not create issue: {r.status_code} {r.text[:150]}")
    remember_jobs(chosen)
    # strong matches get a tailored resume automatically (the workflow reads this file next)
    Path("data").mkdir(exist_ok=True)
    Path("data/auto_tailor.txt").write_text(" ".join(auto_tailor), encoding="utf-8")
    print(f"Tracker: created {created} GitHub issue(s); {len(auto_tailor)} will be tailored automatically.")
