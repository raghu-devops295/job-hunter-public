"""
The robot's BRAIN: gives every job a score and explains why.

How it works (like a teacher marking an exam):
    - Words in the job TITLE        -> big points (the title says what the job IS)
    - Words in the DESCRIPTION      -> small points (the description says what it USES)
    - Bad words (Power Platform...) -> minus points
    - Job in one of YOUR countries  -> bonus points
    - Final score = sum of all points.  Higher = better match for you.

To tune the robot, you only edit the lists below. No other code changes needed.
"""

import re
from pathlib import Path
from difflib import SequenceMatcher

# (label shown to you, pattern to search, points if in TITLE, points if in DESCRIPTION)
# \b means "word boundary", so r"\bsre\b" matches "SRE" but not "pressure".
# Employer HELPS with the move (your keyword list). Also gives +5 on the final rank (see run.py).
VISA_HELP = (r"visa sponsorship|work permit (support|assistance|sponsorship)|relocation (support|package|assistance)"
             r"|international (applicants|candidates) (are )?welcome|immigration (support|assistance)"
             r"|highly skilled migrant|kennismigrant|skilled worker (visa|sponsorship)|employment permit"
             r"|critical skills|\bblue card\b|blaue karte|we (will |can |do )?sponsor|help (you )?with (your )?(visa|work permit|relocation)")

GOOD_WORDS = [
    ("SRE",                r"\bsre\b|site reliability",                    25, 5),
    ("Platform Engineer",  r"platform engineer",                           25, 5),
    ("DevOps",             r"devops",                                      20, 4),
    ("Cloud Engineer",     r"cloud (infra|infrastructure|engineer)",       15, 3),
    ("Infra Engineer",     r"infrastruc?tu(re|ur) engineer|infrastructuur",  15, 3),
    ("Azure",              r"\bazure\b",                                   15, 8),
    ("AKS",                r"\baks\b|azure kubernetes",                    15, 10),
    ("Kubernetes",         r"kubernetes|\bk8s\b",                          10, 6),
    ("Azure DevOps",       r"azure devops|azure pipelines",               15, 6),   # top target role
    ("GitLab",             r"gitlab",                                      3, 3),
    ("Helm",               r"\bhelm\b",                                    3, 3),
    ("Databricks",         r"databricks",                                  5, 4),
    ("Observability",      r"prometheus|grafana|observability",            3, 3),
    ("Terraform",          r"terraform",                                   5, 5),
    ("Identity/Security",  r"entra id|azure ad\b|\brbac\b|azure policy|key vault|hashicorp vault", 3, 3),
    ("English workplace",  r"(working|company|office|team|business) language (is )?english|english[- ]speaking (team|company|environment)|we (work|speak) (in )?english|no (german|dutch|finnish|danish|lithuanian) (needed|required)", 5, 5),
    ("Relocation package", r"relocation (package|support|assistance|budget|bonus)|(help|support) (with|for) (your )?(visa|relocation|housing|flights?)|we (will )?sponsor|visa (support|assistance)", 5, 5),
    ("Senior/Lead",        r"\bsenior\b|\blead\b",                         5, 0),
    ("Banking",            r"bank|fintech|financial services",             4, 4),
    # Relocation words: a BONUS, never a filter.
    ("Work permit/Migration", VISA_HELP, 10, 10),
    ("Relocation/Visa",    r"(?<!not providing )(?<!not offering )(?<!no )relocation(?! sponsorships? (is|are) not)|visa sponsorship|sponsor (a |your )?visa|expat", 10, 10),
]

BAD_WORDS = [
    ("Power Platform/M365", r"power platform|dynamics 365|\bm365\b",       -40, -5),
    ("Product role",        r"product (manager|owner)",                    -40, 0),
    ("Eng Manager",         r"engineering manager",                        0, 0),      # you lead a team of 5 - manager roles are fine
    ("Contract/B2B only",   r"\bfreelance\b|\bfreelancer\b|\bb2b\b|contract (role|position|only)|\bcontractor\b|zzp|\bzlecenie\b", -15, -15),
    ("Program/Project Mgr", r"program manager|project manager|programme manager", -40, 0),
    ("Data role",           r"data engineer|data scientist",               -20, 0),
    ("Developer role",      r"backend|frontend|full[- ]?stack|java developer", -20, 0),
    ("SAP/Avaloq",          r"\bsap\b|avaloq",                             -20, -5),
    ("Sysadmin/Support",    r"systemadministrator|helpdesk|support engineer", -15, 0),
    ("Student/Intern",      r"werkstudent|praktikum|ausbildung|\bintern\b|internship|apprentice", -40, 0),
    ("Non-engineering",     r"assistant|business partner|compensation|designer|recruiter|talent|account executive|marketing", -60, 0),
    ("Mobile/ML/Sales",     r"\bios\b|android|machine learning|\bml\b|account manager|sales", -30, 0),
    # (Language, visa and local-only rules live in filters.py - they skip a job completely.)
]

# Place patterns for every country the robot knows. Cities are listed because many ads only say "Berlin".
ALL_COUNTRIES = {
    "Germany": r"germany|deutschland|,\s*de|berlin|munich|münchen|hamburg|frankfurt|cologne|köln|stuttgart"
               r"|düsseldorf|dusseldorf|nuremberg|nürnberg|leipzig|dresden|hannover|bonn|karlsruhe",
    "Netherlands": r"netherlands|nederland|,\s*nl|amsterdam|rotterdam|utrecht|the hague|den haag|eindhoven|veenendaal"
                   r"|hoofddorp|amstelveen|haarlem|delft|leiden|groningen|nijmegen|arnhem|zwolle|breda|tilburg",
    "Ireland": r"ireland|,\s*ie|dublin|cork|galway|limerick",
    "Denmark": r"denmark|danmark|,\s*dk|copenhagen|københavn|aarhus|odense",
    "Finland": r"finland|suomi|,\s*fi|helsinki|espoo|tampere|oulu|vantaa",
    "Sweden": r"sweden|sverige|,\s*se|stockholm|gothenburg|göteborg|malmö|malmo|uppsala|lund",
    "Luxembourg": r"luxembourg|luxemburg|,\s*lu|luxembourg city",
    "Spain": r"spain|españa|espana|,\s*es|madrid|barcelona|valencia|málaga|malaga|seville|sevilla|bilbao",
    "Estonia": r"estonia|eesti|,\s*ee|tallinn|tartu",
    "Lithuania": r"lithuania|lietuva|,\s*lt|vilnius|kaunas|klaipėda|klaipeda",
    # Gulf (added Nov 2026): Dubai / Abu Dhabi and Riyadh / Jeddah
    "United Arab Emirates": r"united arab emirates|\buae\b|u\.a\.e|,\s*ae|dubai|abu dhabi|sharjah|ajman|ras al khaimah",
    "Saudi Arabia": r"saudi arabia|saudi|\bksa\b|k\.s\.a|riyadh|jeddah|jiddah|dammam|khobar|dhahran|neom",
}

# YOUR target countries come from ONE file: lists/countries.txt (best first). Edit that file only.
_COUNTRIES_FILE = Path(__file__).resolve().parent.parent / "lists" / "countries.txt"


def _target_countries() -> list[str]:
    try:
        lines = _COUNTRIES_FILE.read_text(encoding="utf-8").splitlines()
    except OSError:
        lines = ["Netherlands", "Germany", "Ireland"]
    wanted = [l.strip() for l in lines if l.strip() and not l.strip().startswith("#")]
    unknown = [c for c in wanted if c not in ALL_COUNTRIES]
    if unknown:
        raise ValueError(f"lists/countries.txt: no place pattern for {unknown} - add it to ALL_COUNTRIES in scoring.py")
    return wanted


TARGET_COUNTRIES = _target_countries()
MY_COUNTRIES = {c: ALL_COUNTRIES[c] for c in TARGET_COUNTRIES}
# Every target country gets +10; the FIRST one in the file (your top choice) gets +15.
COUNTRY_BONUS = {c: (15 if i == 0 else 10) for i, c in enumerate(TARGET_COUNTRIES)}
NEAR_WROCLAW = []      # (no extra points for cities any more - every country/city is equal)
MY_COUNTRY_BONUS = 10   # (kept for old imports)

# THE TITLE GATE: the title must contain at least one of these, or the job is out.
# (Stops jobs like "iOS Developer" passing on bonus points alone.)
MY_ROLE_IN_TITLE = r"\bsre\b|site reliability|devops|platform|cloud|infra|azure|kubernetes|\bk8s\b|reliability"

# Jobs scoring at least this much are shown. Raise it to see fewer, better jobs.
MIN_SCORE = 30


def find_country(job: dict) -> str | None:
    """Which of YOUR countries is this job in? (None = somewhere else)"""
    where = (job.get("location") or "").lower()
    for country, pattern in MY_COUNTRIES.items():
        if re.search(rf"\b(?:{pattern})\b", where):
            return country
    return None


def score_job(job: dict) -> tuple[int, list[str]]:
    """Return (score, reasons) for one job."""
    title = job["title"].lower()
    desc = job["description"].lower()

    if not re.search(MY_ROLE_IN_TITLE, title):
        return -100, ["title is not a DevOps/Platform/Cloud role"]

    score, reasons = 0, []

    for label, pattern, title_pts, desc_pts in GOOD_WORDS + BAD_WORDS:
        if title_pts and re.search(pattern, title):
            score += title_pts
            reasons.append(f"{title_pts:+} {label} (title)")
        elif desc_pts and re.search(pattern, desc):
            score += desc_pts
            reasons.append(f"{desc_pts:+} {label}")

    # (AWS-only / GCP-only jobs are now skipped completely in filters.py)

    # A German/Dutch ad that never mentions English usually expects you to speak German/Dutch.
    # We keep it (it might still be fine) but push it down the list.
    from jobhunter.filters import guess_language   # imported here to avoid a circular import
    if guess_language(job["description"]) != "english" and not re.search(r"english|englisch|engels", desc):
        score -= 5
        reasons.append("-5 ad not in English (kept: no language requirement stated)")

    # Remote jobs are allowed but get NO extra points: ranking is about skills, not work style.
    country = find_country(job)
    if country:
        bonus = COUNTRY_BONUS.get(country, MY_COUNTRY_BONUS)
        score += bonus
        reasons.append(f"+{bonus} {country}")
    if job.get("nomad") and not country:
        score += 10                                    # same as a target country
        reasons.append("+10 nomad-visa remote (work from India / anywhere)")
    where = (job.get("location") or "").lower()
    for label, pattern, pts in NEAR_WROCLAW:
        if re.search(pattern, where):
            score += pts
            reasons.append(f"+{pts} {label}")
            break

    # Visa-friendly employers move faster: IND recognised sponsor (NL). (Ads offering visa/relocation
    # help already get +10 from GOOD_WORDS; ads saying "no sponsorship" are skipped in filters.py.)
    if country == "Netherlands":
        from jobhunter.sponsors import is_ind_sponsor
        if is_ind_sponsor(job["company"]):
            score += 10
            reasons.append("+10 IND recognised sponsor")
    if country == "Denmark":
        from jobhunter.sponsors import is_dk_certified
        if is_dk_certified(job["company"]):
            score += 8
            reasons.append("+8 Danish Fast-Track certified")

    from jobhunter.sponsors import is_relocation_friendly
    if is_relocation_friendly(job["company"]):
        score += 5
        reasons.append("+5 known to relocate engineers")

    # Salary shown in the ad and clearly above the work-permit minimum (~EUR 50K/yr) -> small bonus
    m = re.search(r"(?:€|eur|euro)\s?(\d{2,3})[.,]?(\d{3})?\s?(k\b)?|(\d{2,3})[.,]?(\d{3})\s?(?:€|eur)", desc)
    if m:
        nums = [int(x) for x in re.findall(r"\d{2,3}", m.group(0))]
        yearly = nums[0] * 1000 if nums and nums[0] < 1000 else 0
        if yearly >= 50_000:
            score += 3
            reasons.append("+3 salary shown, above visa minimum")

    # Early applicants get far more replies: small bonus for very fresh posts.
    from jobhunter.filters import age_in_days
    age = age_in_days(job)
    if age is not None and age <= 2:
        score += 5
        reasons.append("+5 posted in the last 2 days")

    return score, reasons


def _simple_title(title: str) -> str:
    """'Lead Architekt & Platform Engineer (m/w/d)' -> 'lead architekt platform engineer'"""
    title = title.lower().split("|")[0]                # 'SRE | Germany | Remote' -> 'SRE'
    title = re.sub(r"\(.*?\)", " ", title)           # drop (m/w/d), (100%), ...
    return " ".join(re.sub(r"[^a-zäöüß ]+", " ", title).split())


def group_same_job(jobs: list[dict]) -> list[dict]:
    """
    One company often posts the SAME role in many countries (e.g. Elastic: Poland, Ireland, Spain...).
    Show it once: keep the best-scoring copy and list all locations on it.
    """
    groups = {}
    for job in jobs:
        key = (job["company"].lower(), _simple_title(job["title"]))
        best = groups.get(key)
        if best is None:
            job["all_locations"] = [job["location"]]
            groups[key] = job
        else:
            best["all_locations"].append(job["location"])
            if job["score"] > best["score"]:          # keep the copy in YOUR country
                job["all_locations"] = best["all_locations"]
                groups[key] = job
    return list(groups.values())


def remove_duplicates(jobs: list[dict]) -> list[dict]:
    """
    Keep only the first copy of each job.
    Same id = same job. ALSO: same company + same city + almost the same title = same job
    (catches a job posted twice, e.g. once in German, once in English).
    Fast: we only compare jobs that share company + city (kept in a dictionary).
    """
    seen_ids, unique = set(), []
    by_company_city = {}   # (company, city) -> list of simple titles already kept
    for job in jobs:
        if job["id"] in seen_ids:
            continue
        key = (job["company"].lower(), job["location"].lower())
        title = _simple_title(job["title"])
        twins = by_company_city.setdefault(key, [])
        if any(SequenceMatcher(None, t, title).ratio() > 0.85 for t in twins):
            continue
        twins.append(title)
        seen_ids.add(job["id"])
        unique.append(job)
    return unique
