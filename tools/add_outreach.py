"""
Add 'Why I fit', recruiter contact, cover letter and email draft to every OPEN job issue that doesn't have them yet.
Runs on GitHub: Actions -> "Add cover letters to old issues" -> Run workflow.
"""
import sys
import time
from pathlib import Path

import requests

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import tailor                                   # noqa: E402
from jobhunter import skill_fit, tracker        # noqa: E402

issues = requests.get(f"{tracker.API}/repos/{tracker.REPO}/issues", headers=tracker._headers(), timeout=30,
                      params={"labels": "job", "state": "open", "per_page": 100}).json()
for issue in issues:
    if "Why I fit" in (issue.get("body") or ""):
        continue
    try:
        done = tailor.add_outreach(issue["number"], tailor.job_from_issue(issue["number"]))
        print(f"#{issue['number']}: {'added' if done else 'skipped (no draft)'}")
    except BaseException as error:              # SystemExit from a blocked job site too
        print(f"#{issue['number']}: could not read the job ({error})")
    time.sleep(skill_fit.PAUSE_SECONDS)
