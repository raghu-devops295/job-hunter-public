"""Offline checks for rate-limit handling (no network). Run: python -m pytest tests -q"""
import time
from unittest import mock

from jobhunter.sources import common, company_boards


class FakeResponse:
    def __init__(self, status, payload=None, headers=None):
        self.status_code, self._payload, self.headers = status, payload, headers or {}

    def raise_for_status(self):
        if self.status_code >= 400:
            raise RuntimeError(f"HTTP {self.status_code}")

    def json(self):
        return self._payload


def test_get_json_retries_429_then_succeeds(monkeypatch):
    responses = [FakeResponse(429), FakeResponse(503), FakeResponse(200, {"ok": 1})]
    monkeypatch.setattr(common.requests, "get", lambda *a, **k: responses.pop(0))
    monkeypatch.setattr(common.time, "sleep", lambda s: None)
    assert common.get_json("https://example.test") == {"ok": 1}


def test_get_json_gives_up_after_three_tries(monkeypatch):
    calls = []
    monkeypatch.setattr(common.requests, "get", lambda *a, **k: calls.append(1) or FakeResponse(429))
    monkeypatch.setattr(common.time, "sleep", lambda s: None)
    try:
        common.get_json("https://example.test")
        assert False, "should have raised"
    except RuntimeError:
        pass
    assert len(calls) == 3


def test_get_json_404_is_none_without_retry(monkeypatch):
    calls = []
    monkeypatch.setattr(common.requests, "get", lambda *a, **k: calls.append(1) or FakeResponse(404))
    assert common.get_json("https://example.test") is None
    assert len(calls) == 1


def test_failing_system_is_paused_after_repeated_errors(monkeypatch):
    seen = []

    def bad(company):
        seen.append(company)
        raise RuntimeError("HTTP 429")

    monkeypatch.setitem(company_boards.FETCHERS, "fake", bad)
    monkeypatch.setitem(company_boards.THROTTLE_SECONDS, "fake", 0)
    companies = [f"c{i}" for i in range(12)]
    jobs, missing = company_boards.fetch_all({"fake": companies})
    assert jobs == [] and missing == []
    assert len(seen) < len(companies)                  # the rest of the system was skipped
    assert len(seen) >= company_boards.MAX_ERRORS_PER_SYSTEM


def test_throttle_spaces_requests(monkeypatch):
    stamps = []
    monkeypatch.setitem(company_boards.FETCHERS, "slow", lambda c: stamps.append(time.monotonic()) or [])
    monkeypatch.setitem(company_boards.THROTTLE_SECONDS, "slow", 0.05)
    company_boards.fetch_all({"slow": ["a", "b", "c"]})
    gaps = sorted(b - a for a, b in zip(stamps, stamps[1:]))
    assert len(stamps) == 3 and min(gaps) >= 0.04
