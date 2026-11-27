"""
One-off helper: add the "💶 Salary to ask" block to job issues created before the salary advisor existed.
Safe to run again - issues that already have the block are skipped.

    GITHUB_TOKEN=... python tools/add_salary_to_issues.py
"""

import re
import sys
from pathlib import Path

import requests

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from jobhunter import salary, tracker   # noqa: E402

API, REPO, headers = tracker.API, tracker.REPO, tracker._headers()

issues = requests.get(f"{API}/repos/{REPO}/issues", headers=headers, timeout=30,
                      params={"labels": "job", "state": "open", "per_page": 100}).json()
for issue in issues:
    body = issue.get("body") or ""
    if "Salary to ask" in body:
        continue
    location = re.search(r"\| Location \| (.*?) \|", body)
    fit = re.search(r"\(fit (\d+)", body)
    paid = re.search(r"\| Salary \| (\w+) ([\d,.]+) – ([\d,.]+) per year \|", body)
    job = {"title": re.sub(r"^\[\d+\]\s*|\s–\s.*$", "", issue["title"]),
           "location": location.group(1) if location else "",
           "fit": {"fit": int(fit.group(1))} if fit else None,
           "salary": {"currency": paid.group(1), "min": float(paid.group(2).replace(",", "")),
                      "max": float(paid.group(3).replace(",", "")), "period": "year"} if paid else None}
    block = salary.markdown(job)
    new_body = body.replace("\n\n**Fit:**", f"\n\n{block}\n\n**Fit:**", 1) if "**Fit:**" in body else f"{block}\n\n{body}"
    r = requests.patch(f"{API}/repos/{REPO}/issues/{issue['number']}", headers=headers, timeout=30,
                       json={"body": new_body})
    print(f"#{issue['number']:<3} {'ok ' if r.ok else r.status_code} {salary.advise(job)['ask']:<32} {job['title'][:45]} | {job['location']}")
