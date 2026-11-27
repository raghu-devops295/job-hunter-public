# job-hunter

A personal job-search pipeline I built and run myself: it finds Platform / DevOps / SRE / Azure roles in Europe, scores them against my real experience, tracks every application as a GitHub issue and produces an ATS-tailored resume for each strong match.

A personal job-search robot for DevOps / Platform roles in Europe. Personal data (resume, facts, job tracker) lives in a separate private repo.

## How it works

```
 job boards + company career sites          job-alert emails (LinkedIn, StepStone, agencies)
 (Greenhouse, Lever, Workday, Personio,                 │
  SmartRecruiters, Bundesagentur, LinkedIn via Apify)   ▼
          │                                  Claude "Job alert digest" (daily)
          ▼                                             │ tools/add_email_job.py
 GitHub Actions: run.py (daily)                         │
   1. fetch      jobhunter/sources/*                    │
   2. filter     filters.py  (country, language,        │
                 visa, AWS/GCP-only, NL sponsor)        │
   3. score      scoring.py (rules) + skill_fit.py      │
                 (Gemini Flash-Lite, cheap)             │
   4. track      tracker.py -> GitHub issue ◄───────────┘
   5. tailor     tailor.py  -> ATS resume PDF + score
          │
          ▼
 Claude "Job inbox status check" (daily): labels Gmail replies, moves issues to
 applied / interview / rejected; weekly review flags no-response and drafts follow-ups.
```

## Key design choices

- **One country list:** `lists/countries.txt` drives scoring, filters, the job boards that are called and the Claude task prompts. The first country gets extra ranking points.
- **Sponsorship first:** Netherlands roles must be at an IND recognised sponsor (`sponsors.py`, list refreshed monthly). Ads saying "no sponsorship" or "local candidates only" are skipped.
- **Honest tailoring:** `jobhunter/facts.md` is the single source of truth. The tailor may only reword what is in it, never invent tools or certifications.
- **Cheap where possible:** rules and Gemini Flash-Lite do the bulk scoring for free; Claude handles only judgement work (email triage, reading ads from alerts). Ad text is stored inside each issue so nothing is fetched twice.
- **Tracker = GitHub issues:** labels `new → applied → interview → offer / rejected` (+ `no-response`). The `Label sync` workflow removes `new` automatically.

## Optional: LinkedIn via Apify

Add the repo secret `APIFY_TOKEN` (Settings → Secrets and variables → Actions) to also scan public LinkedIn listings from the last 24 hours for every country in `lists/countries.txt`, focused on "Azure DevOps" first, then "DevOps Engineer" and "Platform Engineer" (exact phrases; non-engineering titles dropped) - about $4.30/month at most, inside Apify's $5 free monthly usage (see the table in `jobhunter/sources/apify_linkedin.py`; repo variable `APIFY_COUNTRIES` limits the countries) (`jobhunter/sources/apify_linkedin.py`, no LinkedIn login used). Without the secret the source is skipped.

## Optional: Groq fallback when Gemini is busy

Google's free Gemini API is often overloaded (HTTP 503). Add the repo secret `GROQ_API_KEY` (free account at console.groq.com, no card) and the robot switches to Groq (`openai/gpt-oss-120b`, `openai/gpt-oss-20b`, `llama-3.3-70b-versatile`, rotated on rate limits) for the rest of a run after Gemini has been busy twice. Without the key, the robot ranks unscored jobs by rules and checks them next run.

## Public code, private data

This repo is public so GitHub Actions runs here are free. Everything personal stays in the private data repo
(`DATA_REPO` in the workflows):

| Private data repo | This public repo |
|---|---|
| `jobhunter/resume.yaml`, `jobhunter/facts.md` | code, workflows, company lists, example files |
| job issues (the tracker) and labels | the daily run, tailoring, fill-job-text |
| tailored PDFs in `resumes/` | robot memory (Actions cache) |
| full run logs in `logs/last-*.txt` | only a one-line status per run |
| `Relay` workflow: the `tailor` / `needs-text` labels start the workflows here | |

Setup: a fine-grained token with **Contents, Issues and Actions: read and write** on both repos, saved as the secret
`DATA_REPO_TOKEN` here and `PUBLIC_REPO_TOKEN` in the private repo. Without the private files the code uses
`jobhunter/resume.example.yaml` and `jobhunter/facts.example.md` (a made-up person), which is what the tests use.

## Workflows

| Workflow | Trigger | What it does |
|---|---|---|
| `job-hunter.yml` | daily | fetch, filter, score, open issues, auto-tailor strong matches |
| `tailor.yml` | label `tailor` | tailored resume PDF + ATS keyword score as an issue comment |
| `fill-job-text.yml` | label `needs-text`, daily | fetch the ad text into the issue, then tailor |
| `label-sync.yml` | status label added | removes the outdated `new` label |
| `find-companies.yml` | company lists change | detects each employer's ATS so the robot can scan it |
| `india-hunter.yml` | schedule | separate India search (logged with label `india`) |

## Run locally

```bash
pip install -r requirements.txt
python -m pytest tests -q                       # offline tests
GEMINI_API_KEY=... GITHUB_TOKEN=... python run.py
GITHUB_TOKEN=... python tailor.py --issue 123
```

## Tech

Python 3.12 · GitHub Actions (schedules, issue events, cache) · GitHub REST API · Google Gemini API · Claude scheduled tasks with Gmail and GitHub connectors.
