"""
SALARY ADVISOR - "what should I ask for this job?"

How it works (no AI, no cost - just a table + simple maths):
    1. Find the city/country in the job location        -> market band for a SENIOR DevOps/Platform engineer
    2. Adjust the band for the job level in the title   -> Lead/Staff/Principal +10%, Junior/Mid -18%
    3. Pick a point inside the band from your skill fit -> strong fit = upper part of the band
    4. If the ad itself states a salary, that wins      -> ask near the TOP of the advertised range
    5. Add the visa minimum (Blue Card etc.) and local notes (13th month, pension, holiday pay)

The bands are GROSS ANNUAL BASE salary (no bonus), for ~7 years of experience, researched Nov 2026 from
careercheck.io, Morgan McKinley, upreer.ch, Bulldogjob, jobrise.io and Payscale, and kept on the
conservative side. They are estimates - update them here when you learn real offers.
"""

import re

# (match words in the location, label, currency, low, high)   - senior band, gross per year
BANDS = [
    # Germany
    (r"m[uü]nchen|munich", "Munich", "EUR", 88_000, 120_000),
    (r"frankfurt", "Frankfurt", "EUR", 85_000, 115_000),
    (r"berlin", "Berlin", "EUR", 80_000, 110_000),
    (r"hamburg", "Hamburg", "EUR", 78_000, 108_000),
    (r"stuttgart|d[uü]sseldorf|k[oö]ln|cologne", "Stuttgart/Düsseldorf/Cologne", "EUR", 76_000, 105_000),
    (r"germany|deutschland|\bde\b|leipzig|dresden|hannover|n[uü]rnberg|nuremberg|bonn|karlsruhe|mannheim|essen|dortmund|bremen",
     "Germany", "EUR", 72_000, 100_000),
    # Netherlands
    (r"amsterdam", "Amsterdam", "EUR", 80_000, 112_000),
    (r"netherlands|nederland|rotterdam|utrecht|eindhoven|den haag|the hague|delft", "Netherlands", "EUR", 72_000, 100_000),
    # Ireland
    (r"dublin", "Dublin", "EUR", 82_000, 118_000),
    (r"ireland|cork|galway|limerick", "Ireland", "EUR", 72_000, 100_000),
    # Denmark (gross incl. no pension - employers add 8-12% pension on top)
    (r"copenhagen|k[oø]benhavn|denmark|danmark|aarhus", "Denmark", "DKK", 650_000, 900_000),
    # Switzerland (often paid as 13 monthly salaries - the yearly total is what counts)
    (r"z[uü]rich", "Zurich", "CHF", 140_000, 185_000),
    (r"switzerland|schweiz|suisse|basel|geneva|gen[eè]ve|bern|lausanne|zug|gland|\bch\b", "Switzerland", "CHF", 130_000, 175_000),
    # Poland (employment contract = UoP gross; B2B invoices are usually ~15-20% higher)
    (r"warsaw|warszawa|krak[oó]w|cracow|wroc[lł]aw|gda[nń]sk|pozna[nń]|poland|polska|katowice|[lł][oó]d[zź]",
     "Poland", "PLN", 260_000, 360_000),
    # Other Europe
    (r"london", "London", "GBP", 75_000, 105_000),
    (r"united kingdom|\buk\b|england|manchester|edinburgh|bristol|cambridge|glasgow", "United Kingdom", "GBP", 60_000, 85_000),
    (r"stockholm|sweden|sverige|gothenburg|g[oö]teborg|malm[oö]", "Sweden", "SEK", 660_000, 900_000),
    (r"oslo|norway|norge", "Norway", "NOK", 800_000, 1_050_000),
    (r"helsinki|finland", "Finland", "EUR", 62_000, 85_000),
    (r"vienna|wien|austria|[oö]sterreich|graz|linz", "Austria", "EUR", 65_000, 90_000),
    (r"brussels|bruxelles|belgium|belgi|antwerp|ghent", "Belgium", "EUR", 65_000, 90_000),
    (r"luxembourg", "Luxembourg", "EUR", 75_000, 100_000),
    (r"paris|france|lyon|toulouse|nantes", "France", "EUR", 62_000, 88_000),
    (r"madrid|barcelona|spain|espa[nñ]a|valencia|m[aá]laga", "Spain", "EUR", 52_000, 78_000),
    (r"lisbon|lisboa|porto|portugal", "Portugal", "EUR", 45_000, 70_000),
    (r"milan|milano|rome|roma|italy|italia|turin|torino", "Italy", "EUR", 50_000, 72_000),
    (r"prague|praha|czech|brno", "Czechia", "EUR", 50_000, 75_000),
    (r"vilnius|kaunas|lithuania|lietuva", "Lithuania", "EUR", 50_000, 72_000),
    (r"tallinn|tartu|estonia|eesti", "Estonia", "EUR", 55_000, 78_000),
    (r"riga|latvia", "Latvia", "EUR", 45_000, 65_000),
    # Gulf: salaries are tax-free; housing/transport allowances are often on top of base - ask for the full package
    (r"dubai|abu dhabi|sharjah|united arab emirates|\buae\b", "United Arab Emirates", "AED", 240_000, 420_000),
    (r"riyadh|jeddah|dammam|khobar|dhahran|neom|saudi", "Saudi Arabia", "SAR", 240_000, 420_000),
    (r"bucharest|romania|cluj|timi[sș]oara|ia[sș]i|bra[sș]ov|\bro\b|budapest|hungary|sofia|bulgaria|athens|greece", "South-East Europe", "EUR", 40_000, 65_000),
]
FALLBACK = ("Europe (location unclear)", "EUR", 65_000, 95_000)

SYMBOL = {"AED": "AED ", "SAR": "SAR ", "EUR": "€", "GBP": "£", "CHF": "CHF ", "DKK": "DKK ", "SEK": "SEK ", "NOK": "NOK ", "PLN": "PLN "}

# Visa minimums 2026 (gross per year) - an offer below these can't get the work permit
VISA = {
    "EUR-DE": "EU Blue Card minimum 2026: €50,700/yr (€45,934 for shortage jobs incl. IT).",
    "EUR-NL": "Highly-skilled-migrant minimum 2026 for you (under 30): €4,357/month = €52,284/yr, excluding the 8% "
              "holiday pay (30+: €5,942/month). Employer must be an IND recognised sponsor - decision in ~2 weeks.",
    "EUR-FI": "Finland fast track: decision target 14 days for specialists / EU Blue Card (apply in Enter Finland).",
    "EUR-LT": "Lithuania EU Blue Card: decision up to 1 month (15 days express, €320); apply from India via VFS.",
    "EUR-EE": "Estonia EU Blue Card minimum 2026: €35,664/yr for IT (shortage field); decision up to ~2 months.",
    "SEK-SE": "Sweden: salary must be at least 90% of the median (SEK 34,470/month from June 2026); decision ~1-2 months.",
    "DKK-DK": "Denmark Fast-Track (certified employer): pay limit DKK 552,000/yr; decision ~1 month.",
    "PLN-PL": "Poland: work permit + D visa often takes 4-8 months from India - ask how long their last non-EU hire took and whether they can start you remotely from India meanwhile.",
    "EUR-CZ": "Czechia: ask if the employer is in the government 'Highly Qualified Worker' programme - it gets priority processing; without it, consulate appointments in India are scarce.",
    "EUR-AT": "Austria: EU Blue Card / Red-White-Red card; the authority's evaluation usually takes several weeks.",
    "AED-AE": "UAE: the employer sponsors your work visa; get your degree certificates attested (India MEA + UAE embassy) early - it takes weeks.",
    "SAR-SA": "Saudi Arabia: the employer sponsors your work visa (iqama); degree certificates must be attested (India MEA + Saudi embassy) - start early.",
    "EUR-IE": "Critical Skills Employment Permit minimum (from 1 Mar 2026): €40,904/yr with a relevant degree.",
}
COUNTRY_OF = {"Munich": "DE", "Frankfurt": "DE", "Berlin": "DE", "Hamburg": "DE", "Stuttgart/Düsseldorf/Cologne": "DE",
              "Germany": "DE", "Amsterdam": "NL", "Netherlands": "NL", "Dublin": "IE", "Ireland": "IE",
              "Finland": "FI", "Lithuania": "LT", "Estonia": "EE", "Sweden": "SE", "Denmark": "DK", "Poland": "PL",
              "Czechia": "CZ", "Austria": "AT", "United Arab Emirates": "AE", "Saudi Arabia": "SA"}

NOTES = {
    "NL": "On top: 8% holiday allowance. Ask HR whether you qualify for the 30% tax ruling.",
    "DK": "On top: employer pension, usually 8-12% of salary - compare offers including it.",
    "CH": "Often paid as 13 monthly salaries - always compare the yearly total.",
    "PL": "Band is for an employment contract (UoP, gross). For B2B, ask ~15-20% more (no paid leave/benefits).",
    "SE": "On top: occupational pension (~4.5%+) and 25+ days holiday.",
    "FI": "On top: holiday bonus (lomaraha, ~half a month's pay) at most employers.",
    "AE": "Tax-free. Compare the full package: base + housing + transport allowance, flights home, medical, end-of-service gratuity.",
    "SA": "Tax-free. Compare the full package: base + housing + transport allowance, flights home, medical, end-of-service gratuity.",
    "DE": "Bonus, pension and benefits often add €5-15K on top of base.",
}


def _fmt(currency: str, amount: float) -> str:
    return f"{SYMBOL.get(currency, currency + ' ')}{round(amount / 1000):,}K"


def find_band(location: str):
    text = (location or "").lower()
    for pattern, label, currency, low, high in BANDS:
        if re.search(pattern, text):
            return label, currency, low, high
    return FALLBACK


def level_of(title: str) -> tuple[str, float]:
    t = (title or "").lower()
    if re.search(r"\b(principal|staff|lead|head|architect|manager)\b", t):
        return "Lead/Staff level", 1.10
    if re.search(r"\b(junior|jr\.?|graduate|entry|associate|mid|medior|intermediate)\b|\b(i|ii)\b$", t):
        return "Junior/Mid level", 0.82
    if re.search(r"\b(senior|sr\.?|iii|expert|specialist)\b", t):
        return "Senior level", 1.0
    return "Level not stated (treated as senior)", 1.0


# "€80,000 - €100,000", "80.000 – 95.000 EUR", "CHF 140k-170k", "£70k to £90k"
_RANGE = re.compile(
    r"(?P<c1>€|eur|£|gbp|chf|dkk|sek|pln)?\s*(?P<a>\d{2,3}(?:[.,\s]?\d{3})|\d{2,3}\s?k)\s*(?P<c2>€|eur|£|gbp|chf|dkk|sek|pln)?"
    r"\s*(?:-|–|—|to|bis)\s*"
    r"(?P<c3>€|eur|£|gbp|chf|dkk|sek|pln)?\s*(?P<b>\d{2,3}(?:[.,\s]?\d{3})|\d{2,3}\s?k)\s*(?P<c4>€|eur|£|gbp|chf|dkk|sek|pln)?",
    re.I)
_CUR = {"€": "EUR", "eur": "EUR", "£": "GBP", "gbp": "GBP", "chf": "CHF", "dkk": "DKK", "sek": "SEK", "pln": "PLN"}


def _num(text: str) -> int:
    text = text.lower().replace(" ", "")
    if text.endswith("k"):
        return int(text[:-1]) * 1000
    return int(re.sub(r"[.,]", "", text))


def salary_from_text(description: str) -> dict | None:
    """Find a yearly salary range written in the ad (only if a currency is next to it)."""
    for m in _RANGE.finditer(description or ""):
        cur = next((m.group(g) for g in ("c1", "c2", "c3", "c4") if m.group(g)), None)
        if not cur:
            continue
        low, high = _num(m.group("a")), _num(m.group("b"))
        if 25_000 <= low < high <= 1_500_000 and high <= low * 2:
            return {"min": low, "max": high, "currency": _CUR[cur.lower()], "period": "year"}
    return None


def advise(job: dict) -> dict:
    """Return {'ask': '...', 'market': '...', 'why': '...', 'visa': '...', 'note': '...'} for one job."""
    label, currency, low, high = find_band(job.get("location", ""))
    level, factor = level_of(job.get("title", ""))
    low, high = low * factor, high * factor

    fit = (job.get("fit") or {}).get("fit")
    point = 0.55                                  # middle-upper part of the band by default
    if fit is not None:
        point = 0.75 if fit >= 75 else 0.6 if fit >= 60 else 0.45
    ask = low + point * (high - low)
    top = min(ask * 1.07, max(high * 1.03, ask))      # upper end of the "ask" range
    floor = max(low, ask * 0.9)                        # walk-away point

    advertised = job.get("salary") or salary_from_text(job.get("description", ""))
    why = f"{level}, skill fit {fit if fit is not None else '?'}"
    if advertised and advertised.get("period") == "year" and advertised.get("max"):
        a_low, a_high = advertised.get("min") or advertised["max"] * 0.85, advertised["max"]
        currency = advertised.get("currency", currency)
        ask = a_low + 0.85 * (a_high - a_low)     # the ad wins: ask near the top of its own range
        top, floor = a_high, max(a_low, ask * 0.9)
        why = f"the ad states {_fmt(currency, a_low)}–{_fmt(currency, a_high)}; aim near its top"

    country = COUNTRY_OF.get(label, {"Denmark": "DK", "Zurich": "CH", "Switzerland": "CH"}.get(label, label))
    result = {
        "ask": f"{_fmt(currency, ask)} – {_fmt(currency, top)} gross / year",
        "minimum": f"don't go below {_fmt(currency, floor)}",
        "market": f"{label}: {_fmt(currency, low)} – {_fmt(currency, high)} ({level.split(' (')[0].lower()})",
        "why": why,
        "visa": VISA.get(f"{currency}-{country}", ""),
        "note": NOTES.get(country, ""),
    }
    return result


def markdown(job: dict) -> str:
    """A small block for the GitHub issue."""
    s = advise(job)
    lines = [f"**💶 Salary to ask: {s['ask']}**  ({s['minimum']})",
             f"<sub>Market band {s['market']} · based on {s['why']}</sub>"]
    if s["visa"]:
        lines.append(f"<sub>🛂 {s['visa']}</sub>")
    if s["note"]:
        lines.append(f"<sub>ℹ️ {s['note']}</sub>")
    lines.append("<sub>Estimate from public 2026 salary surveys - check Glassdoor/levels.fyi for this company before you answer.</sub>")
    return "\n".join(lines)
