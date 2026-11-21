import pytest

from kukuads.llm.client import LLMClient, extract_json
from kukuads.llm.providers import LLMResponse


def test_extract_json_handles_fences_and_chatter():
    assert extract_json('```json\n{"a": 1}\n```') == {"a": 1}
    assert extract_json('Sure! Here it is: {"a": {"b": 2}} hope that helps') == {"a": {"b": 2}}
    with pytest.raises(ValueError):
        extract_json("no json here")


class FakeProvider:
    def __init__(self, replies):
        self.replies = list(replies)
        self.calls = 0

    def complete(self, system, user, **kw):
        self.calls += 1
        r = self.replies.pop(0)
        if isinstance(r, Exception):
            raise r
        return LLMResponse(text=r, model="fake", provider="fake")


def _client(tmp_path, providers):
    chain = [{"provider": f"p{i}", "model": f"m{i}"} for i in range(len(providers))]
    c = LLMClient("finder", chain, {}, {}, cache_dir=tmp_path / "cache", log_path=tmp_path / "log.jsonl")
    c._built = dict(enumerate(providers))
    return c


def test_falls_back_to_next_model_on_api_error(tmp_path):
    p0, p1 = FakeProvider([RuntimeError("429")]), FakeProvider(['{"ok": true}'])
    data, meta = _client(tmp_path, [p0, p1]).complete_json("s", "u")
    assert data == {"ok": True} and meta["fallback"] and meta["model"] == "p1/m1"


class RateLimited(Exception):
    status_code = 429


def test_rate_limit_waits_and_keeps_pinned_model(tmp_path):
    p0 = FakeProvider([RateLimited("Soonest reset ~5s."), '{"ok": true}'])
    p1 = FakeProvider(['{"fallback": true}'])
    c = _client(tmp_path, [p0, p1])
    slept = []
    c._sleep = slept.append
    data, meta = c.complete_json("s", "u")
    assert data == {"ok": True} and not meta["fallback"]
    assert slept == [6.0] and p1.calls == 0


def test_rate_limit_too_long_falls_back(tmp_path):
    p0 = FakeProvider([RateLimited("Soonest reset ~9999s.")])
    p1 = FakeProvider(['{"ok": 2}'])
    c = _client(tmp_path, [p0, p1])
    c._sleep = lambda s: None
    data, meta = c.complete_json("s", "u")
    assert data == {"ok": 2} and meta["fallback"]


def test_variant_is_an_independent_cached_call(tmp_path):
    p0 = FakeProvider(['{"n": 1}', '{"n": 2}'])
    c = _client(tmp_path, [p0])
    assert c.complete_json("s", "u", variant=0)[0] == {"n": 1}
    assert c.complete_json("s", "u", variant=1)[0] == {"n": 2}
    assert c.complete_json("s", "u", variant=1)[0] == {"n": 2} and p0.calls == 2


def test_retries_same_model_once_on_bad_json_then_caches(tmp_path):
    p0 = FakeProvider(["not json", '{"ok": 1}'])
    c = _client(tmp_path, [p0])
    assert c.complete_json("s", "u")[0] == {"ok": 1}
    assert p0.calls == 2
    data, meta = c.complete_json("s", "u")          # served from cache, no new call
    assert meta["cached"] and p0.calls == 2
