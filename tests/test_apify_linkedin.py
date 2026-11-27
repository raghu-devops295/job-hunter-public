"""Offline check of the optional Apify LinkedIn source (no network)."""
from jobhunter.sources import apify_linkedin


def test_skipped_without_token(monkeypatch):
    monkeypatch.delenv("APIFY_TOKEN", raising=False)
    assert apify_linkedin.fetch() == []


def test_focus_searches_and_title_filter(monkeypatch):
    monkeypatch.setenv("APIFY_TOKEN", "x")
    monkeypatch.delenv("APIFY_COUNTRIES", raising=False)
    calls = []

    class Fake:
        def raise_for_status(self): pass
        def json(self):
            return [{"id": "4012345", "title": "Azure DevOps Engineer", "companyName": "Adyen",
                     "location": "Amsterdam, North Holland, Netherlands", "link": "https://www.linkedin.com/jobs/view/4012345?trk=x",
                     "descriptionText": "AKS Terraform", "postedAtTimestamp": 1764000000000, "workplaceTypes": ["Hybrid"]},
                    {"id": "9", "title": "Sales Manager Azure", "link": "https://www.linkedin.com/jobs/view/9"},
                    {"title": ""}]

    def fake_post(url, headers, json, timeout):
        calls.append(json)
        return Fake()

    monkeypatch.setattr(apify_linkedin.requests, "post", fake_post)
    jobs = apify_linkedin.fetch()
    assert len(calls) == 5                                   # Platform Engineer is searched in the top 3 only
    assert all(j["title"] == "Azure DevOps Engineer" for j in jobs) and len(jobs) == 5
    assert jobs[0]["url"] == "https://www.linkedin.com/jobs/view/4012345"
    assert "%22Azure%20DevOps%22" in calls[0]["urls"][0] and calls[0]["limitPerSource"] == 13
    assert any("location=Lithuania" in u for c in calls for u in c["urls"])
    # budget: worst case per month stays under Apify's $5 free usage (~$1 per 1,000 jobs)
    per_day = sum(c["limitPerSource"] * len(c["urls"]) for c in calls)
    assert per_day == 143 and per_day * 30 / 1000 <= 4.6


def test_countries_override(monkeypatch):
    monkeypatch.setenv("APIFY_COUNTRIES", "Netherlands, Germany")
    assert apify_linkedin.apify_countries() == (["Netherlands", "Germany"], [])
    monkeypatch.delenv("APIFY_COUNTRIES")
    top, other = apify_linkedin.apify_countries()
    assert top == ["Netherlands", "Germany", "Ireland"] and "Lithuania" in other


def test_company_apply_url():
    f = apify_linkedin.company_apply_url
    assert f("https://www.linkedin.com/jobs/view/1") == ""              # Easy Apply stays on LinkedIn
    assert f(None) == ""
    assert f("https://job-boards.greenhouse.io/acme/jobs/123?gh_src=abc&utm_source=linkedin") == \
        "https://job-boards.greenhouse.io/acme/jobs/123"
    assert f("https://careers.acme.com/job/42?id=7&utm_medium=x") == "https://careers.acme.com/job/42?id=7"


def test_save_linkedin_careers_pages(tmp_path, monkeypatch):
    import run
    monkeypatch.chdir(tmp_path)
    (tmp_path / "lists").mkdir()
    (tmp_path / "lists" / "alerts_careers_urls.txt").write_text("job-boards.greenhouse.io/known\n")
    monkeypatch.setattr(run, "LINKEDIN_CAREERS", tmp_path / "lists" / "linkedin_careers_urls.txt")
    kept = [{"source": "linkedin", "careers_url": "https://job-boards.greenhouse.io/known/jobs/1"},
            {"source": "linkedin", "careers_url": "https://job-boards.greenhouse.io/acme/jobs/2"},
            {"source": "linkedin", "careers_url": "https://job-boards.greenhouse.io/acme/jobs/3"},   # same site
            {"source": "linkedin", "careers_url": ""},
            {"source": "greenhouse", "careers_url": "https://x.io/a"}]
    run.save_linkedin_careers_pages(kept)
    lines = (tmp_path / "lists" / "linkedin_careers_urls.txt").read_text().splitlines()
    assert lines[1:] == ["job-boards.greenhouse.io/acme/jobs/2"]


def test_thehub_reads_list_and_detail(monkeypatch):
    from jobhunter.sources import more_boards as m
    monkeypatch.setattr("jobhunter.scoring.TARGET_COUNTRIES", ["Denmark"])
    def fake(url, params=None, headers=None):
        if url.endswith("jobsandfeatured"):
            if params["search"] != "devops":
                return {"jobs": {"docs": [], "pages": 1}}
            return {"jobs": {"pages": 1, "docs": [{"id": "abc", "title": "Senior DevOps Engineer", "isRemote": False,
                     "location": {"locality": "Herlev", "country": "Denmark"}, "company": {"name": "Flatpay"}}]}}
        return {"doc": {"description": "<p>Azure and AKS</p>", "publishedAt": "2026-11-20T07:00:00Z",
                        "link": "https://jobs.flatpay.com/jobs/1"}}
    monkeypatch.setattr(m, "get_json", fake)
    jobs = m.thehub()
    assert len(jobs) == 1 and jobs[0]["company"] == "Flatpay" and jobs[0]["location"] == "Herlev, Denmark"
    assert jobs[0]["url"] == "https://jobs.flatpay.com/jobs/1" and "AKS" in jobs[0]["description"]
    assert jobs[0]["posted_at"].startswith("2026-11-20")
