"""Copy new company names / careers URLs found by the morning digest from the PRIVATE data repo into lists/.

The digest (a Claude scheduled task) can only push to the private repo, so it appends employers from
job-alert emails to lists/alerts_companies.txt and lists/alerts_careers_urls.txt THERE. This script
merges any new lines into the same files here (case-insensitive, order kept), so "Find companies"
can detect their hiring systems. These files hold only company names and careers URLs - nothing personal.

    DATA_REPO=owner/private-repo GITHUB_TOKEN=... python tools/pull_alert_lists.py
"""
import base64
import os
from pathlib import Path

import requests

FILES = ["lists/alerts_companies.txt", "lists/alerts_careers_urls.txt"]


def main() -> None:
    repo, token = os.environ.get("DATA_REPO"), os.environ.get("GITHUB_TOKEN")
    if not repo or not token:
        print("No DATA_REPO / token - skipped.")
        return
    headers = {"Authorization": f"Bearer {token}", "Accept": "application/vnd.github+json"}
    for path in FILES:
        r = requests.get(f"https://api.github.com/repos/{repo}/contents/{path}", headers=headers, timeout=30)
        if not r.ok:
            print(f"{path}: not in the private repo ({r.status_code}) - skipped")
            continue
        theirs = base64.b64decode(r.json()["content"]).decode("utf-8").splitlines()
        local = Path(path)
        raw = local.read_text(encoding="utf-8") if local.exists() else ""
        mine = raw.splitlines()
        seen = {line.strip().lower() for line in mine if line.strip()}
        new = [line.strip() for line in theirs
               if line.strip() and not line.startswith("#") and line.strip().lower() not in seen]
        new = list(dict.fromkeys(new))
        if new:
            with local.open("a", encoding="utf-8") as f:
                if raw and not raw.endswith("\n"):
                    f.write("\n")
                f.write("\n".join(new) + "\n")
        print(f"{path}: {len(new)} new line(s)")


if __name__ == "__main__":
    main()
