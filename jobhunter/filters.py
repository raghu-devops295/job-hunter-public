"""
DEALBREAKERS: rules that throw a job away completely, no matter its score.

Rules:
    1. Another language is REQUIRED (German, Dutch, French...)  -> skip
       (but "German is a plus" / "we help you learn German" is OK)
    2. Ads WRITTEN in German/Dutch are KEPT - we just check them for
       the German/Dutch versions of these same phrases.
    3. Says NO visa sponsorship / must already have work permit -> skip
    4. Local candidates only / no relocation                    -> skip
    5. Job is OUTSIDE Europe (USA, India, Asia...)              -> skip
    6. Job needs AWS or GCP (and Azure is not mentioned at all) -> skip
    7. Job posted more than MAX_AGE_DAYS ago                    -> skip
       (multi-cloud jobs that ALSO use Azure are kept)

To add a new dealbreaker phrase, just add a line to the lists below.
"""

import os
import re
from datetime import datetime, timezone

from jobhunter.scoring import MY_COUNTRIES

LANGUAGES = r"(german|dutch|french|polish|danish|swedish|norwegian|finnish|lithuanian|estonian|latvian|russian|italian|spanish|czech|deutsch|nederlands)"

# Phrases that mean "you MUST speak this language"
LANGUAGE_REQUIRED = [
    rf"{LANGUAGES} (language )?(skills? |proficiency |knowledge )?(is |are )?(a must|required|mandatory|essential|a requirement)",
    rf"(fluent|fluency|native|proficient|proficiency|business[- ]level|professional) (in |level )?{LANGUAGES}",
    rf"{LANGUAGES} (and english )?(is |are )?(required|mandatory|a must|essential)",
    rf"{LANGUAGES}[^.]{{0,25}}\b(c1|c2|b2)\b",
    rf"\b(c1|c2|b2)\b[^.]{{0,25}}{LANGUAGES}",
    rf"(must|need to|should) speak {LANGUAGES}",
    rf"{LANGUAGES}[- ]speaking",
    rf"required language: {LANGUAGES} \((fluent|native|good|excellent|professional|business)",   # Magnet.me field
    # German phrases (for ads written in German)
    r"deutsch(-? und englisch)?kenntnisse",          # Deutschkenntnisse / Deutsch- und Englischkenntnisse
    r"(fließend|fließendes|verhandlungssicher|verhandlungssicheres|sicheres|sehr gutes) deutsch",
    r"deutsch (und englisch )?(in wort und schrift|fließend|verhandlungssicher)",
    r"deutsch als muttersprache|deutsche muttersprache",
    # Dutch phrases (for ads written in Dutch)
    r"vloeiend nederlands|nederlandstalig|nederlands en engels",
    r"(je spreekt|beheersing van de|kennis van de) nederlands",
    # "good communication skills in Swedish and English", "written and spoken German"
    rf"(communication|communicat\w+ skills|written and (spoken|verbal)|spoken and written|verbal and written)[^.]{{0,25}}\bin {LANGUAGES}",
    rf"{LANGUAGES} and english (both )?(written and spoken|spoken and written|at a professional level)",
    # Swedish / Danish / Finnish / Spanish / Estonian / Lithuanian phrases (ads written in those languages)
    r"(flytande|goda kunskaper i|god kommunikativ förmåga på|behärskar|talar) svenska|svenska (och engelska )?(i tal och skrift|är ett krav|krävs)",
    r"(flydende|behersker|taler) dansk|dansk (og engelsk )?(i skrift og tale|på højt niveau|er et krav)",
    r"sujuva(a)? suome|suomen kielen (taito|osaaminen)|suomi (ja englanti )?(äidinkielenä|sujuvasti)",
    r"(nivel (alto|avanzado|nativo) de|dominio del|fluidez en) (español|castellano)|(español|castellano) (nativo|fluido|imprescindible)",
    r"lietuvių kalb|eesti keel",
]

# If any of these words are near the language phrase, it's NOT required -> keep the job
LANGUAGE_IS_OPTIONAL = (
    r"plus|nice[- ]to[- ]have|advantage|bonus|beneficial|preferred|desirable|learn"
    r"|von vorteil|wünschenswert|idealerweise|wäre schön"   # German: "an advantage", "ideally"
    r"|\bpré\b|pluspunt"                                    # Dutch: "a plus"
)

NO_VISA = [
    r"(no|not|unable to|cannot|can't|can not|do not|don't|won't|will not)( offer| provide| be able to)? (visa )?sponsor",
    r"without (visa )?sponsorship",
    r"(must|need to) (already )?(have|hold|possess) (a |the |an )?(valid )?(eu |uk |us )?(work permit|right to work|work authori[sz]ation)",
    r"(eu|eea|swiss) (citizenship|citizens|passport) (is )?(required|only)",
    r"keine visa|kein visum|kein(e)? (visa-?)?sponsoring|(gültige )?arbeitserlaubnis (ist )?(erforderlich|voraussetzung)",
    r"geen (visum|sponsoring)|werkvergunning (is )?(vereist|verplicht)",
    # "Must already have right to work"
    r"(must|need to|should|required to) (already )?(have|hold|possess) (the |a |an )?(legal |full |existing )?right to work",
    r"(existing|current|valid|full|unrestricted) right to work (in [a-z ]{2,25})?(is )?(required|needed|essential|mandatory)",
    r"right to work in (the )?(eu|eea|netherlands|germany|ireland|poland|denmark|finland|sweden|austria|europe)[^.]{0,20}(is )?(required|essential|mandatory|needed)",
    r"(only|cannot|can't|unable to|not able to)[^.]{0,40}(applicants|candidates)[^.]{0,30}(require|need)[^.]{0,15}(visa|sponsorship|work permit)",
    # "You hold a valid work permit", "valid EU work permit required", "must be eligible to work in the EU"
    r"(valid|existing|current) (eu |eea |dutch |german |irish |swedish |danish |finnish |spanish |estonian |lithuanian )?(work|residence|work and residence) permit (is )?(required|needed|mandatory|a must|essential)",
    r"(?<!whether )(?<!if )(?<!do )you (already )?(have|hold|possess) (a |the )?valid (eu |eea |[a-z]+ )?(work|residence|work and residence) permit",
    r"(must|need to|should|have to) (already )?be (legally )?(eligible|authori[sz]ed|entitled|permitted) to work in (the )?(eu|eea|europe|european union|netherlands|germany|ireland|denmark|sweden|finland|spain|estonia|lithuania|luxembourg)(?! with)",
    r"(eu|eea) (work (permit|authori[sz]ation)|citizenship|passport) (is )?(required|needed|mandatory|a must)",
    r"without (the )?(need|requirement) (for|of) (visa |work permit )?sponsorship",
    r"(we|the company|employer) (are|is) (unable|not able) to (support|offer|provide|sponsor) (work permits?|visas?|sponsorship)",
    r"(gültige|bestehende) (arbeits- und aufenthaltserlaubnis|aufenthaltserlaubnis|arbeitserlaubnis)",
]

LOCAL_ONLY = [
    r"local candidates only|only local candidates",
    r"(not able to|unable to|cannot|can't|can not|do not|don't|won't|will not) (consider|accept) (any )?(candidates|applicants|applications) (who are |that are )?(not|currently not) (living|based|residing|located)",
    r"not (providing|offering|able to offer|able to provide) (any )?relocation",
    r"(are|be|is) currently (based|living|residing|located) in (the netherlands|germany|ireland|poland|denmark|finland|lithuania|sweden|estonia)",
    r"only (consider|accept|considering|accepting) (applications|candidates|applicants) (who are |already |currently )*(based|living|residing|located)",
    r"(must|should) (already |currently )+(be )?(based|live|living|reside|residing|located) in",
    r"no relocation|relocation (is )?not (offered|provided|possible|supported|available)",
    # "Must reside in..." (but "must be based in X or willing to relocate" is fine)
    r"(must|need to|required to|have to) (be )?(reside|residing|live|living|located|based) (in|within|near)(?![^.]{0,60}(relocat|willing to move|move to))",
    r"(residence|residency|resident) in [a-z ]{3,25} (is )?(required|mandatory|a must)",
    # "Citizen / Permanent Resident only"
    r"(citizens?|citizenship|permanent residen\w*|settled status|nationals?) (only|required|is required|is mandatory)",
    r"only (open to )?(eu |eea |[a-z]+ )?(citizens|nationals|permanent residents)",
    r"(must be|should be) (an? )?(eu |eea |[a-z]+ )?(citizen|national|permanent resident)",
    r"wohnsitz in (deutschland|der nähe) (ist )?(erforderlich|voraussetzung)|keine relocation",
    # remote jobs tied to one country (mostly US/Canada)
    r"(us|u\.s\.|united states|american|canadian) citizen(ship)?|green card",
    # a clearance the candidate must already HOLD / be eligible for (a general "security check" note is fine)
    r"(active|current|valid|existing|must (hold|have|obtain)|eligib\w* (for|to obtain)|ability to obtain)\s+(an? )?(\w+ ){0,2}security clearance"
    r"|security clearance (is )?(required|mandatory|needed)",
    r"(must|need to|required to) (be )?(reside|residing|live|living|located|based) (in|within) (the )?(us|u\.s\.|usa|united states|canada|uk|united kingdom)",
    r"(legally )?authori[sz]ed to work in (the )?(us|u\.s\.|usa|united states|canada|uk|united kingdom)",
    r"remote[^.]{0,30}\((us|usa|u\.s\.|canada)( only)?\)|(us|usa|canada)[- ]only|within (the )?(us|usa|united states) (only|time ?zones?)",
]

# Location words meaning "outside Europe" ...
NOT_EUROPE = (
    r"united states|\busa\b|\bus\b|u\.s\.|americas|north america|latam|new york|san francisco|seattle|austin"
    r"|boston|chicago|denver|los angeles|atlanta|toronto|vancouver|montreal|canada|mexico|brazil|são paulo"
    r"|india|bangalore|bengaluru|hyderabad|pune|chennai|gurgaon|gurugram|noida|delhi|mumbai|kolkata"
    r"|singapore|tokyo|japan|sydney|melbourne|australia|new zealand|korea|seoul|china|beijing|shanghai"
    r"|hong kong|taiwan|vietnam|philippines|manila|indonesia|malaysia|thailand"
    r"|costa rica|argentina|buenos aires|colombia|bogota|chile|peru|uruguay|south africa|nigeria|kenya|egypt"
    r"|apac|asia|dubai|tel aviv|israel"
    # non-EU Eastern Europe / Balkans / Caucasus (your choice: skip these)
    r"|ukraine|kyiv|kiev|lviv|kharkiv|odesa|dnipro|belarus|minsk|russia|moscow|moldova|chisinau"
    r"|serbia|belgrade|novi sad|bosnia|sarajevo|north macedonia|skopje|albania|tirana|montenegro|kosovo"
    r"|georgia|tbilisi|armenia|yerevan|azerbaijan|baku|turkey|türkiye|istanbul|ankara"
)
# Not real jobs: interview gigs, freelance panels, bootcamp trainers
GIG = r"interview experts?|interviewer|freelance|freelancer|contractor pool|\btrainer\b|mentor wanted|expert network"
# ... unless the location ALSO mentions Europe (e.g. "New York or Berlin")
OTHER_EUROPE = (
    r"united kingdom|\buk\b|london|france|paris|spain|madrid|barcelona|portugal|lisbon|switzerland|zurich|zürich"
    r"|italy|milan|austria|vienna|belgium|brussels|sweden|stockholm|norway|oslo|finland|helsinki|czech|prague"
    r"|estonia|tallinn|romania|bucharest|cluj|timisoara|timișoara|greece|athens|hungary|budapest|luxembourg|poland|polska|warsaw|warszawa|krakow|kraków|cracow|wroclaw|wrocław|gdansk|gdańsk|poznan|poznań|katowice|lithuania|lietuva|vilnius|kaunas|czechia|czech republic|bratislava|slovakia"
    r"|, ?(?:fr|es|pt|ch|uk|gb|it|at|be|no|cz|ro|gr|hu|pl|lt|ee|sk)\b"
)
EUROPE = r"europe|emea|\beu\b|" + OTHER_EUROPE + "|" + "|".join(MY_COUNTRIES.values())

OTHER_CLOUDS = r"\baws\b|amazon web services|\bgcp\b|google cloud"
AZURE = r"\bazure\b|\baks\b"

# Freshness: older posts get far fewer replies.
# Ads written in another language are KEPT (labelled ad-not-english, ranked a bit lower) unless they say the
# language is required. Set SKIP_NON_ENGLISH_ADS=1 to skip every non-English ad instead.
SKIP_NON_ENGLISH_ADS = os.environ.get("SKIP_NON_ENGLISH_ADS", "0") == "1"
MAX_AGE_DAYS = int(os.environ.get("MAX_AGE_DAYS") or 14)   # "Run workflow" can override it (e.g. 1 day)
# A job still listed on the company's OWN careers page is still open, so allow older posts there.
COMPANY_MAX_AGE_DAYS = int(os.environ.get("COMPANY_MAX_AGE_DAYS") or 45)
COMPANY_SOURCES = {"greenhouse", "lever", "ashby", "recruitee", "smartrecruiters", "personio", "workable",
                   "bamboohr", "teamtailor", "join", "workday", "phenom", "successfactors"}


def max_age(job: dict) -> int:
    """14 days for job boards, 45 days for a company's own careers page (unless a 1-day run is asked for)."""
    if job.get("source") in COMPANY_SOURCES and MAX_AGE_DAYS >= 14:
        return COMPANY_MAX_AGE_DAYS
    return MAX_AGE_DAYS
# Greenhouse only gives "updated_at" (not the real posting date), so we don't age-check it.
SOURCES_WITH_REAL_POST_DATE = {"arbeitnow", "lever", "ashby", "bundesagentur", "recruitee",
                               "smartrecruiters", "personio", "workable",
                               "workday", "remotive", "remoteok", "himalayas", "jobicy",
                               "nofluffjobs", "justjoin", "weworkremotely", "workingnomads", "jobindex", "itjobbank", "thehub", "eures", "jaabz", "teamtailor", "phenom", "successfactors", "cvonline", "linkedin"}


def age_in_days(job: dict) -> int | None:
    """How many days ago was this job posted? None if we don't know."""
    posted = job.get("posted_at")
    if not posted or job.get("source") not in SOURCES_WITH_REAL_POST_DATE:
        return None
    if isinstance(posted, (int, float)) or str(posted).isdigit():          # epoch seconds / ms
        seconds = float(posted) / (1000 if float(posted) > 1e11 else 1)
        return (datetime.now(timezone.utc) - datetime.fromtimestamp(seconds, timezone.utc)).days
    try:
        when = datetime.fromisoformat(str(posted).replace(" UTC", "+00:00").replace("Z", "+00:00"))
    except ValueError:
        return None
    if when.tzinfo is None:
        when = when.replace(tzinfo=timezone.utc)
    return (datetime.now(timezone.utc) - when).days


# Common little words, used to guess which language the ad is written in.
STOPWORDS = {
    "english": {"the", "and", "you", "with", "for", "our", "are", "will", "your", "we", "to", "of"},
    "german": {"und", "der", "die", "das", "mit", "für", "wir", "sie", "ist", "eine", "auf", "von", "bei", "zu"},
    "dutch": {"en", "het", "van", "een", "voor", "wij", "je", "jouw", "zijn", "op", "bij", "naar"},
    "swedish": {"och", "att", "som", "för", "med", "är", "vi", "du", "på", "av", "till", "har"},
    "danish": {"og", "at", "som", "til", "med", "er", "vi", "du", "på", "af", "har", "vores"},
    "finnish": {"ja", "on", "että", "sekä", "tai", "olet", "meidän", "työ", "tehtävä", "kanssa", "sinä", "hyvä"},
    "spanish": {"el", "la", "los", "las", "y", "de", "en", "para", "con", "nuestro", "una", "del"},
}


def guess_language(text: str) -> str:
    """Count little words of each language. The language with the most wins."""
    words = re.findall(r"[a-zäöüßåæøéñáíóú]+", text.lower())
    counts = {lang: sum(w in stop for w in words) for lang, stop in STOPWORDS.items()}
    return max(counts, key=counts.get)


def _language_required(text: str) -> str | None:
    for pattern in LANGUAGE_REQUIRED:
        for match in re.finditer(pattern, text):
            # look at ~60 characters around the match for "plus", "nice to have", ...
            nearby = text[max(0, match.start() - 60): match.end() + 60]
            if not re.search(LANGUAGE_IS_OPTIONAL, nearby):
                return match.group(0)
    return None


EMPLOYMENT_CONTRACTS = {"permanent", "uop", "employment", "employment_contract", "umowa_o_prace"}
POLISH_EMPLOYMENT = r"umow\w* o prac\w*|umowa o pracę|\buop\b|\bu ?o ?p\b|employment contract|contract of employment|permanent contract|full[- ]time employment"


# Places in India, and words that make a place count as remote.
INDIA_PLACES = r"\bindia\b|bangalore|bengaluru|hyderabad|pune|chennai|gurgaon|gurugram|noida|delhi|mumbai|kolkata"
REMOTE_WORDS = r"\bremote\b|anywhere|worldwide|apac|asia|global|any location"


# Companies whose jobs you also want in places outside lists/countries.txt (your choice, Nov 2026).
EXTRA_PLACES_FOR_COMPANY = {
    r"julius\s*baer|juliusbaer": r"switzerland|schweiz|suisse|z[uü]rich|zuerich|geneva|gen[eè]ve|lugano|basel",
}


def _extra_place_ok(job: dict, where: str) -> bool:
    who = f"{job.get('company') or ''} {job.get('url') or ''}".lower()
    return any(re.search(c, who) and re.search(p, where) for c, p in EXTRA_PLACES_FOR_COMPANY.items())


def location_dealbreaker(job: dict) -> str | None:
    """Location only: drops non-remote India roles and any place outside your target countries (lists/countries.txt).
    Also used by tools/add_email_job.py, which adds jobs by hand."""
    where = (job.get("location") or "").lower()
    # India roles count only if the place itself says remote. A source's "remote" flag is not enough:
    # #117 (Kyndryl, Bangalore, on-site) was tagged remote because of the flag.
    if re.search(INDIA_PLACES, where) and not re.search(REMOTE_WORDS, where):
        return f"on-site India role (not remote): '{job.get('location')}'"
    # Remote jobs are always welcome, wherever the company is (your choice). The other checks below
    # (no visa, local only, language, AWS/GCP-only) still apply, e.g. "Remote - US citizens only" is skipped.
    remote = job.get("remote") or re.search(r"\bremote\b|anywhere|work from home|wfh|fully distributed", where + " " + job["title"].lower())
    if remote:
        # NOMAD-VISA REMOTE: fully remote jobs you can do from India / anywhere. With a digital nomad visa
        # (Spain, Portugal, Croatia, Greece, Estonia...) you can then live in Europe while doing them.
        us_only = re.search(r"\b(us|usa|u\.s\.|united states|canada|north america|latam|americas)\b", where)
        if re.search(r"\bindia\b|\bapac\b|asia|worldwide|anywhere|global|any location|international", where) and not us_only:
            job["nomad"] = True
        # "Remote - Canada", "Remote (US)": remote but only inside a non-Europe country -> skip
        if not job.get("nomad") and re.search(NOT_EUROPE, where) and not re.search(EUROPE, where) and not re.search(r"worldwide|anywhere|global", where):
            return f"remote but outside europe only: '{job['location']}'"
        # "Remote - Spain" / "Madrid, Spain": remote but only inside a European country that isn't one of yours -> skip
        mine = any(re.search(rf"\b(?:{p})\b", where) for p in MY_COUNTRIES.values())
        if re.search(OTHER_EUROPE, where) and not mine and not job.get("nomad") and not re.search(r"europe|emea|\beu\b|worldwide|anywhere|global", where):
            return f"remote but not in my countries: '{job['location']}'"
        where = where + ", remote-ok, germany"      # passes the location checks below
    if re.search(NOT_EUROPE, where) and not re.search(EUROPE, where):
        return f"outside europe: '{job['location']}'"

    # Only your target countries (lists/countries.txt). "Remote - Europe" without one of them is skipped too.
    # German job boards often give only the city ("Ingolstadt") -> treat as Germany unless another country is named
    if job.get("source") in ("bundesagentur", "arbeitnow") and where and not re.search(OTHER_EUROPE, where):
        where += ", germany"
    if _extra_place_ok(job, where):
        return None
    if not any(re.search(rf"\b(?:{pattern})\b", where) for pattern in MY_COUNTRIES.values()):
        return f"not my countries: '{job.get('location') or 'no location'}'"
    return None


def sponsor_dealbreaker(job: dict) -> str | None:
    """Netherlands: a non-EU hire needs an IND recognised sponsor, so other NL employers are skipped.
    (If the IND list could not be downloaded, nothing is skipped.) Remote nomad jobs need no sponsor."""
    from jobhunter.scoring import find_country
    from jobhunter.sponsors import ind_sponsors, is_ind_sponsor
    if job.get("nomad") or find_country(job) != "Netherlands" or not ind_sponsors():
        return None
    if not is_ind_sponsor(job.get("company") or ""):
        return f"NL employer is not an IND recognised sponsor: '{job.get('company')}'"
    return None


def find_dealbreaker(job: dict) -> str | None:
    """Return the reason to skip this job, or None if it's fine."""
    text = (job["title"] + " " + job["description"] + " " + (job.get("location") or "")).lower()

    age = age_in_days(job)
    if age is not None and age > max_age(job):
        return f"too old: {age} days"

    if job["description"].endswith("[closed]"):
        return "closed / archived ad"

    gig = re.search(GIG, job["title"].lower())
    if gig:
        return f"gig, not a job: '{gig.group(0)}'"

    reason = location_dealbreaker(job)
    if reason:
        return reason

    reason = sponsor_dealbreaker(job)
    if reason:
        return reason

    if re.search(OTHER_CLOUDS, text) and not re.search(AZURE, text):
        cloud = re.search(OTHER_CLOUDS, text).group(0)
        return f"aws/gcp only: '{cloud}' and no Azure"

    phrase = _language_required(text)
    if phrase:
        return f"language required: '{phrase}'"

    # Optional strict mode (SKIP_NON_ENGLISH_ADS=1): skip every ad not written in English.
    if SKIP_NON_ENGLISH_ADS and len(job["description"]) >= 400:
        lang = guess_language(job["description"])
        if lang != "english":
            return f"ad not in English: '{lang}'"

    for pattern in ([] if job.get("nomad") else NO_VISA):     # nomad-visa remote jobs need no sponsorship
        m = re.search(pattern, text)
        if m:
            return f"no visa: '{m.group(0)}'"

    for pattern in LOCAL_ONLY:
        m = re.search(pattern, text)
        if m:
            return f"local only: '{m.group(0)}'"

    return None
