"""
Fill in the job ad text for issues labelled `needs-text`, then tailor the resume.

Why: the Claude cloud tasks often cannot open job pages, but a GitHub Actions runner can.
So Claude only adds the issue (with the link); this script fetches the ad text, stores it
inside the issue (between <!-- job-text --> markers) and removes `needs-text`.
The workflow then runs tailor.py for every issue that got its text.

    GITHUB_TOKEN=... python tools/fill_job_text.py            # all open needs-text issues
    GITHUB_TOKEN=... python tools/fill_job_text.py --issue 485
Prints the numbers of the filled issues to data/filled.txt (one per line).
"""
import argparse
import html
import json
import re
import sys
from pathlib import Path

import requests

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from jobhunter import filters, tracker            # noqa: E402
from jobhunter.sources.common import HEADERS      # noqa: E402

API, REPO, H = tracker.API, tracker.REPO, tracker._headers()
MIN_TEXT = 1500


def ad_text(url: str) -> str:
    """Best effort: the JobPosting JSON-LD description (most ATS pages have it), else the visible page text."""
    page = requests.get(url, headers=HEADERS, timeout=30).text
    for block in re.findall(r'<script[^>]+application/ld\+json[^>]*>(.*?)</script>', page, re.S | re.I):
        try:
            data = json.loads(block.strip())
        except ValueError:
            continue
        for item in (data if isinstance(data, list) else data.get("@graph", [data])):
            if isinstance(item, dict) and item.get("@type") == "JobPosting" and item.get("description"):
                return _clean(item["description"])
    page = re.sub(r"<(script|style|noscript|nav|header|footer)[^>]*>.*?</\1>", " ", page, flags=re.S | re.I)
    return _clean(page)


def _clean(markup: str) -> str:
    text = re.sub(r"<(br|/p|/li|/h\d|/div)[^>]*>", "\n", markup, flags=re.I)
    text = html.unescape(re.sub(r"<[^>]+>", " ", text))
    text = re.sub(r"[ \t\xa0]+", " ", text)
    return re.sub(r"\n\s*\n+", "\n\n", text).strip()[:12000]


def fill(issue: dict) -> bool:
    body = issue.get("body") or ""
    link = re.search(r"\[Open the job ad\]\((.+?)\)", body)
    if not link:
        print(f"   #{issue['number']}: no job link in the issue")
        return False
    try:
        text = ad_text(link.group(1))
    except Exception as error:
        print(f"   #{issue['number']}: could not open {link.group(1)}: {str(error)[:100]}")
        return False
    if len(text) < MIN_TEXT:
        print(f"   #{issue['number']}: page gave only {len(text)} characters (JavaScript-only page?) - paste the ad by hand")
        return False
    block = f"<!-- job-text -->\n{text}\n<!-- /job-text -->"
    if "<!-- job-text -->" in body:
        body = re.sub(r"<!-- job-text -->.*?<!-- /job-text -->", lambda _: block, body, flags=re.S)
    else:
        body += f"\n\n<details><summary>Full job ad text</summary>\n\n{block}\n</details>\n"
    requests.patch(f"{API}/repos/{REPO}/issues/{issue['number']}", headers=H, json={"body": body}, timeout=30).raise_for_status()
    requests.delete(f"{API}/repos/{REPO}/issues/{issue['number']}/labels/needs-text", headers=H, timeout=30)
    print(f"   #{issue['number']}: filled {len(text)} characters")
    # Same deal-breaker rules as the robot (language required, no visa, local only, AWS/GCP-only).
    # The Claude digest often cannot read ads itself, so this is where those checks happen.
    loc = re.search(r"\| Location \| (.*?) \|", body)
    job = {"title": re.sub(r"^\[[^\]]*\]\s*|\s+–\s+.*$", "", issue["title"]), "description": text,
           "location": loc.group(1) if loc else "", "company": "", "source": "email"}
    reason = filters.find_dealbreaker(job)
    if reason:
        requests.post(f"{API}/repos/{REPO}/issues/{issue['number']}/comments", headers=H, timeout=30,
                      json={"body": f"⚠️ Robot check of the full ad: **{reason}** – probably not worth applying. "
                                    "Close this issue if you agree."})
        requests.post(f"{API}/repos/{REPO}/issues/{issue['number']}/labels", headers=H, timeout=30,
                      json={"labels": ["check-fit"]})
        print(f"   #{issue['number']}: deal-breaker found - {reason} (labelled check-fit, not tailored)")
        return False          # do not spend a Gemini tailoring call on it
    return True


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--issue", type=int)
    args = ap.parse_args()
    if args.issue:
        issues = [requests.get(f"{API}/repos/{REPO}/issues/{args.issue}", headers=H, timeout=30).json()]
    else:
        issues = requests.get(f"{API}/repos/{REPO}/issues", headers=H, timeout=30,
                              params={"labels": "needs-text", "state": "open", "per_page": 50}).json()
    filled = [str(i["number"]) for i in issues if fill(i)]
    Path("data").mkdir(exist_ok=True)
    Path("data/filled.txt").write_text("\n".join(filled), encoding="utf-8")
    print(f"Filled {len(filled)} of {len(issues)} issue(s).")


if __name__ == "__main__":
    main()
