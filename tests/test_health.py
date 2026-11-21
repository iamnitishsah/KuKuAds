from kukuads.health import check_backends

CFG = {
    "providers": {
        "local": {"type": "openai_compatible", "base_url": "http://127.0.0.1:9/v1", "api_key_env": "T_KEY"},
        "cloud": {"type": "anthropic", "api_key_env": "T_ANTHROPIC"},
        "tunnel": {"type": "openai_compatible", "base_url_env": "T_URL", "api_key_env": "T_KEY"},
    },
    "stages": {"finder": [{"provider": "local", "model": "m1"}, {"provider": "cloud", "model": "m2"}],
               "judge": [{"provider": "tunnel", "model": "m3"}]},
}


def test_missing_key_is_reported_not_raised(monkeypatch):
    for k in ("T_KEY", "T_ANTHROPIC", "T_URL"):
        monkeypatch.delenv(k, raising=False)
    rows = check_backends(CFG)
    assert [r["key_set"] for r in rows] == [False, False, False]
    assert "T_KEY is not set" in rows[0]["detail"]


def test_unreachable_endpoint_and_unprobed_anthropic(monkeypatch):
    monkeypatch.setenv("T_KEY", "x")
    monkeypatch.setenv("T_ANTHROPIC", "x")
    monkeypatch.delenv("T_URL", raising=False)
    rows = check_backends(CFG, timeout=1)
    assert rows[0]["reachable"] is False                      # nothing listens on port 9
    assert rows[1]["reachable"] is None and rows[1]["key_set"]  # anthropic: key only
    assert "T_URL is not set" in rows[2]["detail"]
