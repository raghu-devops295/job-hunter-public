"""
The robot's "main" file. Run it with:   py run.py

Steps:
    1. FETCH        - get jobs from ALL sources (Arbeitnow, company boards, Bundesagentur)
    2. CLEAN        - remove duplicate jobs
    3. TITLE GATE   - keep only titles that look like your kind of job
    4. DETAILS      - Bundesagentur only: fetch descriptions for those jobs
    5. DEALBREAKERS - skip jobs that REQUIRE another language, no visa, local only, outside Europe
    6. SCORE        - give each job points (scoring.py)
    7. MEMORY       - hide jobs you've already seen (add --all to see everything)
    8. SKILL FIT    - Gemini compares each job's must-haves with jobhunter/facts.md
    9. SHOW         - best first: 70% skill fit + 30% rules score

Run:  py run.py          -> only NEW jobs
      py run.py --all    -> all matching jobs, new and old
"""

import re
from pathlib import Path
import sys
import time
from collections import Counter
from concurrent.futures import ThreadPoolExecutor

from jobhunter import companies, memory, salary, skill_fit, tracker
from jobhunter.filters import COMPANY_SOURCES, age_in_days, find_dealbreaker, guess_language, max_age
from jobhunter.scoring import MIN_SCORE, MY_ROLE_IN_TITLE, group_same_job, remove_duplicates, score_job
from jobhunter.sources import apify_linkedin, arbeitnow, bundesagentur, company_boards, enterprise, more_boards, remote_boards, workday


def fetch_everything() -> list[dict]:
    jobs = []

    print("1/5 Arbeitnow...")
    try:
        found = arbeitnow.fetch(max_pages=3)
        print(f"    {len(found)} jobs")
        jobs += found
    except Exception as error:
        print(f"    ! Arbeitnow failed: {error}")

    print("2/5 Company career pages (7 hiring systems)...")
    found, not_found = company_boards.fetch_all({
        "greenhouse": companies.GREENHOUSE, "lever": companies.LEVER, "ashby": companies.ASHBY,
        "recruitee": companies.RECRUITEE, "smartrecruiters": companies.SMARTRECRUITERS,
        "personio": companies.PERSONIO, "workable": companies.WORKABLE,
        "bamboohr": companies.BAMBOOHR, "teamtailor": companies.TEAMTAILOR, "join": companies.JOIN})
    # big-company sites (Phenom, SAP SuccessFactors) - same parallel reader, other fetchers
    company_boards.FETCHERS.update(enterprise.FETCHERS)
    big, big_missing = company_boards.fetch_all({"phenom": companies.PHENOM, "successfactors": companies.SUCCESSFACTORS})
    print(f"    big-company sites (Phenom, SuccessFactors): {len(big)} jobs")
    found += big
    not_found += big_missing
    print(f"    {len(found)} jobs")
    if not_found:
        print(f"    not found (delete these from companies.py): {', '.join(not_found)}")
    jobs += found

    print("3/5 Workday career sites (banks & big tech)...")
    found, not_found = workday.fetch_all(companies.WORKDAY)
    print(f"    {len(found)} jobs")
    if not_found:
        print(f"    not found (delete these from WORKDAY in companies.py): {', '.join(not_found)}")
    jobs += found

    print("4/5 Job boards (Remotive, RemoteOK, Himalayas, Jobicy, NoFluffJobs, JustJoin.it, WeWorkRemotely, Working Nomads)...")
    jobs += remote_boards.fetch_all()
    jobs += more_boards.fetch_all()

    print("5/5 Bundesagentur fuer Arbeit...")
    found = bundesagentur.fetch(companies.BUNDESAGENTUR_SEARCHES)
    print(f"    {len(found)} jobs")
    jobs += found

    print("+ LinkedIn (via Apify, optional)...")
    try:
        jobs += apify_linkedin.fetch()
    except Exception as error:                      # never let an optional source break the run
        print(f"    ! LinkedIn via Apify failed: {str(error)[:150]}")

    return jobs


LINKEDIN_CAREERS = Path("lists/linkedin_careers_urls.txt")


def save_linkedin_careers_pages(kept: list[dict], limit: int = 40) -> None:
    """LinkedIn jobs whose "Apply" button leads to the company's own careers site: remember that site.
    The "Find companies" workflow then detects its hiring system (Greenhouse, Lever, Workday...), and from the
    next run on the robot scans that company's WHOLE careers site - the same role and every other matching one."""
    from urllib.parse import urlparse
    known = set()
    for f in Path("lists").glob("*_careers_urls.txt"):
        known |= {l.strip().lower().rstrip("/") for l in f.read_text(encoding="utf-8").splitlines()
                  if l.strip() and not l.startswith("#")}
    known_hosts = {k.split("/")[0] for k in known}
    new = []
    for job in kept:
        url = job.get("careers_url")
        if job.get("source") != "linkedin" or not url:
            continue
        p = urlparse(url)
        entry = (p.netloc + p.path).lower().rstrip("/")
        # one entry per careers site (host + first path part, e.g. job-boards.greenhouse.io/acme)
        site = "/".join(entry.split("/")[:2])
        if not p.netloc or site in known or entry in known or (p.netloc.lower() in known_hosts and site.count("/") == 0):
            continue
        known.add(site)
        new.append(entry)
    if not new:
        print("LinkedIn: no new company careers pages.")
        return
    new = new[:limit]
    header = "" if LINKEDIN_CAREERS.exists() else \
        "# Careers pages of companies seen on LinkedIn (added by the robot). One per line, no https://\n"
    with LINKEDIN_CAREERS.open("a", encoding="utf-8") as f:
        f.write(header + "\n".join(new) + "\n")
    print(f"LinkedIn: {len(new)} new company careers page(s) saved -> Find companies will add them.")


def final_rank(job: dict) -> int:
    """Skills first: 70% Gemini skill fit + 30% rules score (rules score capped at 80 = full marks)."""
    rules = min(job["score"], 80) / 80 * 100
    help_bonus = 5 if any("Work permit/Migration" in r for r in job.get("reasons", [])) else 0   # on top of the cap
    if job.get("fit"):
        return round(0.7 * job["fit"]["fit"] + 0.3 * rules) + help_bonus
    return round(0.7 * 50 + 0.3 * rules)   # not checked yet -> assume a neutral fit of 50


def main():
    started = time.time()
    jobs = fetch_everything()
    print(f"\nGot {len(jobs)} jobs from all sources.")

    # Title gate FIRST (cheap), so the slower steps only see ~500 jobs instead of ~7000
    jobs = [j for j in jobs if re.search(MY_ROLE_IN_TITLE, j["title"].lower())]
    jobs = remove_duplicates(jobs)
    print(f"{len(jobs)} unique jobs with a DevOps/Platform/Cloud title.")

    # Three sources only give a title in their list -> fetch the description for title-gate survivors
    # (skip ones we already know are too old - saves minutes on Workday)
    need_details = [j for j in jobs if j["source"] in ("bundesagentur", "smartrecruiters", "workday", "relocateme", "jaabz", "bamboohr", "join", "phenom", "successfactors", "jobly", "magnetme", "nofluffjobs")
                    and (age_in_days(j) or 0) <= max_age(j)]
    print(f"Reading {len(need_details)} job descriptions (5 at a time)...")

    def describe(job):
        try:
            if job["source"] == "bundesagentur":
                bundesagentur.add_description(job)
            elif job["source"] == "workday":
                workday.add_description(job)
            elif job["source"] == "relocateme":
                more_boards.add_relocateme_description(job)
            elif job["source"] == "jaabz":
                more_boards.add_jaabz_description(job)
            elif job["source"] == "bamboohr":
                company_boards.add_bamboohr_description(job)
            elif job["source"] == "join":
                company_boards.add_jsonld_description(job)
            elif job["source"] == "nofluffjobs":
                more_boards.add_nofluff_description(job)
            elif job["source"] in ("jobly", "magnetme"):
                company_boards.add_jsonld_description(job)
            elif job["source"] == "phenom":
                enterprise.add_phenom_description(job)
            elif job["source"] == "successfactors":
                enterprise.add_successfactors_description(job)
            else:
                company_boards.add_smartrecruiters_description(job)
        except Exception:
            pass  # no description -> still scored on its title

    with ThreadPoolExecutor(max_workers=5) as pool:
        list(pool.map(describe, need_details))

    kept, skipped = [], Counter()
    for job in jobs:
        reason = find_dealbreaker(job)
        if reason:
            skipped[reason.split(":")[0]] += 1
        else:
            kept.append(job)
    print(f"{len(kept)} left after dealbreakers. Skipped: {dict(skipped)}\n")

    # Companies found on JOB BOARDS -> tomorrow's "Find companies" run looks for their own careers page,
    # so their OTHER matching jobs get scanned too (e.g. a company seen once on NoFluffJobs).
    board_companies = sorted({re.sub(r"\s*\(.*?\)", "", j["company"]).strip() for j in kept
                              if j["source"] not in COMPANY_SOURCES and j.get("company")})
    Path("data").mkdir(exist_ok=True)
    Path("data/scan_companies.txt").write_text("\n".join(board_companies), encoding="utf-8")
    print(f"{len(board_companies)} job-board companies saved for careers-page discovery.")
    save_linkedin_careers_pages(kept)

    for job in kept:
        job["score"], job["reasons"] = score_job(job)
        job["ad_language"] = guess_language(job["description"])

    kept = group_same_job(kept)
    good = sorted((j for j in kept if j["score"] >= MIN_SCORE), key=lambda j: j["score"], reverse=True)
    print(f"{len(good)} jobs scored {MIN_SCORE}+   (by source: {dict(Counter(j['source'] for j in good))})")

    seen = memory.load()
    new = [j for j in good if j["id"] not in seen]
    show_all = "--all" in sys.argv
    print(f"{len(new)} NEW since last run, {len(good) - len(new)} already seen."
          + ("" if show_all else "  (use --all to see them all)") + "\n")

    # Judge ALL current matches (Gemini answers are cached, so old jobs cost nothing;
    # at most 25 new checks per run). The tracker needs every judged job, not only new ones.
    # NEW jobs get the Gemini checks first (best rules score first); old jobs only use what's left.
    skill_fit.add_fit(sorted(good, key=lambda j: (j["id"] in seen, -j["score"])))

    # The AI may spot dealbreakers our word-rules missed (e.g. German required, AWS-only)
    ai_skipped = Counter()
    judged_ok = []
    for job in good:
        reason = skill_fit.ai_dealbreaker(job)
        if reason:
            ai_skipped[reason] += 1
        else:
            job["rank"] = final_rank(job)
            judged_ok.append(job)
    judged_ok.sort(key=lambda j: j["rank"], reverse=True)
    if ai_skipped:
        print(f"AI also skipped: {dict(ai_skipped)}")

    to_show = judged_ok if show_all else [j for j in judged_ok if j["id"] not in seen]
    print()

    for job in to_show:
        where = "Remote" if job["remote"] and not job["location"] else job["location"]
        lang = "" if job["ad_language"] == "english" else f"  (ad in {job['ad_language']})"
        tag = "NEW " if job["id"] not in seen else "    "
        fit = job.get("fit")
        label = f"rank {job['rank']:>3} | fit {fit['fit']:>3} | rules {job['score']:>3}" if fit else f"rules {job['score']:>3}"
        print(f"{tag}[{label}] {job['title']}  |  {job['company']}  |  {where}{lang}")
        others = [loc for loc in job.get("all_locations", []) if loc != job["location"]]
        if others:
            print(f"      also in: {'; '.join(others)}")
        sal = job.get("salary")
        if sal:
            print(f"      salary: {sal['currency']} {sal['min'] or '?':,} - {sal['max'] or '?':,} per {sal['period']}")
        print(f"      ask: {salary.advise(job)['ask']}")
        if fit:
            print(f"      fit: {fit.get('verdict', '')}")
            print(f"      matched: {', '.join(fit.get('matched', []))}")
            if fit.get("missing"):
                print(f"      missing: {', '.join(fit['missing'])}")
        print(f"      why: {', '.join(job['reasons'])}")
        print(f"      {job['url']}\n")

    # GitHub Issues (only inside GitHub Actions). Looks at ALL judged matches;
    # it skips any job that already has an issue, so nothing is created twice.
    tracker.publish(judged_ok)
    tracker.remember_jobs(judged_ok)   # keep the full job text so "tailor" works for every issue

    gaps = skill_fit.skill_gaps()
    if gaps:
        print("SKILL GAP REPORT - skills most often missing across all checked jobs:")
        for skill, count in gaps:
            print(f"   {count:>3} jobs  {skill}")
        print()

    # Remember a job only once it has been fully judged. Jobs that missed the Gemini check this run
    # (free-tier limit of 25 per run) stay "new" so the next run checks them.
    judged = [j for j in good if j["id"] in seen or j.get("fit") or not j["description"]]
    memory.remember(seen, judged)
    memory.save(seen)
    # Tell the workflow's tailoring step whether Gemini was overloaded (then it skips tailoring this run;
    # add the label `tailor` to an issue later to get its resume).
    busy_flag = Path("data/google_busy")
    if skill_fit.GOOGLE_BUSY:
        busy_flag.parent.mkdir(exist_ok=True)
        busy_flag.write_text("1")
    elif busy_flag.exists():
        busy_flag.unlink()
    print(f"Done in {time.time() - started:.0f} seconds. Memory now holds {len(seen)} jobs.")


if __name__ == "__main__":
    main()
