"""
DISCOVERY TOOL: finds which hiring system each company uses.

Run:   py tools\\find_companies.py

For every name in CANDIDATES it tries all 7 hiring systems (Greenhouse, Lever, Ashby,
Recruitee, SmartRecruiters, Personio, Workable) and prints the ones that answer, with how
many jobs and how many DevOps/Platform/Cloud titles they have right now.
At the end it prints lists you can paste into jobhunter/companies.py.

Add any company you like to CANDIDATES (lowercase, no spaces - try the name as it appears
in its careers URL, e.g. "trade-republic" or "traderepublic").
"""

import argparse
import re
import sys
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))   # so "jobhunter" can be imported

from jobhunter import companies                                    # noqa: E402
from jobhunter.scoring import MY_ROLE_IN_TITLE                     # noqa: E402
from jobhunter.sources.company_boards import FETCHERS              # noqa: E402

CANDIDATES = [
    # Czechia (Prague / Brno / Ostrava - 3-5h from Wroclaw) and Austria (Vienna)
    "kiwicom", "kiwi", "rohlik", "apify", "emplifi", "gendigital", "avast", "jetbrains", "stormware", "smartsupp",
    "pipetech", "ceskasporitelna", "kentico", "mewssystems", "notino", "alza", "sewio", "flowmon", "y-soft", "ysoft",
    "bitpanda", "dynatrace", "gostudent", "tractive", "refurbed", "adverity", "storyblok", "bitmovin", "anyline",
    "kununu", "runtastic", "frequentis", "tttech", "celum", "eversports", "hokify", "byrd", "prewave",
    # Eastern Germany (Dresden / Leipzig / Berlin - 3-5h from Wroclaw)
    "staffbase", "spreadshirt", "unister", "check24", "ottonova", "cloudflight", "scalable", "scalablecapital",
    "zalando", "delivery-hero", "deliveryhero", "babbel", "solarisbank", "solaris", "raisin", "taxfix", "pitch", "ecosia",
    # Netherlands
    "mollie", "bitvavo", "picnic", "catawiki", "tiqets", "bird", "messagebird", "mews", "backbase",
    "abnamro", "ing", "rabobank", "adevinta", "elastic", "miro", "bolt", "takeaway", "justeattakeaway",
    # Germany
    "personio", "taxfix", "deliveryhero", "traderepublic", "trade-republic", "raisin", "solaris",
    "solarisbank", "flink", "enpal", "1komma5grad", "zalando", "idealo", "check24", "scout24",
    "auto1", "babbel", "blinkist", "commerzbank", "deutschebank", "allianz", "bosch", "boschgroup",
    "siemens", "sap", "mediamarktsaturn", "otto", "ottogroup", "tradeworx", "wefox", "clark",
    "staffbase", "sennder", "getsafe", "moss", "pliant", "qonto", "upvest", "scalable", "scalablecapital",
    # Ireland
    "workday", "hubspot", "fenergo", "wayflyer", "tines", "flipdish", "aib", "bankofireland",
    # Poland
    "allegro", "docplanner", "brainly", "revolut", "ing-hubs", "inghubspoland", "ocado",
    # Denmark / Nordics
    "pleo", "lunar", "danskebank", "trustpilot", "unity", "zendesk", "klarna", "spotify", "wolt",
    # Switzerland
    "ubs", "scandit", "nexthink", "beekeeper", "wefox", "on", "onrunning", "swissquote", "postfinance",
    # From LinkedIn job-alert emails (Nov 2026): employers and recruitment agencies
    "a2g", "akkodis", "alten", "amadeus-fire", "amadeusfire", "astronomer", "attio", "baader-bank", "baaderbank", "cisco", "computer-futures", "computerfutures", "cowmanager", "darwin-recruitment", "darwinrecruitment", "deutsche-bank", "deutschebank", "doghouse-recruitment", "doghouserecruitment", "everience", "exa", "experis", "flatpay", "fruition-group", "fruitiongroup", "good-company", "goodcompany", "guidewire", "harvey-nash", "harveynash", "hays", "it-search", "itility", "itsearch", "jefferson-frank", "jeffersonfrank", "kelvion", "layover-solutions", "layoversolutions", "lepaya", "lunar", "luxoft", "matomo", "mckesson", "michael-page", "michaelpage", "n-ix", "n26", "nigel-frank", "nigelfrank", "nix", "rabobank", "raisin", "randstad", "rapidratings", "redcare", "redcare-pharmacy", "redcarepharmacy", "shop-apotheke", "shopapotheke", "simon-kucher", "simonkucher", "sioux-technologies", "siouxtechnologies", "symphonyai", "taskverse", "trade-republic", "traderepublic", "understanding-recruitment", "understandingrecruitment", "wert-group", "wertgroup",
    # Ireland: large tech & finance firms with Dublin hubs (fast Critical Skills permits)
    "stripe", "intercom", "squarespace", "toast", "toasttab", "etsy", "dropbox", "workhuman", "evervault",
    "cloudflare", "twilio", "datadog", "okta", "coinbase", "shopify", "airbnb", "pinterest", "doordash",
    "github", "zalando", "statestreet", "citi", "bnymellon", "fidelity", "northerntrust", "susquehanna",
    "virtu", "stripe-ireland", "kraken", "paypal", "salesforce", "workday", "riot", "riotgames", "fiserv",
    "globalpayments", "fexco", "pointy", "manna", "tines", "wayflyer", "flipdish", "fenergo", "teamwork",
    # Netherlands: IND recognised sponsors on readable job boards
    "booking", "bol", "coolblue", "wetransfer", "mambu", "framer", "tomtom", "channable", "lightspeed",
    "polarsteps", "sendcloud", "exact", "nn", "aegon", "abnamro", "ing", "asml", "philips", "ahold",
    "fastned", "bitfury", "vandebron", "bux", "ohpen", "knab", "funda", "otrium", "trengo", "studocu",
    # From job-alert emails (LinkedIn/Monster, Nov 2)
    "xebia", "mfgroup", "mf-group", "onwelo", "mastercard", "isaraerospace", "isar-aerospace", "vodafone",
    "unzer", "trellix", "wertgroup", "baaderbank", "simonkucher", "luxoftglobal", "kelviongroup", "flatpayaps",
    # Remote / EU-wide
    "clickhouse", "mollie", "doctolib", "contentsquare", "datadog", "hashicorp", "grafanalabs",
    # added 2 Nov 2026: more NL/DE/IE/PL/DK + AI/infra companies
    "adyen", "bunq", "mendix", "lightyear", "nebius", "eneco", "wehkamp", "dept", "databricks", "snowflake", "confluent", "mongodb", "gitlab", "productboard", "celonis", "n8n", "deepl", "aleph-alpha", "alephalpha", "helsing", "quantco", "getyourguide", "contentful", "sumup", "hellofresh", "trivago", "freenow", "flix", "commercetools", "ionos", "chrono24", "parloa", "black-forest-labs", "blackforestlabs", "langfuse", "zeiss", "infineon", "cariad", "mytheresa", "tier", "qualtrics", "glofox", "kitman-labs", "kitmanlabs", "phorest", "ding", "aryza", "spacelift", "netguru", "stxnext", "stx-next", "10clouds", "booksy", "synerise", "packhelp", "rtbhouse", "livechat", "text", "software-mind", "softwaremind", "spyrosoft", "billennium", "intive", "codete", "deviniti", "vercom", "growbots", "ramp", "templafy", "issuu", "vivino", "toogoodtogo", "too-good-to-go", "netcompany", "saxobank", "dixa", "planday", "queue-it", "queueit", "corti", "visma", "mistral", "cohere", "huggingface", "elevenlabs", "synthesia", "canonical", "pulumi", "chainguard", "sysdig", "gitpod", "tailscale",
    # added 3 Nov 2026 from LinkedIn job posts (DevOps/Platform/SRE/Azure, NL/DE/IE/PL/DK, past week)
    "schubergphilis", "schuberg-philis", "centrica", "centricaenergy", "keepit", "wpp", "bwi", "akamai", "graphcore", "bankdata", "velux", "tno", "cgi", "porsche-consulting", "merative", "sprinklr", "nordea", "kuehne-nagel", "euroclear", "agileengine", "astek", "rib-software", "ribsoftware", "clerkio", "clerk", "sentia", "jndata", "unit-it", "twoday", "quantumblack", "devoteam", "ducklabs", "ampere", "togetherai", "together-ai", "doxis", "qualcomm", "dustin", "jakala", "computacenter", "compugroup", "cgm", "applied-intuition", "appliedintuition", "voize", "acuity", "fis", "bloomberg", "intersystems", "medtronic", "opentext", "cognism", "griddynamics", "grid-dynamics", "sii", "siipoland", "transeu", "trans-eu", "spirii", "mjolner", "bestseller", "stibo", "stibodx", "nnit", "signicat", "luscii", "edsn", "optics11", "thales", "thunderbird", "imc", "imctrading", "onlinepaymentplatform", "datasnipper", "leaseweb", "linkit", "brunel", "soptim", "rabot", "rabotenergy", "expleo", "adesso", "stackit", "schwarzdigits", "schwarz-digits", "schufa", "testo", "westernacher", "inovex", "katapult", "rulemapping", "livekit", "ripple", "keepersecurity", "keeper", "telnyx", "dnb", "mcafee", "netapp", "f5", "fivetran", "castai", "cast-ai", "zinkworks", "fineos", "pepperadvantage", "demant", "concentrix", "globallogic", "lumapps", "remitly", "addepar", "moderna", "roche", "simcorp", "patrianna", "proxify", "signify", "renesas", "wpengine", "frontiers", "hso", "codefield", "maisa", "optiver", "flowtraders", "flow-traders", "adyen-careers",
    # added 3 Nov 2026: Finland, Lithuania, Sweden, Estonia
    "supercell", "rovio", "relexsolutions", "relex", "aiven", "smartly", "smartlyio", "ouraring", "oura", "varjo", "iceye", "swappie", "sanoma", "withsecure", "reaktor", "futurice", "solita", "vincit", "elisa", "upcloud", "polar", "yousician", "enfuce", "holvi", "maventa", "kone", "nokia", "wartsila", "hiq", "siili", "gofore", "nitor", "tietoevry", "visma-solutions", "vinted", "nordsecurity", "nord-security", "kilohealth", "kilo-health", "oxylabs", "tesonet", "hostinger", "telesoftas", "devbridge", "baltic-amadeus", "nasdaq", "westernunion", "sebgroup", "seb", "swedbank", "ignitis", "euromonitor", "paysera", "mano-bank", "revolut-lithuania", "cast", "cognizant", "king", "mojang", "epidemicsound", "epidemic-sound", "voi", "tink", "truecaller", "einride", "sinch", "kry", "livi", "trustly", "zettle", "budbee", "qliro", "avanza", "tibber", "mentimeter", "hemnet", "storytel", "polestar", "ericsson", "northvolt", "embark", "paradoxinteractive", "paradox", "wise", "transferwise", "pipedrive", "veriff", "playtech", "starshiptechnologies", "starship", "glia", "testlio", "katanamrp", "katana", "cleveron", "nortal", "helmes", "twilio-estonia", "skeleton", "skeletontech",
    # added 3 Nov 2026: companies known to offer relocation (github.com/AndrewStetsenko/tech-jobs-with-relocation)
    "creativefabrica", "evbox", "finn", "gnosis", "highsnobiety", "hometogo", "housinganywhere", "join", "lemonade", "movingimage", "navvis", "neocom", "oda", "payrails", "shape", "simscale", "solvians", "soundcloud", "stream", "getstream", "tactilegames", "lego", "vimcar", "ziegertgroup", "applike", "applikegroup", "epages", "zound",
]

ALREADY = {name for name in companies.GREENHOUSE + companies.LEVER + companies.ASHBY + companies.RECRUITEE
           + companies.SMARTRECRUITERS + companies.PERSONIO + companies.WORKABLE
           + companies.BAMBOOHR + companies.TEAMTAILOR + companies.JOIN}


# Extra name lists in lists/*_companies.txt (comma/line separated, '#' = comment) - e.g. the AIH relocation list
# and the companies the morning digest saw in job alerts. Plain company names are turned into slugs.
def slugs(name: str) -> set[str]:
    n = re.sub(r"[.,()&]", " ", name.lower())
    n = re.sub(r"\b(gmbh|ag|se|bv|b v|nv|n v|ltd|limited|inc|plc|oy|ab|a/s|aps|group|holding|co kg|kg)\b", " ", n)
    words = re.sub(r"[^a-z0-9 -]", " ", n).replace("-", " ").split()
    return {"".join(words), "-".join(words)} if words else set()


_ROOT = Path(__file__).resolve().parent.parent
# + data/scan_companies.txt: companies the daily scan found on job boards (restored from the scan's cache)
for _f in sorted(_ROOT.glob("lists/*_companies.txt")) + [p for p in [_ROOT / "data" / "scan_companies.txt"] if p.exists()]:
    for _line in _f.read_text(encoding="utf-8").splitlines():
        if not _line.lstrip().startswith("#"):
            for _n in _line.split(","):
                CANDIDATES += sorted(slugs(_n)) if " " in _n.strip() or "." in _n else [_n.strip().lower()] if _n.strip() else []


def try_one(task):
    system, name = task
    try:
        jobs = FETCHERS[system](name)
    except Exception:
        return None
    if not jobs:
        return None
    devops = sum(bool(re.search(MY_ROLE_IN_TITLE, j["title"].lower())) for j in jobs)
    # keep companies that hire in my countries even if they have no DevOps job open today (they may post one tomorrow)
    from jobhunter.scoring import find_country
    in_my_countries = sum(bool(find_country(j)) for j in jobs)
    return system, name, len(jobs), devops if devops else (0.5 if in_my_countries >= 2 else 0)


def add_to_companies_file(found: dict) -> int:
    """Write found companies (with at least 1 DevOps-type job) straight into jobhunter/companies.py."""
    path = Path(__file__).resolve().parent.parent / "jobhunter" / "companies.py"
    text = path.read_text(encoding="utf-8")
    added = 0
    for system, items in found.items():
        names = [n for n, devops in items if devops > 0]
        block = re.search(rf"^{system.upper()} = \[(.*?)^\]", text, re.S | re.M)
        if not block or not names:
            continue
        new_lines = "".join(f'    "{n}",            # added by find_companies\n' for n in names
                            if f'"{n}"' not in block.group(1))
        if new_lines:
            text = text[:block.end() - 1] + new_lines + text[block.end() - 1:]
            added += new_lines.count("\n")
    path.write_text(text, encoding="utf-8")
    return added


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--write", action="store_true", help="add found companies to jobhunter/companies.py")
    ap.add_argument("--names", help="only test these names (comma separated), e.g. from today's job alerts")
    args = ap.parse_args()

    if args.names:
        wanted = set().union(*(slugs(n) for n in args.names.split(",")))
        names = sorted(wanted - ALREADY)
    else:
        names = sorted(set(CANDIDATES) - ALREADY)
    tasks = [(system, name) for name in names for system in FETCHERS]
    print(f"Testing {len(names)} companies on {len(FETCHERS)} systems ({len(tasks)} checks)...\n")

    found = defaultdict(list)
    with ThreadPoolExecutor(max_workers=24) as pool:
        for result in pool.map(try_one, tasks):
            if result:
                system, name, total, devops = result
                print(f"  FOUND  {system:16} {name:22} {total:4} jobs, {devops:3} DevOps/Platform/Cloud titles")
                found[system].append((name, devops))

    if args.write:
        print(f"\nAdded {add_to_companies_file(found)} companies to jobhunter/companies.py")
        return

    print("\n=== Paste into jobhunter/companies.py (inside the matching list) ===")
    for system, items in found.items():
        print(f"\n{system.upper()}:")
        for name, devops in sorted(items, key=lambda x: -x[1]):
            print(f'    "{name}",{"" if devops else "   # 0 DevOps jobs right now"}')


if __name__ == "__main__":
    main()
