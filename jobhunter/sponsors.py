"""
VISA-FRIENDLY EMPLOYERS

Netherlands: the IND publishes every "recognised sponsor" (companies allowed to hire
Highly Skilled Migrants with a fast permit, usually 2-4 weeks). We download that list once a
month into data/ind_sponsors.txt and give jobs from those companies extra points.

Denmark: SIRI publishes the companies certified for the Fast-Track scheme (permit in ~1 month,
"Quick Job Start" possible). Same idea: data/dk_certified.txt, refreshed monthly.

(Ireland's "Trusted Partner" list no longer exists - all employers now use the same route.
 Finland's fast track is open to any employer, so there is no list to check.)

If a page can't be read, the robot simply carries on without the bonus.
"""

import html
import re
import time
from pathlib import Path

import requests

from jobhunter.sources.common import HEADERS

IND_URL = "https://ind.nl/en/public-register-recognised-sponsors/public-register-work"
CACHE = Path("data/ind_sponsors.txt")
MAX_AGE_DAYS = 30

# Words that differ between "Adyen N.V." on the IND list and "adyen" on a job board
_NOISE = (r"\b(b\.?v\.?|n\.?v\.?|gmbh|ltd|limited|inc|holding|holdings|group|nederland|netherlands|the|europe|international"
          r"|a/s|aps|p/s|i/s|k/s|danmark|denmark)\b")


def normalise(name: str) -> str:
    name = html.unescape(name or "").lower().replace("&", " and ")
    name = re.sub(_NOISE, " ", name)
    return re.sub(r"[^a-z0-9]+", "", name)


def _download() -> list[str]:
    page = requests.get(IND_URL, headers=HEADERS, timeout=60).text
    rows = re.findall(r"<td[^>]*>(.*?)</td>\s*<td[^>]*>\s*(\d{8})\s*</td>", page, re.S | re.I)
    names = [re.sub(r"<[^>]+>", " ", n).strip() for n, _ in rows]
    if not names:   # page layout changed -> fall back to "Name 12345678" lines in the plain text
        text = html.unescape(re.sub(r"<[^>]+>", "\n", page))
        names = [m.group(1).strip() for m in re.finditer(r"^\s*(.+?)\s+\d{8}\s*$", text, re.M)]
    return names


_cache: set[str] | None = None


def ind_sponsors() -> set[str]:
    """Normalised names of all IND recognised sponsors (work). Empty set if unavailable."""
    global _cache
    if _cache is not None:
        return _cache
    fresh = CACHE.exists() and (time.time() - CACHE.stat().st_mtime) < MAX_AGE_DAYS * 86400
    if not fresh:
        try:
            names = _download()
            if len(names) > 500:                       # sanity check: the real list has thousands
                CACHE.parent.mkdir(exist_ok=True)
                CACHE.write_text("\n".join(names), encoding="utf-8")
                print(f"   IND sponsor list updated: {len(names)} companies")
        except Exception as error:
            print(f"   (could not update IND sponsor list: {error})")
    names = CACHE.read_text(encoding="utf-8").splitlines() if CACHE.exists() else []
    _cache = {normalise(n) for n in names if normalise(n)}
    return _cache


def is_ind_sponsor(company: str) -> bool:
    key = normalise(company)
    if len(key) < 3:
        return False
    sponsors = ind_sponsors()
    if key in sponsors:
        return True
    # "adyen" vs "adyennv" / "bunq" vs "bunqbv" etc.: allow the sponsor name to start with the company name
    return len(key) >= 5 and any(s.startswith(key) for s in sponsors)


# ---------------- Denmark: SIRI certified companies (Fast-Track scheme) ----------------
DK_URL = "https://www.nyidanmark.dk/en-GB/Words-and-concepts/SIRI/Certified-companies"
DK_CACHE = Path("data/dk_certified.txt")
_COMPANY_SUFFIX = r"\b(A/S|ApS|P/S|I/S|K/S|SE|AB|AS|Ltd\.?|Limited|GmbH|Inc\.?|B\.V\.|S\.A\.|LLC|Oy|filial)\b"
_dk_cache: set[str] | None = None


def _download_dk() -> list[str]:
    page = requests.get(DK_URL, headers=HEADERS, timeout=60).text
    text = html.unescape(re.sub(r"<[^>]+>", "\n", page))
    lines = [re.sub(r"\s+", " ", l).strip() for l in text.splitlines()]
    return sorted({l for l in lines if 3 <= len(l) <= 90 and re.search(_COMPANY_SUFFIX, l)})


def dk_certified() -> set[str]:
    global _dk_cache
    if _dk_cache is not None:
        return _dk_cache
    fresh = DK_CACHE.exists() and (time.time() - DK_CACHE.stat().st_mtime) < MAX_AGE_DAYS * 86400
    if not fresh:
        try:
            names = _download_dk()
            if len(names) > 200:                       # the real list has several hundred companies
                DK_CACHE.parent.mkdir(exist_ok=True)
                DK_CACHE.write_text("\n".join(names), encoding="utf-8")
                print(f"   Danish Fast-Track (SIRI certified) list updated: {len(names)} companies")
            else:
                print(f"   (Danish certified list looked wrong: only {len(names)} names - not saved)")
        except Exception as error:
            print(f"   (could not update Danish certified list: {error})")
    names = DK_CACHE.read_text(encoding="utf-8").splitlines() if DK_CACHE.exists() else []
    _dk_cache = {normalise(n) for n in names if normalise(n)}
    return _dk_cache


def is_dk_certified(company: str) -> bool:
    key = normalise(company)
    if len(key) < 3:
        return False
    certified = dk_certified()
    return key in certified or (len(key) >= 5 and any(s.startswith(key) for s in certified))


# ---------------- Companies known to relocate people (community list) ----------------
# Source: github.com/AndrewStetsenko/tech-jobs-with-relocation (companies in your countries) + firms that
# relocated engineers in your tracker. Jobs from these get a small bonus.
RELOCATION_FRIENDLY = {normalise(n) for n in """
Applike Blinkist Bol Catawiki Coolblue CreativeFabrica ePages EVBox FINN FlowTraders Gnosis Highsnobiety HomeToGo
HousingAnywhere JOIN JustEatTakeaway Lemonade Mollie movingimage NavVis Neocom Oda Payrails Picnic Queue-it Reaktor
Scout24 Shape SimScale Smartly Smartlyio Solvians SoundCloud Stream TactileGames LEGO Vimcar Ziegert Zound Adyen
Booking Kyndryl Nebius IMC Optiver Elastic MongoDB Doctolib Zalando DeliveryHero N26 Wolt Supercell Spotify Klarna
""".split()}


def is_relocation_friendly(company: str) -> bool:
    key = normalise(company)
    return len(key) >= 3 and any(key == r or (len(key) >= 5 and key.startswith(r)) for r in RELOCATION_FRIENDLY)
