"""
DEBUG HELPER: peek at the raw answer from the Bundesagentur API.

Run:   py tools\\peek_bundesagentur.py

It asks for just 2 DevOps jobs and prints what the website sends back,
so we can see the real field names. (Engineers call this "debugging":
look at the real data before guessing.)
"""

import json

import requests

BASE = "https://rest.arbeitsagentur.de/jobboerse/jobsuche-service"

for version in ("v6", "v4"):
    url = f"{BASE}/pc/{version}/jobs"
    response = requests.get(url, params={"was": "DevOps", "size": 2},
                            headers={"X-API-Key": "jobboerse-jobsuche"}, timeout=30)
    print(f"\n===== {version}: status {response.status_code} =====")
    try:
        print(json.dumps(response.json(), ensure_ascii=False, indent=1)[:1500])
    except ValueError:
        print(response.text[:500])


# ---- Step 2: try the "job details" call for the first job ----
import base64

first = requests.get(f"{BASE}/pc/v6/jobs", params={"was": "DevOps", "size": 1},
                     headers={"X-API-Key": "jobboerse-jobsuche"}, timeout=30).json()
refnr = (first.get("ergebnisliste") or [{}])[0].get("referenznummer")
print(f"\n===== details for {refnr} =====")
if refnr:
    encoded = base64.b64encode(refnr.encode()).decode()
    for version in ("v6", "v5", "v4", "v3"):
        r = requests.get(f"{BASE}/pc/{version}/jobdetails/{encoded}",
                         headers={"X-API-Key": "jobboerse-jobsuche"}, timeout=30)
        print(f"--- {version}: status {r.status_code}")
        if r.ok:
            data = r.json()
            print("fields:", list(data.keys()))
            print(json.dumps(data, ensure_ascii=False)[:600])
            break
