"""
YOUR list of companies to watch, grouped by the hiring system they use.

How to find a company's system: open its careers page and look at the job links.
    boards.greenhouse.io/NAME  or  job-boards.greenhouse.io/NAME   -> GREENHOUSE, use NAME
    jobs.lever.co/NAME         or  jobs.eu.lever.co/NAME           -> LEVER, use NAME
    jobs.ashbyhq.com/NAME                                          -> ASHBY, use NAME
    NAME.recruitee.com                                             -> RECRUITEE
    jobs.smartrecruiters.com/NAME                                  -> SMARTRECRUITERS
    NAME.jobs.personio.de  /  NAME.jobs.personio.com               -> PERSONIO
    apply.workable.com/NAME                                        -> WORKABLE

Easiest: run   py tools\find_companies.py   - it tests many companies on all 7 systems
and prints ready-to-paste lists.

If the robot prints "not found" for a company, it changed systems -> delete that line.
"""

GREENHOUSE = [
    "adyen",          # Amsterdam - payments
    "n26",            # Berlin - bank
    "celonis",        # Munich
    "getyourguide",   # Berlin, Zurich
    "hellofresh",     # Berlin
    "sumup",          # Berlin, Dublin
    "contentful",     # Berlin
    "commercetools",  # Munich, Berlin
    "datadog",        # Dublin, Amsterdam, Paris
    "elastic",        # remote Europe
    "gitlab",         # remote
    "cloudflare",     # Lisbon, London, Munich
    "mongodb",        # Dublin
    "databricks",     # Amsterdam, Berlin, Munich
    "stripe",         # Dublin
    "intercom",       # Dublin
    "grafanalabs",    # remote Europe
    "canonical",      # remote
    "wolt",            # Helsinki/Berlin, 12 DevOps jobs
    "onrunning",       # Zurich
    "scout24",         # Munich/Berlin
    "solarisbank",     # Berlin - bank
    "bird",            # Amsterdam
    "catawiki",        # Amsterdam
    "flipdish",        # Dublin
    "raisin",          # Berlin - fintech
    "scandit",         # Zurich
    "staffbase",       # Germany
    "tines",           # Dublin
    "trustpilot",      # Copenhagen
    "nix",            # added by find_companies
    "airbnb",            # added by find_companies
    "coinbase",            # added by find_companies
    "dropbox",            # added by find_companies
    "okta",            # added by find_companies
    "pinterest",            # added by find_companies
    "riotgames",            # added by find_companies
    "squarespace",            # added by find_companies
    "toast",            # added by find_companies
    "twilio",            # added by find_companies
    "virtu",            # added by find_companies
    "isaraerospace",            # added by find_companies
    "chainguard",            # added by find_companies
    "dept",            # added by find_companies
    "flix",            # added by find_companies
    "helsing",            # added by find_companies
    "ionos",            # added by find_companies
    "nebius",            # added by find_companies
    "parloa",            # added by find_companies
    "qualtrics",            # added by find_companies
    "rtbhouse",            # added by find_companies
    "tailscale",            # added by find_companies
    "trivago",            # added by find_companies
    "cognism",            # added by find_companies
    "fivetran",            # added by find_companies
    "flowtraders",            # added by find_companies
    "graphcore",            # added by find_companies
    "imc",            # added by find_companies
    "intersystems",            # added by find_companies
    "keepersecurity",            # added by find_companies
    "ripple",            # added by find_companies
    "schubergphilis",            # added by find_companies
    "togetherai",            # added by find_companies
    "wpp",            # added by find_companies
    "nortal",            # added by find_companies
    "oura",            # added by find_companies
    "relex",            # added by find_companies
    "smartlyio",            # added by find_companies
    "solita",            # added by find_companies
    "testlio",            # added by find_companies
    "truecaller",            # added by find_companies
    "veriff",            # added by find_companies
    "navvis",            # added by find_companies
    "bitmovin",            # added by find_companies
    "bitpanda",            # added by find_companies
    "jetbrains",            # added by find_companies
    "nasdaq",            # added by find_companies
    "storyblok",            # added by find_companies
    # from the AIH relocation list
    "housinganywhere", "wunderflats", "anthropic", "affirm",
    "deliveroo",            # added by find_companies
    "dkbcodefactory",            # added by find_companies
    "dremio",            # added by find_companies
    "emnify",            # added by find_companies
    "hp",            # added by find_companies
    "idnow",            # added by find_companies
    "kinexon",            # added by find_companies
    "monzo",            # added by find_companies
    "stepstone",            # added by find_companies
    "talonone",            # added by find_companies
    "traderepublicbank",            # added by find_companies
    "xometry",            # added by detect_ats
    # companies you asked about (Nov 2026)
    "marvelfusion",
    "alphasense",            # added by find_companies
    "mariadbplc",            # added by detect_ats
    # Lithuania / Finland employers (Nov 2026)
    "transfergo",
    "appinio",            # added by find_companies
    "avimedical",            # added by find_companies
    "bolcom",            # added by find_companies
    "clariness",            # added by find_companies
    "creativefabrica",            # added by find_companies
    "ecosio",            # added by find_companies
    "emplifi",            # added by find_companies
    "enmacc",            # added by find_companies
    "eversports",            # added by find_companies
    "flaconi",            # added by find_companies
    "freenow",            # added by find_companies
    "gigs",            # added by find_companies
    "gostudent",            # added by find_companies
    "housemarque",            # added by find_companies
    "kununu",            # added by find_companies
    "lanesplanes",            # added by find_companies
    "mentimeter",            # added by find_companies
    "mewssystems",            # added by find_companies
    "moia",            # added by find_companies
    "rebtel",            # added by find_companies
    "tactilegames",            # added by find_companies
    "think-cell",            # added by find_companies
    "wooga",            # added by find_companies
    "yousician",            # added by find_companies
    "charles",            # added by detect_ats
    "coreweave",            # added by find_companies
    "hudl",            # added by find_companies
    "algolia",            # added by detect_ats
    "numagroupgmbh",            # added by detect_ats
    "binance",            # added by find_companies
    "turing",            # added by find_companies
    "asana",            # added by find_companies
    "gardacp",            # added by find_companies
    "horizontradingsolutions",            # added by find_companies
    "orkes",            # added by find_companies
    "arxroboticsgmbh",            # added by detect_ats
    "nexhealth",            # added by detect_ats
    "beyondtrust",            # added by find_companies
    "roku",            # added by find_companies
    "vinteden",            # added by find_companies
    "agilerobotsse",            # added by find_companies
    "apaleo",            # added by find_companies
    "dotmatics",            # added by find_companies
    "anaplan",            # added by find_companies
    "verifone",            # added by find_companies
    "bearingpoint",            # added by find_companies
    "focalsystems",            # added by find_companies
    "speechmatics",            # added by find_companies
    "bloomreach",            # added by find_companies
    "jfrog",            # added by find_companies
    "newrelic",            # added by find_companies
    "pagerduty",            # added by find_companies
    "poppulo",            # added by find_companies
    "starburst",            # added by find_companies
    "phenogyag",            # added by find_companies
    "discord",            # added by find_companies
    "ledgy",            # added by detect_ats
    "upgrade",            # added by find_companies
    "veeamsoftware",            # added by find_companies
    "blacklane",            # added by detect_ats
    "forvismazars",            # added by find_companies
    "proton",            # added by find_companies
    "gitlabcrm",            # added by detect_ats
]

LEVER = [
    "spotify",
    "qonto",
    "pigment",
    "contentsquare",   # Paris
    "unzer",            # added by find_companies
    "kitmanlabs",            # added by find_companies
    "mendix",            # added by find_companies
    "sysdig",            # added by find_companies
    "text",            # added by find_companies
    "dnb",            # added by find_companies
    "westernacher",            # added by find_companies
    "seb",            # added by find_companies
    "tomtom",            # added by find_companies
    "finn",            # added by find_companies
    # from the AIH relocation list
    "fuellabs", "swapcard", "moonpay",
    "brevo",            # added by find_companies
    "impossiblecloud",            # added by find_companies
    "linkedin",            # added by find_companies
    "vestiairecollective",            # added by find_companies
    "vivenu",            # added by find_companies
    "quantco-",            # added by detect_ats
    # companies you asked about (Nov 2026)
    "kolibrigames", "crytek",
    # Lithuania / Finland employers (Nov 2026)
    "omnisend", "nfq",
    "innogames",            # added by find_companies
    "justwatch",            # added by find_companies
    "xtb",            # added by find_companies
    "smart-working-solutions",            # added by find_companies
    "loftorbital",            # added by find_companies
    "plus-2",            # added by detect_ats
    "skaylink",            # added by find_companies
    "actian",            # added by find_companies
    "jobgether",            # added by find_companies
    "storiogroup",            # added by find_companies
    "frontier",            # added by find_companies
    "scaleway",            # added by find_companies
    "sonarsource",            # added by find_companies
    "swile",            # added by find_companies
    "qualysoft",            # added by find_companies
]

ASHBY = [
    "n8n",            # Berlin
    "deepl",          # Cologne
    "supabase",       # remote
    "linear",         # remote
    "clickhouse",      # Germany/EU, 45 DevOps jobs
    "doctolib",        # Paris/Berlin, 13 DevOps jobs
    "mollie",          # Amsterdam - payments
    "pliant",          # Berlin - fintech
    "babbel",          # Berlin
    "bitvavo",         # Amsterdam - crypto exchange
    "lunar",           # Copenhagen - bank
    "clark",           # Germany - insurtech
    "docplanner",      # Poland/Spain
    "upvest",          # Berlin - fintech
    "brainly",         # Poland
    "enpal",           # Berlin
    "flink",           # Berlin
    "miro",            # Amsterdam
    "moss",            # Berlin - fintech
    "pleo",            # Copenhagen - fintech
    "wayflyer",        # Dublin - fintech
    "astronomer",            # added by find_companies
    "attio",            # added by find_companies
    "exa",            # added by find_companies
    "polarsteps",            # added by find_companies
    "black-forest-labs",            # added by find_companies
    "cohere",            # added by find_companies
    "elevenlabs",            # added by find_companies
    "parloa",            # added by find_companies
    "ramp",            # added by find_companies
    "snowflake",            # added by find_companies
    "synthesia",            # added by find_companies
    "toogoodtogo",            # added by find_companies
    "datasnipper",            # added by find_companies
    "livekit",            # added by find_companies
    "patrianna",            # added by find_companies
    "epidemic-sound",            # added by find_companies
    "iceye",            # added by find_companies
    "nord-security",            # added by find_companies
    "polar",            # added by find_companies
    "reaktor",            # added by find_companies
    "supercell",            # added by find_companies
    "trustly",            # added by find_companies
    "lemonade",            # added by find_companies
    "stream",            # added by find_companies
    "apify",            # added by find_companies
    # from the AIH relocation list
    "justplay-gmbh", "qdrant.tech",
    "adjoe",            # added by find_companies
    "blocktech",            # added by find_companies
    "manychat",            # added by find_companies
    "orbem",            # added by find_companies
    "percona",            # added by find_companies
    "proxima-fusion",            # added by find_companies
    "sosafe",            # added by find_companies
    "stackfuel",            # added by find_companies
    "statista",            # added by find_companies
    "sunday",            # added by find_companies
    "the-exploration-company",            # added by find_companies
    "wemolo",            # added by find_companies
    "zapier",            # added by find_companies
    "bettermile",            # added by detect_ats
    "coachhub%20careers",            # added by detect_ats
    "incident",            # added by detect_ats
    "jobber",            # added by detect_ats
    "mistral.ai",            # added by detect_ats
    "preply",            # added by detect_ats
    # companies you asked about (Nov 2026)
    "justdice", "lemon-markets", "zeit-ai",
    "eneba",            # added by find_companies
    "sievo",            # added by find_companies
    "surfshark",            # added by find_companies
    # Lithuania / Finland employers (Nov 2026)
    "hostinger",
    "billie",            # added by find_companies
    "bynder",            # added by find_companies
    "corti",            # added by find_companies
    "factor-eleven",            # added by find_companies
    "flip",            # added by find_companies
    "gigs",            # added by find_companies
    "glia",            # added by find_companies
    "gotphoto",            # added by find_companies
    "klim",            # added by find_companies
    "patronus",            # added by find_companies
    "payrails",            # added by find_companies
    "reonic",            # added by find_companies
    "rohlik",            # added by find_companies
    "virtual-identity",            # added by find_companies
    "voize",            # added by find_companies
    "workhuman",            # added by find_companies
    "cosuno",            # added by detect_ats
    "koro",            # added by detect_ats
    "liqid-lig",            # added by detect_ats
    "qlub",            # added by detect_ats
    "qonto",            # added by detect_ats
    "sensmore",            # added by detect_ats
    "sunday-gmbh",            # added by detect_ats
    "netic",            # added by find_companies
    "bunch",            # added by detect_ats
    "chainalysis-careers",            # added by detect_ats
    "junction",            # added by detect_ats
    "omnea",            # added by detect_ats
    "tacto",            # added by detect_ats
    "evervault",            # added by find_companies
    "se3",            # added by find_companies
    "verda",            # added by find_companies
    "luminovo",            # added by detect_ats
    "odysseyml",            # added by detect_ats
    "sereact",            # added by detect_ats
    "telli",            # added by detect_ats
    "allica-bank",            # added by find_companies
    "dash0",            # added by detect_ats
    "kubermatic",            # added by detect_ats
    "nelly",            # added by detect_ats
    "poolside",            # added by detect_ats
    "everfield",            # added by find_companies
    "npv",            # added by find_companies
    "siena",            # added by find_companies
    "frontcareers",            # added by detect_ats
    "blacksemiconductor",            # added by find_companies
    "neuralframes",            # added by find_companies
    "prosus",            # added by find_companies
    "tonies",            # added by find_companies
    "robin-radar",            # added by detect_ats
    "workerbase",            # added by detect_ats
    "atp",            # added by find_companies
    "holidu",            # added by find_companies
    "radiant",            # added by find_companies
    "deeptech-recruitment",            # added by find_companies
    "mondoo",            # added by find_companies
    "rain",            # added by detect_ats
    "almetra",            # added by find_companies
    "lio",            # added by find_companies
    "yazio",            # added by find_companies
    "speechmatics",            # added by find_companies
    "docker",            # added by find_companies
    "forto",            # added by find_companies
    "knowunity",            # added by find_companies
    "pennylane",            # added by find_companies
    "prior-labs",            # added by find_companies
    "redis",            # added by find_companies
    "sentry",            # added by find_companies
    "zenjob",            # added by find_companies
    "swap",            # added by detect_ats
    "backmarket",            # added by find_companies
    "amenitiz",            # added by detect_ats
    "lyceum",            # added by find_companies
    "almedia",            # added by find_companies
    "saily",            # added by find_companies
    "rerun",            # added by detect_ats
    "zauber",            # added by detect_ats
]

RECRUITEE = [
    "bunq",           # Amsterdam - bank
    "cowmanager",            # added by find_companies
    "channable",            # added by find_companies
    "adesso",            # added by find_companies
    "ampere",            # added by find_companies
    "edsn",            # added by find_companies
    "inovex",            # added by find_companies
    "linkit",            # added by find_companies
    "luscii",            # added by find_companies
    "onlinepaymentplatform",            # added by find_companies
    "optics11",            # added by find_companies
    # from the AIH relocation list
    "amperecloud", "bonial", "xchange", "greenflux", "makersitegmbh", "onemobility",
    "adjust",            # added by find_companies
    "distribusion",            # added by find_companies
    "swisscom",            # added by find_companies
    "qualifyzegmbh",            # added by detect_ats
    "dpgmedia",            # added by find_companies
    "pvcase",            # added by find_companies
    "epilot",            # added by find_companies
    "ey",            # added by find_companies
    "fastned",            # added by find_companies
    "funda",            # added by find_companies
    "insidem2m",            # added by find_companies
    "instagrid",            # added by find_companies
    "kion",            # added by find_companies
    "lillydoo",            # added by find_companies
    "limehome",            # added by find_companies
    "mirka",            # added by find_companies
    "naxcon",            # added by find_companies
    "nmbrs",            # added by find_companies
    "sharpist",            # added by find_companies
    "squla",            # added by find_companies
    "unu",            # added by find_companies
    "vandebron",            # added by find_companies
    "voltaira",            # added by find_companies
    "ingestro",            # added by detect_ats
    "accenture",            # added by find_companies
    "berlinmetropolitanschool",            # added by find_companies
    "cloudpunks",            # added by find_companies
    "effectory",            # added by find_companies
    "eleqtron",            # added by find_companies
    "exeonanalytics",            # added by find_companies
    "hypersolid",            # added by find_companies
    "smartpatient",            # added by find_companies
    "softgames",            # added by find_companies
    "intelic",            # added by find_companies
    "solvinity",            # added by find_companies
    "rewire",            # added by find_companies
    "studytube",            # added by find_companies
    "sgbsmit",            # added by find_companies
    "thetraineecompany",            # added by find_companies
    "gridscale",            # added by find_companies
    "s4d",            # added by find_companies
    "trackman",            # added by find_companies
    "dawntechnology",            # added by find_companies
    "hetzner",            # added by find_companies
    "wellis",            # added by find_companies
    "wtss",            # added by find_companies
    "distribusiontechnologies",            # added by find_companies
    "quality",            # added by find_companies
]

SMARTRECRUITERS = [   # filled by tools/find_companies.py
    "boschgroup",      # Germany - Bosch, 21 DevOps jobs
    "deliveryhero",    # Berlin, 16 DevOps jobs
    "nexthink",        # Switzerland, 5 DevOps jobs
    "swissquote",      # Switzerland - bank, 2 DevOps jobs
    "auto1",           # Berlin
    "allegro",         # Poland
    "picnic",          # Netherlands
    "alten",            # added by find_companies
    "everience",            # added by find_companies
    "redcare-pharmacy",            # added by find_companies
    "coolblue",            # added by find_companies
    "softwaremind",            # added by find_companies
    "agileengine",            # added by find_companies
    "devoteam",            # added by find_companies
    "playtech",            # added by find_companies
    "wise",            # added by find_companies
    "frequentis",            # added by find_companies
    # from the AIH relocation list
    "lgcgroup", "scalablegmbh",
    "abbvie",            # added by find_companies
    "brainlab",            # added by find_companies
    "cliffordchance",            # added by find_companies
    "continental",            # added by find_companies
    "freshworks",            # added by find_companies
    "kpn",            # added by find_companies
    "redbull",            # added by find_companies
    "servicenow",            # added by find_companies
    "sixt",            # added by find_companies
    "vattenfall",            # added by find_companies
    "wundermobility",            # added by find_companies
    "BoschGroup",            # added by detect_ats
    "Freshworks",            # added by detect_ats
    "ScalableGmbH",            # added by detect_ats
    "StepStoneGroup",            # added by detect_ats
    # companies you asked about (Nov 2026)
    "coera",
    "konecranes",            # added by find_companies
    "itsearch",            # added by find_companies
    "omio",            # added by find_companies
    "redcarepharmacy",            # added by find_companies
    "robertbosch",            # added by find_companies
    "rocketinternet",            # added by find_companies
    "sevensenders",            # added by find_companies
    "wehkamp",            # added by find_companies
    "PACEPaparazziCateringEventGmbH",            # added by detect_ats
    "SevenSenders",            # added by detect_ats
    "binance",            # added by find_companies
    "Flink3",            # added by detect_ats
    "UbiqueSystems1",            # added by detect_ats
    "version1",            # added by find_companies
    "sia",            # added by find_companies
    "renesaselectronics",            # added by find_companies
]

PERSONIO = [          # filled by tools/find_companies.py
    "1komma5grad",     # Germany - solar/energy, 7 DevOps jobs
    "ohpen",            # added by find_companies
    "aryza",            # added by find_companies
    "rulemapping",            # added by find_companies
    "hiq",            # added by find_companies
    "ottonova",            # added by find_companies
    # from the AIH relocation list
    "askui-gmbh", "bigpoint", "bonify", "celus", "common-goal-ggmbh", "geton", "holoplot", "homify", "indra-avitech", "juit", "kugu", "mobimeo", "onemedia-consulting", "tidely", "workpath",
    "mbition",            # added by find_companies
    "merantix",            # added by find_companies
    "ng-voice",            # added by find_companies
    "solactive",            # added by find_companies
    "bitcap",            # added by detect_ats
    "checkmk-gmbh",            # added by detect_ats
    "exmox-gmbh",            # added by detect_ats
    "rivada-space-networks-gmbh",            # added by detect_ats
    # companies you asked about (Nov 2026)
    "pair",
    "meierhofer",            # added by find_companies
    "matrix42",            # added by detect_ats
    "allocnow",            # added by find_companies
    "alteos",            # added by find_companies
    "bliq",            # added by find_companies
    "capmo",            # added by find_companies
    "carbmee",            # added by find_companies
    "casavi",            # added by find_companies
    "chrono24",            # added by find_companies
    "entityx",            # added by find_companies
    "felmo",            # added by find_companies
    "holidaypirates",            # added by find_companies
    "internations",            # added by find_companies
    "kiwi",            # added by find_companies
    "magazino",            # added by find_companies
    "metalshub",            # added by find_companies
    "mynaric",            # added by find_companies
    "porsche-consulting",            # added by find_companies
    "prewave",            # added by find_companies
    "randstad",            # added by find_companies
    "reos",            # added by find_companies
    "riskident",            # added by find_companies
    "shyftplan",            # added by find_companies
    "temedica",            # added by find_companies
    "twaice",            # added by find_companies
    "we-love-x",            # added by find_companies
    "westwing",            # added by find_companies
    "yfoodlabs",            # added by find_companies
    "chargecloud-gmbh",            # added by detect_ats
    "epages-gmbh",            # added by detect_ats
    "event-inc",            # added by detect_ats
    "vanilla-steel-gmbh",            # added by detect_ats
    "steadforce",            # added by find_companies
    "lepaya",            # added by find_companies
    "lumenaza",            # added by find_companies
    "become-1-gmbh",            # added by detect_ats
    "kipu-quantum",            # added by find_companies
    "gus",            # added by find_companies
    "id-ware",            # added by find_companies
    "soley-gmbh",            # added by detect_ats
    "civey-gmbh",            # added by detect_ats
    "atissystems",            # added by find_companies
    "hornetsecurity",            # added by find_companies
    "mm-software-gmbh",            # added by detect_ats
    "personio",            # added by find_companies
    "squer",            # added by find_companies
    "partspace",            # added by find_companies
    "peak-one",            # added by find_companies
    "hive-robotics",            # added by detect_ats
    "liveeo-gmbh",            # added by detect_ats
    "vantis",            # added by detect_ats
    "stark",            # added by find_companies
    "lanes-planes",            # added by find_companies
    "dachs-it",            # added by find_companies
    "dyn-media-gmbh",            # added by detect_ats
    "deepspin-gmbh",            # added by detect_ats
    "platoapp",            # added by detect_ats
]

WORKABLE = [          # filled by tools/find_companies.py
    "scalable",        # Munich - Scalable Capital
    # from the AIH relocation list
    "akur8", "bkbn", "cara-care", "careerfoundry", "gamigo", "labtwin", "n8n",
    "euromonitor",            # added by find_companies
    # companies you asked about (Nov 2026)
    "agile-robots",
    "adverity",            # added by find_companies
    "robeaute",            # added by detect_ats
    "1global",            # added by find_companies
    "prodyna",            # added by find_companies
    "skeletontech",            # added by find_companies
    "deployteq",            # added by find_companies
    "degura",            # added by detect_ats
]

# Bundesagentur fuer Arbeit (Germany's official job agency): what to search for
BAMBOOHR = [          # COMPANY.bamboohr.com (from the AIH relocation list; more added by find_companies)
    "aklamio", "astroscale", "flexionmobile", "onlinefilings", "brainrocket",
    "altenar",            # added by find_companies
    "kubermatic",            # added by find_companies
    "duplo",            # added by detect_ats
    "tpaerospace",            # added by find_companies
    "alloptions",            # added by find_companies
    "bragi",            # added by find_companies
    "codasip",            # added by find_companies
    "microharvest",            # added by find_companies
    "pfhtechnology",            # added by find_companies
    "nedap",            # added by find_companies
    "docosoft",            # added by find_companies
]
TEAMTAILOR = [        # COMPANY.teamtailor.com
    "goodgamestudios", "starship",
    "bankdata",            # added by find_companies
    "codit",            # added by find_companies
    "dustin",            # added by find_companies
    "flatpay",            # added by find_companies
    "journi",            # added by find_companies
    "keepit",            # added by find_companies
    "knaufit",            # added by find_companies
    "leaseweb",            # added by find_companies
    "lumapps",            # added by find_companies
    "multiversecomputing",            # added by find_companies
    "onwelo",            # added by find_companies
    "qliro",            # added by find_companies
    "sendcloud",            # added by find_companies
    "signicat",            # added by find_companies
    "spacelift",            # added by find_companies
    "teamviewer",            # added by find_companies
    "thales",            # added by find_companies
    "tibber",            # added by find_companies
    "upcloud",            # added by find_companies
    "zinkworks",            # added by find_companies
    "sdworxgroup",            # added by detect_ats
    "adform",            # added by find_companies
    "forwardforever",            # added by find_companies
    # Lithuania / Finland employers (Nov 2026)
    "iqm",
    "carvertical",            # added by find_companies
    "hemnet",            # added by find_companies
    "highsnobiety",            # added by find_companies
    "holvi",            # added by find_companies
    "huawei",            # added by find_companies
    "huaweifinland",            # added by find_companies
    "polestar",            # added by find_companies
    "queueit",            # added by find_companies
    "rebtel",            # added by find_companies
    "siili",            # added by find_companies
    "storytel",            # added by find_companies
    "templafy",            # added by find_companies
    "twoday",            # added by find_companies
    "virtuagym",            # added by find_companies
    "vismafinland",            # added by find_companies
    "vincitoyj",            # added by detect_ats
    "paynetalent",            # added by detect_ats
    "redpilllinpro",            # added by find_companies
    "danskecommoditiesas",            # added by detect_ats
    "boylesports",            # added by find_companies
    "twodaydenmark",            # added by detect_ats
    "twodayfinland",            # added by detect_ats
    "twodaylithuania",            # added by detect_ats
    "twodaynorway",            # added by detect_ats
    "atp",            # added by find_companies
    "softswiss",            # added by find_companies
    "bearingpoint",            # added by find_companies
    "itm8",            # added by find_companies
    "deezer",            # added by find_companies
    "egmont",            # added by find_companies
    "gitguardian",            # added by find_companies
    "eficode",            # added by find_companies
]
JOIN = [              # join.com/companies/COMPANY (German start-ups, from the AIH list)
    "accountable", "advanced-store", "aeyde", "automaited", "akkuracy", "atopia", "aurahealth1", "autobahn-security",
    "awakemobility", "bayes", "beesandbears", "codepan", "convercus", "cybervize", "dexter-health", "dudechem", "egroup",
    "faircado", "feniska", "fine", "gauss-robotics", "iluxi", "innential", "linetweet", "livello", "locoia", "loudly",
    "lumiform", "nitrado", "mavue", "medability", "meshle", "mitai", "movinga", "mute-labs", "nrobotics", "noca-mobility",
    "oncare", "onu", "oppcourt", "oxolo", "paretos", "piurimaging", "primal-state", "promiseq", "quant-ip",
    "retresco", "cuju", "sidestream", "silber-salon", "softwaregini", "spacegoats", "spized", "sprk",
    "tomorrowbiostasis", "tozero", "trainos", "unumotors", "voltstorage", "xolo", "xouxouberlin",
    "mytheresa",            # added by find_companies
    "q-perior",            # added by find_companies
    "seqana",            # added by find_companies
    "vicoland",            # added by find_companies
    "accenture",            # added by find_companies
    "anyfields",            # added by find_companies
    "newmonday",            # added by find_companies
    "citema",            # added by find_companies
    "soley",            # added by find_companies
    "concape",            # added by find_companies
    "kd-pharma",            # added by find_companies
    "uneat",            # added by find_companies
    "hornetsecurity",            # added by find_companies
    "rockstardevelopers",            # added by find_companies
    "machineering1",            # added by detect_ats
    "inspacion",            # added by find_companies
    "iqplus",            # added by find_companies
    "unity",            # added by find_companies
    "wabcon",            # added by find_companies
    "angeheuert",            # added by find_companies
    "k-tronik",            # added by find_companies
    "partspace",            # added by find_companies
    "pci-experts",            # added by find_companies
    "triology",            # added by find_companies
    "mintcode-solutions",            # added by find_companies
    "allegro-packets",            # added by find_companies
    "group24",            # added by find_companies
    "netlogix",            # added by find_companies
    "bizfactory",            # added by find_companies
]

PHENOM = [            # big-company career sites on Phenom (found by tools/detect_ats.py)
    "careers.abb", "careers.allianz.com", "careers.cisco.com", "careers.dhl.com", "careers.exyte.net",
    "careers.hellofresh.com", "careers.roche.com", "jobs.kuehne-nagel.com", "jobs.thermofisher.com",
    "www.careers.philips.com", "careers.mastercard.com", "career.lanxess.com", "jobs.proximus.com",
    "careers.justeattakeaway.com",            # added by detect_ats
    "careers.hugoboss.com",            # added by detect_ats
]
SUCCESSFACTORS = [    # SAP SuccessFactors "Career Site Builder" sites (found by tools/detect_ats.py)
    "basf.jobs", "careers.eon.com", "careers.faurecia.com", "careers.jenoptik.com", "jobs.hannover-re.com",
    "jobs.kpmg.de", "jobs.nordex-online.com", "jobs.prosiebensat1.com", "jobs.rational-online.com",
    "jobs.schaeffler.com", "jobs.uniper.energy", "jobs.vaillant-group.com", "jobs.volkswagen-group.com",
    "jobs.wacker.com", "jobs.zf.com", "www.jobs.atlascopcogroup.com", "jobs.bilfinger.com", "jobs.epo.org",
    "careers.knorr-bremse.com", "careers.cybex-online.com", "jobs.oetker.com", "jobs.man.eu",
    "opportunities.bestseller.com",            # added by detect_ats
    "opportunities.vodafone.com",            # added by detect_ats
    "career.deutsche-boerse.com",            # added by detect_ats
    "careers.ey.com",            # added by detect_ats
    "careers.nordea.com",            # added by detect_ats
    "careers.vestas.com",            # added by detect_ats
    "careers.gi-de.com",            # added by detect_ats
]

BUNDESAGENTUR_SEARCHES = [
    "DevOps Engineer",
    "Platform Engineer",
    "Site Reliability Engineer",
    "Cloud Engineer Azure",
    "Kubernetes",
]


# Workday career sites: (tenant, wdN, site) from the careers URL https://<tenant>.<wdN>.myworkdayjobs.com/en-US/<site>
# Unchecked guesses are fine: sites that don't answer are listed after each run ("not found") - delete those.
WORKDAY = [
    ("juliusbaer", "wd3", "External"),           # Julius Baer - Zurich (allowed via EXTRA_PLACES_FOR_COMPANY), Madrid, Dublin, Luxembourg, Frankfurt
    ("adobe", "wd5", "external_experienced"),     # from the AIH relocation list
    ("dxctechnology", "wd1", "DXCJobs"),
    ("embl", "wd103", "EMBL"),
    ("kone", "wd3", "Careers"),
    ("nasdaq", "wd1", "Global_External_Site"),
    ("medtronic", "wd1", "MedtronicCareers"),
    ("modernatx", "wd1", "M_tx"),
    ("roche", "wd3", "roche-ext"),
    ("mcafee", "wd1", "External"),
    ("centrica", "wd3", "Centrica"),
    ("fis", "wd5", "SearchJobs"),
    ("kyndryl", "wd5", "KyndrylProfessionalCareers"),
    ("mastercard", "wd1", "CorporateCareers"),
    ("citi", "wd5", "2"),
    ("statestreet", "wd1", "Global"),
    ("ntrs", "wd1", "northerntrust"),
    ("paypal", "wd1", "jobs"),
    ("philips", "wd3", "jobs-and-careers"),
    ("salesforce", "wd12", "External_Career_Site"),
    ("workday", "wd5", "Workday"),
    ("nvidia", "wd5", "NVIDIAExternalCareerSite"),
    ("accenture", "wd103", "AccentureCareers"),
    ("intel", "wd1", "External"),
    ("equinix", "wd1", "External"),
    ("relx", "wd3", "relx"),
    ("wk", "wd3", "External"),
    ("fiserv", "wd5", "EXT"),
    ("ing", "wd3", "ICSGBLCOR"),
    ("adobe", "wd5", "external_experienced"),
    ("hp", "wd5", "ExternalCareerSite"),
    ("broadcom", "wd1", "External_Career"),
    ("autodesk", "wd1", "Ext"),
    ("redhat", "wd5", "jobs"),
    ("thomsonreuters", "wd5", "External_Career_Site"),
    ("lseg", "wd3", "Careers"),
    ("motorolasolutions", "wd5", "Careers"),
    ("aptiv", "wd5", "APTIV_CAREERS"),
    ("sabre", "wd1", "SabreJobs"),
    ("shell", "wd3", "ShellCareers"),
    ("maersk", "wd3", "Maersk_Careers"),
    ("db", "wd3", "DBWebsite"),
    ("ebay", "wd5", "apply"),
    ("visa", "wd5", "Visa"),
    ("tmobile", "wd1", "External"),
    ("ag", "wd3", "Airbus"),     # added by detect_ats
    ("agilent", "wd5", "Agilent_Careers"),     # added by detect_ats
    ("barclays", "wd3", "External_Career_Site_Barclays"),     # added by detect_ats
    ("covestro", "wd3", "cov_external"),     # added by detect_ats
    ("essity", "wd3", "Job_opportunities"),     # added by detect_ats
    ("evotecgroup", "wd3", "Evotec_Career_Site"),     # added by detect_ats
    ("fielmann", "wd3", "External"),     # added by detect_ats
    ("interpublic", "wd5", "OMC"),     # added by detect_ats
    ("jj", "wd5", "JJ"),     # added by detect_ats
    ("kiongroup", "wd3", "KION_SCS"),     # added by detect_ats
    ("lbg", "wd3", "lbg_Careers"),     # added by detect_ats
    ("leonardocompany", "wd3", "LeonardoCareerSite"),     # added by detect_ats
    ("onehealthineers", "wd3", "SHSJB"),     # added by detect_ats
    ("soti", "wd3", "Careers"),     # added by detect_ats
    ("springernature", "wd3", "SpringerNatureCareers"),     # added by detect_ats
    ("zendesk", "wd1", "zendesk"),     # added by detect_ats
    ("clio", "wd3", "ClioCareerSite"),     # added by detect_ats
    ("valmet", "wd103", "External"),     # added by detect_ats
    ("tnsi", "wd1", "Search"),     # added by detect_ats
    ("gevernova", "wd5", "Vernova_ExternalSite"),     # added by detect_ats
    ("iqvia", "wd1", "IQVIA"),     # added by detect_ats
]
