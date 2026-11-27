"""
DASHBOARD - a read-only web page of your open job issues (one static file, no server).

    python tools/build_dashboard.py                 # writes docs/index.html
    python tools/build_dashboard.py --out my.html

Reads the open job issues with the GitHub CLI (gh), so it needs `gh auth login` or GITHUB_TOKEN.
The page is plain HTML + JavaScript: search, filter by country / status, sort by rank.
Publish it with GitHub Pages (Settings > Pages > deploy from /docs) if you want a link.
"""

import argparse
import html
import json
import os
import re
import subprocess
from datetime import datetime, timezone
from pathlib import Path

REPO = os.environ.get("DATA_REPO") or os.environ.get("GITHUB_REPOSITORY", "")
COUNTRIES = ["Germany", "Netherlands", "Ireland", "Denmark", "Sweden", "Finland", "Luxembourg", "India", "Remote", "Other"]

# city / code -> country, so 'Dublin' or 'Amersfoort, NL' also count (checked in order)
PLACES = [
    ("Germany", r"germany|deutschland|berlin|munich|münchen|k[oö]ln|hamburg|frankfurt|stuttgart|dusseldorf|düsseldorf|nuremberg|nürnberg|b[oö]blingen|\bDE\b"),
    ("Netherlands", r"netherlands|nederland|amsterdam|utrecht|amersfoort|veldhoven|harmelen|hoofddorp|eindhoven|rotterdam|\bNL\b"),
    ("Ireland", r"ireland|dublin|cork|galway|\bIE\b"),
    ("Denmark", r"denmark|danmark|copenhagen|k[øo]benhavn|aarhus|\bDK\b"),
    ("Sweden", r"sweden|sverige|stockholm|gothenburg|g[öo]teborg|malm[öo]|\bSE\b"),
    ("Finland", r"finland|suomi|helsinki|espoo|tampere|oulu|\bFI\b"),
    ("Luxembourg", r"luxembourg|luxemburg|\bLU\b"),
    ("India", r"india|pune|bangalore|bengaluru|noida|hyderabad|chennai|mumbai|gurgaon|gurugram"),
    ("Other", r"poland|polska|warsaw|krakow|katowice|wroclaw|gdansk|cyprus|limassol|lithuania|vilnius|czech|romania|austria|switzerland|united kingdom|\bUK\b|london|usa|united states|canada"),
]


def guess_country(text: str) -> str:
    for name, pattern in PLACES:
        if re.search(pattern, text, re.I):
            return name
    if re.search(r"remote|nomad", text, re.I):
        return "Remote"
    return ""


def fetch_issues() -> list[dict]:
    issues, page = [], 1
    while True:   # owner/repo path + page loop (numeric-id paths and --paginate fail here)
        out = subprocess.run(["gh", "api", f"repos/{REPO}/issues?state=open&per_page=100&page={page}"],
                             capture_output=True, text=True, check=True).stdout
        batch = json.loads(out)
        issues += [i for i in batch if "pull_request" not in i]
        if len(batch) < 100:
            return issues
        page += 1


def field(body: str, name: str) -> str:
    m = re.search(rf"^\|\s*{name}\s*\|\s*(.+?)\s*\|\s*$", body or "", re.M)
    return re.sub(r"\*\*", "", m.group(1)).strip() if m else ""


def parse(issue: dict) -> dict:
    body = issue.get("body") or ""
    labels = [l["name"] for l in issue.get("labels", [])]
    rank = re.search(r"Rank\s*\|?\s*\*\*(\d+)\*\*", body)
    salary = re.search(r"Salary to ask:\*\*?\s*([^\n]+)", body) or re.search(r"Salary to ask:\s*([^\n]+)", body)
    location = field(body, "Location")
    country = guess_country(f"{location} {issue['title']}")
    status = "applied" if "applied" in labels else "open"
    return {
        "number": issue["number"], "title": re.sub(r"^(\[\d+\]|\[email\])\s*", "", issue["title"]).strip(),
        "company": field(body, "Company"), "location": location, "country": country,
        "rank": int(rank.group(1)) if rank else 0,
        "salary": (re.sub(r"\*\*", "", salary.group(1)).split("  (")[0].strip() if salary else ""), "status": status,
        "labels": [l for l in labels if l not in ("job", "new", "applied", "tailored")], "url": issue["html_url"],
        "tailored": "tailored" in labels,
        "updated": issue["updated_at"][:10],
    }


PAGE = """<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Job hunt dashboard</title>
<style>
:root{--bg:#fafaf7;--card:#fff;--ink:#1d1d1b;--muted:#6b6b66;--line:#e6e4dc;--accent:#2f6f5e;--warn:#b5651d}
@media (prefers-color-scheme: dark){:root:not([data-theme="light"]){--bg:#161614;--card:#21211e;--ink:#eceae2;--muted:#9c9a92;--line:#33332f;--accent:#7fc1ad;--warn:#e0a060}}
:root[data-theme="dark"]{--bg:#161614;--card:#21211e;--ink:#eceae2;--muted:#9c9a92;--line:#33332f;--accent:#7fc1ad;--warn:#e0a060}
body{margin:0;background:var(--bg);color:var(--ink);font:15px/1.45 system-ui,-apple-system,Segoe UI,sans-serif}
main{max-width:1100px;margin:0 auto;padding:20px 16px}
h1{font-size:22px;margin:0 0 4px}.sub{color:var(--muted);margin:0 0 16px;font-size:13px}
.stats{display:flex;gap:10px;flex-wrap:wrap;margin-bottom:14px}
.stat{background:var(--card);border:1px solid var(--line);border-radius:10px;padding:8px 14px;min-width:110px}
.stat b{display:block;font-size:20px}.stat span{color:var(--muted);font-size:12px}
.bar{display:flex;gap:8px;flex-wrap:wrap;margin-bottom:12px}
input[type=search]{flex:1;min-width:200px;padding:9px 12px;border:1px solid var(--line);border-radius:8px;background:var(--card);color:var(--ink);font:inherit}
.chip{border:1px solid var(--line);background:var(--card);color:var(--ink);border-radius:999px;padding:6px 12px;cursor:pointer;font:inherit;font-size:13px}
.chip.on{background:var(--accent);color:#fff;border-color:var(--accent)}
.card{background:var(--card);border:1px solid var(--line);border-radius:12px;padding:12px 14px;margin-bottom:8px;display:grid;grid-template-columns:auto 1fr auto;gap:12px;align-items:center}
.rank{font-weight:700;font-size:18px;min-width:44px;text-align:center;color:var(--accent)}
.rank.low{color:var(--muted)}
.title{font-weight:600}.title a{color:var(--ink);text-decoration:none}.title a:hover{text-decoration:underline}
.meta{color:var(--muted);font-size:13px;margin-top:2px}
.tags{display:flex;gap:6px;flex-wrap:wrap;margin-top:6px}
.tag{font-size:11px;border:1px solid var(--line);border-radius:6px;padding:2px 6px;color:var(--muted)}
.tag.applied{color:var(--accent);border-color:var(--accent)}.tag.tailored{color:var(--warn);border-color:var(--warn)}
.sal{font-size:13px;text-align:right;color:var(--muted);white-space:nowrap}
footer{color:var(--muted);font-size:12px;margin-top:18px}
@media (max-width:600px){.card{grid-template-columns:auto 1fr}.sal{grid-column:1/-1;text-align:left}}
</style></head><body><main>
<h1>Job hunt dashboard</h1>
<p class="sub">Read-only view of the open job issues. Updated __UPDATED__. Nothing is applied to automatically.</p>
<div class="stats">
<div class="stat"><b>__TOTAL__</b><span>open jobs</span></div>
<div class="stat"><b>__NEW__</b><span>not yet applied</span></div>
<div class="stat"><b>__TAILORED__</b><span>tailored resume ready</span></div>
<div class="stat"><b>__APPLIED__</b><span>marked applied</span></div>
</div>
<div class="bar">
<input type="search" id="q" placeholder="Search title, company, location">
<select id="status" class="chip" aria-label="Status"><option value="">All status</option><option value="open">Not applied</option><option value="applied">Applied</option></select>
</div>
<div class="bar" id="countries"></div>
<div id="list"></div>
<footer>Ranks come from the robot's skill-fit and ATS checks. Open the issue for the tailored resume, cover letter and recruiter email draft.</footer>
</main>
<script>
const JOBS = __DATA__;
const COUNTRIES = __COUNTRIES__;
let country = "", status = "";
const esc = s => String(s).replace(/[&<>"']/g, c => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]));
const bar = document.getElementById("countries");
bar.innerHTML = ['<button class="chip on" data-c="">All countries</button>']
  .concat(COUNTRIES.map(c => `<button class="chip" data-c="${esc(c)}">${esc(c)}</button>`)).join("");
bar.addEventListener("click", e => { const b = e.target.closest("button"); if (!b) return;
  country = b.dataset.c; bar.querySelectorAll(".chip").forEach(x => x.classList.toggle("on", x === b)); draw(); });
document.getElementById("status").addEventListener("change", e => { status = e.target.value; draw(); });
document.getElementById("q").addEventListener("input", draw);
function draw() {
  const q = document.getElementById("q").value.trim().toLowerCase();
  const rows = JOBS.filter(j => (!country || j.country === country) && (!status || j.status === status) &&
    (!q || `${j.title} ${j.company} ${j.location}`.toLowerCase().includes(q)))
    .sort((a, b) => b.rank - a.rank);
  document.getElementById("list").innerHTML = rows.length ? rows.map(j => `
    <div class="card">
      <div class="rank ${j.rank < 60 ? "low" : ""}">${j.rank || "–"}</div>
      <div><div class="title"><a href="${esc(j.url)}" target="_blank" rel="noopener">${esc(j.title)}</a></div>
        <div class="meta">${esc(j.company)} · ${esc(j.location)}</div>
        <div class="tags"><span class="tag ${j.status}">${j.status === "applied" ? "applied" : "not applied"}</span>${j.tailored ? '<span class="tag tailored">tailored</span>' : ""}
        ${j.labels.map(l => `<span class="tag">${esc(l)}</span>`).join("")}</div></div>
      <div class="sal">${esc(j.salary || "salary not shown")}</div>
    </div>`).join("") : '<p class="meta">No jobs match these filters.</p>';
}
draw();
</script></body></html>"""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="docs/index.html")
    args = ap.parse_args()
    jobs = [parse(i) for i in fetch_issues()]
    count = lambda s: sum(j["status"] == s for j in jobs) if s != "tailored" else sum(j["tailored"] for j in jobs)
    page = (PAGE.replace("__DATA__", json.dumps(jobs, ensure_ascii=False).replace("</", "<\\/"))
            .replace("__COUNTRIES__", json.dumps(COUNTRIES))
            .replace("__TOTAL__", str(len(jobs))).replace("__NEW__", str(count("open")))
            .replace("__TAILORED__", str(count("tailored"))).replace("__APPLIED__", str(count("applied")))
            .replace("__UPDATED__", datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")))
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(page, encoding="utf-8")
    print(f"{len(jobs)} open jobs -> {out}")


if __name__ == "__main__":
    main()
