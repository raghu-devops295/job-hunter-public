"""
Source #5: Bundesagentur fuer Arbeit (Germany's official job agency).

The biggest job database in Germany. Free API. The "API key" below is a PUBLIC
key that everyone uses - it is not a secret.

Two-step process:
    1. SEARCH  -> gives only title, employer, city (no description)
    2. DETAILS -> one extra call per job to get the description
We only do step 2 for jobs whose title already looks right, to stay fast and polite.
"""

import base64

from jobhunter.sources.common import get_json, strip_html

BASE = "https://rest.arbeitsagentur.de/jobboerse/jobsuche-service"
KEY = {"X-API-Key": "jobboerse-jobsuche"}


def search(keyword: str, days: int = 7, size: int = 100) -> list[dict]:
    """Find jobs (only basic info). `days` = only jobs published in the last N days."""
    params = {"was": keyword, "angebotsart": 1, "veroeffentlichtseit": days, "size": size}
    data = None
    # The agency retires old API versions now and then, so try the newest first.
    # For SEARCH only v6 works (checked 30 Oct 2026)
    for version in ("v6", "v4"):
        try:
            data = get_json(f"{BASE}/pc/{version}/jobs", headers=KEY, params=params)
            if data is not None:
                break
        except Exception:
            continue
    if data is None:
        raise RuntimeError("no API version answered (v6/v4)")
    jobs = []
    # v6 calls the list "ergebnisliste"; older versions called it "stellenangebote"
    for j in (data or {}).get("ergebnisliste") or (data or {}).get("stellenangebote") or []:
        refnr = j.get("referenznummer") or j.get("refnr")
        if not refnr:
            continue

        # City: v6 -> stellenlokationen[0].adresse.ort ; old -> arbeitsort.ort
        places = j.get("stellenlokationen") or []
        city = ((places[0].get("adresse") or {}).get("ort") if places else None) \
            or (j.get("arbeitsort") or {}).get("ort")

        # Salary (v6 bonus!): yearly range in EUR, when the employer shares it
        low, high = j.get("gehaltsspanneVon"), j.get("gehaltsspanneBis")
        salary = None
        if low or high:
            salary = {"min": low, "max": high, "currency": "EUR",
                      "period": "year" if j.get("verguetungsangabe") == "JAHRESGEHALT" else "other"}

        jobs.append({
            "id": f"bundesagentur:{refnr}",
            "source": "bundesagentur",
            "refnr": refnr,
            "title": j.get("stellenangebotsTitel") or j.get("titel") or j.get("hauptberuf") or "",
            "company": j.get("firma") or j.get("arbeitgeber") or "",
            "location": ", ".join(filter(None, [city, "Germany"])),
            "remote": False,
            "url": j.get("externeUrl") or f"https://www.arbeitsagentur.de/jobsuche/jobdetail/{refnr}",
            "tags": [],
            "description": "",   # filled in by add_description() later
            "posted_at": j.get("datumErsteVeroeffentlichung") or j.get("aktuelleVeroeffentlichungsdatum"),
            "salary": salary,
        })
    return jobs


def add_description(job: dict) -> None:
    """Step 2: fetch the full description for ONE job (changes the job in place)."""
    encoded = base64.b64encode(job["refnr"].encode()).decode()
    data = {}
    # For DETAILS only v4 works (checked with tools/peek_bundesagentur.py on 30 Oct 2026)
    for version in ("v4", "v6"):
        try:
            data = get_json(f"{BASE}/pc/{version}/jobdetails/{encoded}", headers=KEY) or {}
            if data:
                break
        except Exception:
            continue
    job["description"] = strip_html(data.get("stellenangebotsBeschreibung") or data.get("stellenbeschreibung") or "")


def fetch(keywords: list[str]) -> list[dict]:
    jobs = []
    for keyword in keywords:
        try:
            jobs.extend(search(keyword))
        except Exception as error:
            print(f"   ! bundesagentur '{keyword}': error {error}")
    return jobs
