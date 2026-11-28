"""Offline checks (no Gemini, no GitHub). Run: python -m pytest tests -q"""
import re
import pytest

from jobhunter import filters, scoring, tailor


def job(location, title="Senior Platform Engineer", source="greenhouse", desc="Azure AKS Kubernetes Terraform " * 20):
    return {"title": title, "description": desc, "location": location, "source": source, "company": "x"}


# ---- countries: only the ones in lists/countries.txt are in

@pytest.fixture(autouse=True)
def no_sponsor_list(monkeypatch):
    """Offline: pretend the IND sponsor list could not be downloaded (so the NL sponsor rule is off)."""
    from jobhunter import sponsors
    monkeypatch.setattr(sponsors, "ind_sponsors", lambda: set())


@pytest.mark.parametrize("loc", ["Berlin, Germany", "Amsterdam, Netherlands", "Dublin, Ireland",
                                 "Hoofddorp, NL", "Aarhus, Denmark", "Stockholm, Sweden", "Helsinki, Finland",
                                 "Luxembourg City", "Madrid, Spain", "Tallinn, Estonia", "Vilnius, Lithuania", "Remote - Germany, Spain, Sweden, UK"])
def test_target_countries_pass(loc):
    assert filters.find_dealbreaker(job(loc)) is None, loc


@pytest.mark.parametrize("loc", ["Krakow, Poland", "Warsaw, PL", "Remote - Poland, Remote, Kraków, Poland",
                                 "Prague, Czechia",
                                 "Remote - Romania", "Cluj-Napoca, RO", "Bratislava",
                                 "Milton Keynes, UK", "Remote - Canada", "Remote, USA",
                                 "Zurich, Switzerland", "Lisbon, Portugal", "Paris, France"])
def test_other_countries_skipped(loc):
    assert filters.find_dealbreaker(job(loc)) is not None, loc


def test_country_list_comes_from_file():
    assert scoring.TARGET_COUNTRIES == ["Netherlands", "Germany", "Ireland", "Denmark", "Finland",
                                        "Sweden", "Luxembourg", "Spain", "Estonia", "Lithuania",
                                        "United Arab Emirates", "Saudi Arabia"]
    assert set(scoring.MY_COUNTRIES) == set(scoring.COUNTRY_BONUS) == set(scoring.TARGET_COUNTRIES)
    assert scoring.COUNTRY_BONUS["Netherlands"] == 15 and scoring.COUNTRY_BONUS["Germany"] == 10


def test_nl_job_needs_ind_sponsor(monkeypatch):
    from jobhunter import sponsors
    monkeypatch.setattr(sponsors, "ind_sponsors", lambda: {"adyen"})
    ok = dict(job("Amsterdam, Netherlands"), company="Adyen N.V.")
    no = dict(job("Amsterdam, Netherlands"), company="Tiny Startup")
    de = dict(job("Berlin, Germany"), company="Tiny Startup")
    assert filters.find_dealbreaker(ok) is None
    assert "IND recognised sponsor" in filters.find_dealbreaker(no)
    assert filters.find_dealbreaker(de) is None


# ---- tailor: retries stop when they cannot help

def test_skips_tailoring_when_master_cannot_reach_target(monkeypatch):
    """Kafka is not on the master resume, so the master's ceiling is far below 90%: no Gemini tailoring call."""
    calls = {"n": 0}
    monkeypatch.setattr(tailor, "_plan_prompt", lambda *a, **k: "prompt")
    monkeypatch.setattr(tailor, "extract_keywords", lambda j: {"must": ["Kafka"], "nice": [], "job_title": "x"})
    def fake_plan(prompt, temperature=0.0):
        calls["n"] += 1
        return {"bullets": [], "skills": []}
    monkeypatch.setattr(tailor, "ask_json", fake_plan)
    with pytest.raises(SystemExit, match="covers only"):
        tailor.tailor({"title": "x", "description": "x"})
    assert calls["n"] == 0


# ---- German cover letter (Anschreiben)

from jobhunter import outreach


def test_german_ad_detected():
    de = {"title": "Platform Engineer", "location": "Berlin, Germany",
          "description": "Wir suchen einen Engineer. Du bist Teil unseres Teams und arbeitest mit uns an der Plattform."}
    en = {"title": "Platform Engineer", "location": "Dublin, Ireland",
          "description": "We are looking for a platform engineer to join our team. You will work with AKS and Terraform."}
    assert outreach.is_german_ad(de)
    assert not outreach.is_german_ad(en)


def test_german_letter_number_check(monkeypatch):
    job = {"title": "Platform Engineer", "company": "X", "location": "Berlin, Germany", "description": "Wir " * 200}
    good = "Sehr geehrte Damen und Herren, ich bringe 7 Jahre Erfahrung mit. Mit freundlichen Grüßen\nAlex Example"
    bad = "Sehr geehrte Damen und Herren, ich habe 99 Jahre Erfahrung. Mit freundlichen Grüßen\nAlex Example"
    monkeypatch.setattr(outreach.skill_fit, "ask_json", lambda *a, **k: {"cover_de": bad})
    assert outreach.draft_german(job, {"7"}) == ""          # invented number -> not used
    monkeypatch.setattr(outreach.skill_fit, "ask_json", lambda *a, **k: {"cover_de": good})
    assert outreach.draft_german(job, {"7"}) == good


def test_trained_azure_certs_count_as_on_resume():
    resume_text = "Azure Administrator Associate (AZ-104), trained; Azure DevOps Engineer Expert (AZ-400), trained"
    norm = tailor._norm(resume_text)
    assert tailor._has("Azure Administrator certification (AZ-104)", norm)
    assert tailor._has("Azure Expert", norm)
    assert tailor._has("azure devops engineer expert", norm)


def test_recruiter_box_highlights_contact_or_says_none():
    from jobhunter import outreach
    with_contact = {"description": "Send CV to jobs@acme.com or call +49 30 1234567", "title": "x", "company": "A"}
    assert outreach.recruiter_box(with_contact, None)[0].startswith("### 🟢 RECRUITER / HR IN THIS AD")
    assert "jobs@acme.com" in outreach.recruiter_box(with_contact, None)[0]
    none = {"description": "Great job, apply online", "title": "x", "company": "A"}
    assert outreach.recruiter_box(none, None)[0].startswith("### ⚪ No recruiter or HR named")


# ---- India: only remote India roles; hand-added (email) jobs get the same location rules

@pytest.mark.parametrize("loc", ["Bangalore, Karnataka, India, Greater Noida, Uttar Pradesh, India", "Pune, India"])
def test_onsite_india_skipped_even_if_source_says_remote(loc):
    j = job(loc)
    j["remote"] = True                       # the source flag must not make an on-site India role pass
    assert filters.location_dealbreaker(j) is not None, loc


@pytest.mark.parametrize("loc", ["Remote - India (UK working hours); NOMAD-VISA REMOTE", "Remote, India", "Remote - APAC"])
def test_remote_india_passes(loc):
    assert filters.location_dealbreaker(job(loc)) is None, loc


def test_email_job_in_poland_skipped():
    loc = "Katowice, Poland (hybrid 2 office / 3 remote)"
    assert filters.location_dealbreaker(job(loc)) is not None


# ---- tracker: at most 2 issues per aggregator per run; auto-tailor picks up strong jobs with any extra label

from jobhunter import tracker


def _j(i, company, rank=80, fit=75):
    return {"id": f"id-{i}", "title": f"Platform Engineer {i}", "company": company, "rank": rank,
            "fit": {"fit": fit}, "location": "Berlin, Germany", "remote": False, "source": "lever"}


def test_aggregator_capped_per_run():
    jobs = [_j(1, "jobgether"), _j(2, "jobgether"), _j(3, "jobgether"), _j(4, "acme", rank=70)]
    picked = tracker.pick(jobs, set())
    assert sum(j["company"] == "jobgether" for j in picked) == tracker.MAX_PER_AGGREGATOR
    assert any(j["company"] == "acme" for j in picked)


def test_strong_label_detected_for_nomad_jobs(monkeypatch):
    # a strong nomad job gets labels [..., "fit-strong", "nomad-remote"]; the auto-tailor check must still see it
    issued, tailor_list = [], {}
    class R:
        ok = True
        def json(self): return {"number": 7}
    monkeypatch.setattr(tracker, "_ensure_labels", lambda: None)
    monkeypatch.setattr(tracker, "_existing_job_ids", lambda: set())
    monkeypatch.setattr(tracker, "pick", lambda jobs, already: [{**_j(9, "acme"), "nomad": True, "reasons": [],
                                                              "description": "x", "url": "u", "salary": None,
                                                              "ad_language": "english", "title": "SRE"}])
    monkeypatch.setattr(tracker, "_issue_text", lambda j: ("t", "b", ["job", "new", "fit-strong", "nomad-remote"]))
    monkeypatch.setattr(tracker, "remember_jobs", lambda jobs: None)
    monkeypatch.setattr(tracker.outreach, "markdown", lambda j, d: "")
    monkeypatch.setattr(tracker.outreach, "draft", lambda j: {})
    monkeypatch.setattr(tracker.requests, "post", lambda *a, **k: R())
    monkeypatch.setenv("GITHUB_TOKEN", "x")
    monkeypatch.chdir(__import__("tempfile").mkdtemp())
    tracker.publish([])
    assert open("data/auto_tailor.txt").read() == "7"


@pytest.mark.parametrize("loc", ["Dubai, United Arab Emirates", "Abu Dhabi, UAE", "Riyadh, Saudi Arabia", "Jeddah, KSA"])
def test_gulf_countries_kept(loc):
    assert filters.location_dealbreaker(job(loc)) is None, loc


def test_gulf_nationals_only_skipped():
    j = job("Dubai, UAE")
    j["description"] = "This role is open to UAE nationals only as part of Emiratisation."
    assert filters.find_dealbreaker(j) is not None


def test_pick_skips_agencies_reposters_non_english_and_weak_fit():
    mk = lambda c, f, r, lang="english": {"id": c, "title": "Senior DevOps Engineer " + c, "company": c, "rank": r,
                                          "fit": {"fit": f}, "ad_language": lang}
    jobs = [mk("Adyen", 80, 70), mk("Hays", 85, 80), mk("jobgether", 90, 80), mk("Bol", 60, 70),
            mk("Siemens", 80, 70, "german"), mk("NORDkind Recruiting GmbH", 80, 70)]
    assert [j["company"] for j in tracker.pick(jobs, set())] == ["Adyen"]
