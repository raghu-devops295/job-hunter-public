"""
The robot's MEMORY: remembers every job it has already shown you.

It's just a small JSON file (data/seen_jobs.json) that looks like:
    {
      "greenhouse:adyen:7607691": {"first_seen": "2026-10-30", "title": "...", "company": "adyen", "score": 52},
      ...
    }
Next run, any job whose id is already in the file is "old" and hidden (unless you use --all).

The data/ folder is NOT uploaded to GitHub (see .gitignore) - it's your personal history.
"""

import json
from datetime import date
from pathlib import Path

MEMORY_FILE = Path("data/seen_jobs.json")


def load() -> dict:
    """Read the memory file. If it doesn't exist yet (first run), start empty."""
    if MEMORY_FILE.exists():
        return json.loads(MEMORY_FILE.read_text(encoding="utf-8"))
    return {}


def save(seen: dict) -> None:
    MEMORY_FILE.parent.mkdir(exist_ok=True)   # create data/ folder if missing
    MEMORY_FILE.write_text(json.dumps(seen, indent=1, ensure_ascii=False), encoding="utf-8")


def remember(seen: dict, jobs: list[dict]) -> None:
    """Add jobs to memory (keeps the date we FIRST saw each one)."""
    today = date.today().isoformat()
    for job in jobs:
        if job["id"] not in seen:
            seen[job["id"]] = {"first_seen": today, "title": job["title"],
                               "company": job["company"], "score": job.get("score")}
