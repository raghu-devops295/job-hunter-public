"""
Add jobs the robot can't scan (LinkedIn-only, Workday...) to the tracker by hand.
Input: a JSON file with a list of {"title", "company", "location", "url", "description", "why"}.
Each becomes an issue (labels: job, new, fit-strong, from-email) with the job text inside it,
then gets the `tailor` label -> tailored resume, cover letter, hiring message (GitHub workflow).

    GITHUB_TOKEN=... python tools/add_email_job.py jobs.json
"""
import json
import sys
from pathlib import Path

import requests

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from jobhunter import filters, salary, tracker   # noqa: E402

API, REPO, H = tracker.API, tracker.REPO, tracker._headers()
requests.post(f"{API}/repos/{REPO}/labels", headers=H, json={"name": "from-email", "color": "d4c5f9"}, timeout=30)
requests.post(f"{API}/repos/{REPO}/labels", headers=H, json={"name": "needs-text", "color": "fbca04"}, timeout=30)
existing = tracker._existing_job_ids()
MIN_TEXT = 1500   # characters of job text needed before auto-tailoring

for job in json.loads(Path(sys.argv[1]).read_text(encoding="utf-8")):
    job.setdefault("source", "email")
    reason = filters.location_dealbreaker(job) or filters.sponsor_dealbreaker(job)   # same location + NL sponsor rules as the robot
    if reason:
        print(f"   skipped (location): {job['title']} – {job['company']}: {reason}")
        continue
    job_id = f"email-{job['url'].rstrip('/').split('/')[-1]}"
    if job_id in existing or tracker.same_job_key(job["title"], job["company"]) in existing:
        print(f"   already tracked: {job['title']} – {job['company']}")
        continue
    body = "\n".join([
        f"**[Open the job ad]({job['url']})**", "",
        "| | |", "|---|---|",
        f"| Company | {job['company']} |", f"| Location | {job['location']} |",
        "| Source | job-alert email (added by hand) |", "",
        salary.markdown(job), "",
        f"**Why it's a fit:** {job.get('why', '')}", "",
        "---",
        "Status: change the label `new` → `applied` → `interview` → `offer` / `rejected`. Close when done.",
        "", "<details><summary>Job ad text (used for tailoring)</summary>", "",
        "<!-- job-text -->", job["description"].strip(), "<!-- /job-text -->", "</details>",
        f"<!-- job-id: {job_id} -->"])
    title = f"[email] {job['title']} – {job['company']} ({job['location']})"[:250]
    r = requests.post(f"{API}/repos/{REPO}/issues", headers=H, timeout=30,
                      json={"title": title, "body": body, "labels": ["job", "new", "fit-strong", "from-email"]})
    if not r.ok:
        print(f"   ! {r.status_code} {r.text[:150]}")
        continue
    n = r.json()["number"]
    if len(job["description"].strip()) >= MIN_TEXT:
        requests.post(f"{API}/repos/{REPO}/issues/{n}/labels", headers=H, json={"labels": ["tailor"]}, timeout=30)
        print(f"   issue #{n}: {title}")
    else:   # too little job text -> tailoring gives a poor resume; paste the full ad, then add `tailor`
        requests.post(f"{API}/repos/{REPO}/issues/{n}/labels", headers=H, json={"labels": ["needs-text"]}, timeout=30)
        print(f"   issue #{n}: {title}  (short job text -> labelled needs-text, not tailored)")
