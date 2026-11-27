"""Google busy for a long time must not hang the robot run."""
from jobhunter import skill_fit


def _jobs(n):
    return [{"id": f"j{i}", "title": "Platform Engineer", "description": "Azure AKS " * 50, "company": "x",
             "location": "Berlin"} for i in range(n)]


def test_stops_after_two_failures_in_a_row(monkeypatch, tmp_path):
    calls = {"n": 0}
    monkeypatch.setattr(skill_fit, "api_key", lambda: "k")
    monkeypatch.setattr(skill_fit, "_load_cache", lambda: {})
    monkeypatch.setattr(skill_fit, "_save_cache", lambda c: None)
    monkeypatch.setattr(skill_fit, "PAUSE_SECONDS", 0)
    monkeypatch.setattr(skill_fit.posting_guard, "check", lambda j: [])

    def busy(job):
        calls["n"] += 1
        raise RuntimeError("Gemini rate limit: try again later")
    monkeypatch.setattr(skill_fit, "_ask_gemini", busy)
    skill_fit.add_fit(_jobs(10))
    assert calls["n"] == 2                     # gave up after 2 failed jobs instead of trying all 10
    assert skill_fit._DEADLINE is None and skill_fit.GOOGLE_BUSY
    skill_fit.GOOGLE_BUSY = False


def test_budget_blocks_long_waits(monkeypatch):
    import time
    monkeypatch.setattr(skill_fit, "_DEADLINE", time.monotonic() + 1)
    try:
        skill_fit._sleep(60)
        assert False, "should not sleep past the budget"
    except skill_fit.GeminiBudgetUsed:
        pass


def test_outreach_skipped_once_google_busy(monkeypatch):
    calls = {"n": 0}
    monkeypatch.setattr(skill_fit, "GOOGLE_BUSY", False)

    def busy(prompt, temperature=0.1):
        calls["n"] += 1
        raise skill_fit.GeminiBudgetUsed("busy")
    monkeypatch.setattr(skill_fit, "ask_json", busy)
    for _ in range(3):
        try:
            skill_fit.ask_json_quick("x")
        except skill_fit.GeminiBudgetUsed:
            pass
    assert calls["n"] == 1 and skill_fit.GOOGLE_BUSY and skill_fit._DEADLINE is None


class _Resp:
    def __init__(self, status, payload=None, text=""):
        self.status_code, self._payload, self.text = status, payload, text

    def json(self):
        return self._payload

    def raise_for_status(self):
        if self.status_code >= 400:
            raise RuntimeError(self.status_code)


def test_gemini_busy_switches_to_groq(monkeypatch):
    monkeypatch.setenv("GROQ_API_KEY", "g")
    monkeypatch.setattr(skill_fit, "USE_FALLBACK", False)
    monkeypatch.setattr(skill_fit, "api_key", lambda: "k")
    monkeypatch.setattr(skill_fit.time, "sleep", lambda s: None)
    urls = []

    def post(url, json=None, timeout=None, headers=None):
        urls.append(url)
        if "googleapis" in url:
            return _Resp(503)
        if json["model"] == "openai/gpt-oss-120b":
            return _Resp(429)                     # first Groq model at its limit -> next model
        return _Resp(200, {"choices": [{"message": {"content": '{"fit": 80}'}}]})

    monkeypatch.setattr(skill_fit.requests, "post", post)
    assert skill_fit.ask_json("prompt") == {"fit": 80}
    assert sum("googleapis" in u for u in urls) == 2 and skill_fit.USE_FALLBACK
    urls.clear()
    assert skill_fit.ask_json("prompt 2") == {"fit": 80}           # rest of the run goes straight to Groq
    assert not any("googleapis" in u for u in urls)


def test_no_groq_key_keeps_gemini_behaviour(monkeypatch):
    monkeypatch.delenv("GROQ_API_KEY", raising=False)
    monkeypatch.setattr(skill_fit, "USE_FALLBACK", False)
    assert skill_fit._switch_to_fallback() is False
