"""Save a run's full log in the PRIVATE data repo (logs/<name>/<YYYY-MM-DD>.txt) instead of the public run page.

    python tools/save_log.py run-output.txt job-hunter

This repo is public, so its run pages are too. The workflows send the robot's output to a file,
store it privately with this script, and show only a short status line in public.
Needs DATA_REPO (owner/name) and GITHUB_TOKEN (a token that can write to it).
"""
import base64
import os
import sys
from datetime import datetime, timezone

import requests

API = "https://api.github.com"


def main(log_file: str, name: str) -> None:
    repo, token = os.environ.get("DATA_REPO"), os.environ.get("GITHUB_TOKEN")
    if not repo or not token or not os.path.exists(log_file):
        print("Log not saved (no DATA_REPO, token or log file).")
        return
    path = f"logs/{name}/{datetime.now(timezone.utc):%Y-%m-%d}.txt"   # one file per day (a re-run that day replaces it)
    headers = {"Authorization": f"Bearer {token}", "Accept": "application/vnd.github+json"}
    old = requests.get(f"{API}/repos/{repo}/contents/{path}", headers=headers, timeout=30)
    body = {"message": f"Log of the {name} run",
            "content": base64.b64encode(open(log_file, "rb").read()[-900_000:]).decode()}
    if old.ok:
        body["sha"] = old.json()["sha"]
    r = requests.put(f"{API}/repos/{repo}/contents/{path}", headers=headers, json=body, timeout=60)
    print("Full log saved in the private repo." if r.ok else f"Log not saved (GitHub answered {r.status_code}).")


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
