"""
Make a tailored, ATS-friendly resume PDF for ONE job.

On your laptop (pick one):
    py tailor.py --file job.txt          <- paste the job ad text into job.txt first (works for ANY site, incl. LinkedIn)
    py tailor.py --url  https://...      <- company career pages (Greenhouse, Lever, Ashby...); LinkedIn blocks this

On GitHub (automatic): add the label  tailor  to a job issue -> the PDF + ATS report appear on the issue.

Output: output/Raghu_<Company>_<Short_Title>.pdf and an ATS report in the terminal.
"""

import argparse
import base64
import json
import os
import re
import sys
from pathlib import Path

import requests

from jobhunter import tailor
from jobhunter.sources.common import HEADERS, strip_html

API = "https://api.github.com"
REPO = os.environ.get("DATA_REPO") or os.environ.get("GITHUB_REPOSITORY", "")


def job_from_file(path: str) -> dict:
    text = Path(path).read_text(encoding="utf-8")
    first = next((line.strip() for line in text.splitlines() if line.strip()), "Job")
    return {"id": "file", "title": first[:100], "company": "", "location": "", "url": "", "description": text}


def job_from_url(url: str) -> dict:
    r = requests.get(url, headers=HEADERS, timeout=30)
    r.raise_for_status()
    title = re.search(r"<title>(.*?)</title>", r.text, re.S | re.I)
    text = strip_html(re.sub(r"<(script|style)[^>]*>.*?</\1>", " ", r.text, flags=re.S | re.I))
    return {"id": url, "title": strip_html(title.group(1)) if title else "Job", "company": "",
            "location": "", "url": url, "description": text[:12000]}


def _gh(method, path, **kw):
    headers = {"Authorization": f"Bearer {os.environ['GITHUB_TOKEN']}", "Accept": "application/vnd.github+json"}
    r = requests.request(method, f"{API}/repos/{REPO}{path}", headers=headers, timeout=30, **kw)
    r.raise_for_status()
    return r.json() if r.text else {}


def job_from_issue(number: int) -> dict:
    issue = _gh("GET", f"/issues/{number}")
    job_id = re.search(r"<!-- job-id: (.+?) -->", issue.get("body") or "")
    store_file = Path("data/job_store.json")
    store = json.loads(store_file.read_text(encoding="utf-8")) if store_file.exists() else {}
    company = re.search(r"\| Company \| (.*?) \|", issue.get("body") or "")
    embedded = re.search(r"<!-- job-text -->(.*?)<!-- /job-text -->", issue.get("body") or "", re.S)
    if embedded and len(embedded.group(1).strip()) > 300:      # job added by hand (e.g. from an alert email)
        where = re.search(r"\| Location \| (.*?) \|", issue["body"])
        link = re.search(r"\[Open the job ad\]\((.+?)\)", issue["body"])
        return {"id": f"issue-{number}", "title": re.sub(r"^\[[^\]]*\]\s*|\s+–\s+.*$", "", issue["title"]),
                "company": company.group(1) if company else "", "location": where.group(1) if where else "",
                "url": link.group(1) if link else "", "description": embedded.group(1).strip()}
    if job_id and job_id.group(1) in store and store[job_id.group(1)].get("description"):
        job = dict(store[job_id.group(1)])
        job["company"] = job.get("company") or (company.group(1) if company else "")
        return job
    link = re.search(r"\[Open the job ad\]\((.+?)\)", issue.get("body") or "")
    if not link:
        raise SystemExit("Could not find the job text or link on this issue.")
    try:
        job = job_from_url(link.group(1))
    except requests.HTTPError:
        raise SystemExit("the job website blocked the robot from reading the ad. The robot saves job texts on "
                         "every run now, so add the `tailor` label again after the next run (or paste the job to Claude).")
    job["title"] = re.sub(r"^\[\d+\]\s*|\s+–\s+.*$", "", issue["title"])
    job["company"] = company.group(1) if company else ""
    return job


def upload_pdf(pdf: Path, issue: int) -> str:
    """Save the PDF in the repo under resumes/ so it opens with one click from the issue."""
    path = f"resumes/{pdf.name}"                  # all PDFs in one folder, file name starts with your name
    existing = requests.get(f"{API}/repos/{REPO}/contents/{path}", timeout=30,
                            headers={"Authorization": f"Bearer {os.environ['GITHUB_TOKEN']}"})
    body = {"message": f"Tailored resume for issue #{issue}",
            "content": base64.b64encode(pdf.read_bytes()).decode()}
    if existing.ok:
        body["sha"] = existing.json()["sha"]          # replace an older version
    import time
    for attempt in range(4):                          # 409 = another save happened at the same moment -> retry
        try:
            _gh("PUT", f"/contents/{path}", json=body)
            break
        except requests.HTTPError as error:
            if error.response is None or error.response.status_code != 409 or attempt == 3:
                raise
            time.sleep(5 * (attempt + 1))
    return f"https://github.com/{REPO}/blob/main/{path}"


def remove_tailor_label(issue: int) -> None:
    """Take the 'tailor' label off again, so adding it later triggers a fresh run."""
    r = requests.delete(f"{API}/repos/{REPO}/issues/{issue}/labels/tailor", timeout=30,
                        headers={"Authorization": f"Bearer {os.environ['GITHUB_TOKEN']}",
                                 "Accept": "application/vnd.github+json"})
    if r.status_code == 404:          # already off (the auto-run never had it) - nothing to do
        print("   'tailor' label already off")
    else:
        print(f"   remove 'tailor' label: HTTP {r.status_code}")


def add_outreach(issue: int, job: dict) -> bool:
    """Put 'Why I fit', recruiter, cover letter and email draft into the issue (once)."""
    from jobhunter import outreach
    body = _gh("GET", f"/issues/{issue}").get("body") or ""
    if "Why I fit" in body:
        return False
    extra = outreach.markdown(job, outreach.draft(job))
    if not extra:
        return False
    body = body.replace("\n---\n", f"\n{extra}\n\n---\n", 1) if "\n---\n" in body else body + "\n\n" + extra
    _gh("PATCH", f"/issues/{issue}", json={"body": body})
    return True


SHORT_WORDS = [  # long words -> short ones, so file names stay short (upload forms often limit length)
    (r"site reliability engineer(ing)?", "SRE"), (r"senior", "Sr"), (r"engineer(ing)?", "Eng"),
    (r"principal", "Princ"), (r"infrastructure", "Infra"), (r"platform", "Platform"), (r"software", "SW"),
    (r"developer", "Dev"), (r"architect", "Arch"), (r"specialist", "Spec"), (r"manager", "Mgr"),
    (r"management", "Mgmt"), (r"microsoft\s+", ""), (r"cloud\s+", "Cloud"), (r"\b(and|with|for|the|of|in)\b", " "),
]
COMPANY_NOISE = r"\b(gmbh|ag|se|ltd|limited|inc|bv|b\.v\.|nv|group|groupe|technologies|technology|ireland|deutschland|niederlassung|holding|com)\b"


def safe_name(company: str, title: str = "", limit: int = 38) -> str:
    """('Doctolib', 'Senior Site Reliability Engineer (x/f/m)') -> 'Doctolib_Sr_SRE' (short, safe file name)."""
    company = re.sub(COMPANY_NOISE, " ", company or "", flags=re.I).split()
    company = (company[0] if company else "")[:12]
    title = re.sub(r"\((?:[a-z]/?)+\)|\(gn\)|\(all genders?\)|\(.*?\)", " ", title or "", flags=re.I)  # drop (m/w/d), (...)
    title = re.split(r"\s[-–|—:]\s", title)[0]                     # 'Platform Engineer - Observability' -> first part
    for pattern, short in SHORT_WORDS:
        title = re.sub(pattern, short, title, flags=re.I)
    name = re.sub(r"[^A-Za-z0-9]+", "_", f"{company} {title}").strip("_")
    if len(name) > limit:
        name = name[:limit].rsplit("_", 1)[0]          # cut at a whole word
    return name


def main():
    ap = argparse.ArgumentParser(description="Tailor your resume to one job")
    src = ap.add_mutually_exclusive_group(required=True)
    src.add_argument("--file")
    src.add_argument("--url")
    src.add_argument("--issue", type=int)
    args = ap.parse_args()

    if not os.environ.get("GEMINI_API_KEY"):
        sys.exit("GEMINI_API_KEY is not set.")

    job = job_from_file(args.file) if args.file else job_from_url(args.url) if args.url else job_from_issue(args.issue)
    if len(job["description"]) < 300:
        sys.exit("The job text is too short - the page probably blocked us. Save the ad text to a file and use --file.")

    print(f"Tailoring for: {job['title']} {('- ' + job['company']) if job['company'] else ''}")
    # on GitHub (label added): always generate the resume, no match check; on a laptop keep the gate
    result = tailor.tailor(job, gate=not args.issue)
    name = safe_name(job["company"], result["keywords"]["job_title"] or job["title"]) or "job"
    pdf = tailor.render_pdf(result, Path("output") / f"Raghu_{name}.pdf")
    text_report = tailor.report(result)
    parsed = tailor.pdf_parse_check(pdf, result)
    if parsed:
        pdf_score, pdf_missing = parsed
        text_report += (f"\n\n**PDF text check (what the ATS parser reads): {pdf_score}%**"
                        + (f" - keywords the PDF text lacks: {', '.join(pdf_missing)}" if pdf_score < result["score"] else ""))
    print("\n" + text_report.replace("**", ""))
    print(f"\nPDF saved: {pdf}")

    if args.issue:                    # running on GitHub: save the PDF in the repo and comment on the issue
        link = upload_pdf(pdf, args.issue)
        _gh("POST", f"/issues/{args.issue}/comments", json={"body":
            f"### ✅ Tailored resume ready\n\n**[📄 Open the PDF]({link})**  (then ⋯ / Download)\n\n{text_report}\n\n"
            f"Please read it once before sending - you are the final check."})
        # only a resume that reached the ATS target gets the "tailored" label; a short one is flagged for review
        done_label = "tailored" if result["score"] >= tailor.TARGET_SCORE else "needs-review"
        _gh("POST", f"/issues/{args.issue}/labels", json={"labels": [done_label]})
        try:
            add_outreach(args.issue, job)       # cover letter etc. for issues made before this feature
        except Exception as error:
            print(f"   (outreach skipped: {error})")
        remove_tailor_label(args.issue)

if __name__ == "__main__":
    try:
        main()
    except SystemExit as stop:
        issue = next((int(a) for i, a in enumerate(sys.argv) if sys.argv[i - 1] == "--issue"), None)
        if issue and stop.code not in (0, None) and os.environ.get("GITHUB_TOKEN"):
            _gh("POST", f"/issues/{issue}/comments", json={"body": f"⚠️ Could not tailor this one: {stop.code}"})
            remove_tailor_label(issue)
        raise
    except Exception as error:
        issue = next((int(a) for i, a in enumerate(sys.argv) if sys.argv[i - 1] == "--issue"), None)
        if issue and os.environ.get("GITHUB_TOKEN"):
            _gh("POST", f"/issues/{issue}/comments", json={"body":
                f"⚠️ Could not tailor this one ({type(error).__name__}). Remove and add the `tailor` label again "
                f"to retry, or paste the job text to Claude."})
            remove_tailor_label(issue)
        raise
