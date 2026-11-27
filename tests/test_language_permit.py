"""Language / work-permit rules found missing on 25 Nov (LinkedIn ads from the new countries)."""
import pytest

from jobhunter import filters

EN = "We are looking for an Azure DevOps engineer to join our team and you will work with our platform. " * 6


def job(extra, location="Berlin, Germany"):
    return {"title": "Azure DevOps Engineer", "description": EN + extra, "location": location,
            "company": "x", "source": "greenhouse"}


@pytest.mark.parametrize("text", [
    "Good communication skills in Swedish and English.",
    "God kommunikativ förmåga på svenska och engelska.",
    "Du taler flydende dansk.",
    "Nivel alto de español.",
    "You hold a valid work permit for the Netherlands.",
    "A valid EU work permit is required.",
    "You must be eligible to work in the EU.",
    "We are unable to offer visa sponsorship.",
    "Candidates must be able to work without the need for sponsorship.",
])
def test_blocked(text):
    assert filters.find_dealbreaker(job(text)) is not None, text


@pytest.mark.parametrize("text", [
    "Swedish is a plus.",
    "Proficiency in Dutch is considered an advantage.",
    "We provide full support with visa processes and relocation.",
    "Visa sponsorship available for you and your family.",
    "Please tell us your start date and whether you hold a valid work permit for Germany.",
])
def test_allowed(text):
    assert filters.find_dealbreaker(job(text)) is None, text


def test_ad_written_in_dutch_is_kept_unless_dutch_required(monkeypatch):
    dutch = "Wij zoeken een DevOps engineer voor ons team. Je werkt met Azure en Kubernetes en het platform van onze klanten. " * 6
    j = {"title": "DevOps Engineer", "description": dutch, "location": "Utrecht, Netherlands", "company": "x", "source": "greenhouse"}
    assert filters.guess_language(dutch) == "dutch"
    assert filters.find_dealbreaker(j) is None                       # kept, labelled ad-not-english later
    j["description"] = dutch + " Je spreekt vloeiend Nederlands."
    assert "language required" in filters.find_dealbreaker(j)
    monkeypatch.setattr(filters, "SKIP_NON_ENGLISH_ADS", True)       # strict mode skips it anyway
    j["description"] = dutch
    assert "not in English" in filters.find_dealbreaker(j)


def test_julius_baer_zurich_is_kept_but_other_zurich_jobs_are_not():
    from jobhunter.filters import location_dealbreaker
    jb = {"title": "Platform Engineer", "company": "juliusbaer", "location": "Zurich",
          "url": "https://juliusbaer.wd3.myworkdayjobs.com/en-US/External/job/Zurich/Platform-Engineer_r-20212-1"}
    other = {"title": "Platform Engineer", "company": "somebank", "location": "Zurich, Switzerland", "url": "https://x.example/job"}
    assert location_dealbreaker(jb) is None
    assert location_dealbreaker(other)
