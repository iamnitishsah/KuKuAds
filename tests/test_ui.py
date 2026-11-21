import os
from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

APP = Path(__file__).resolve().parents[1] / "app.py"


@pytest.fixture
def app(tmp_path, monkeypatch):
    monkeypatch.setenv("KUKUADS_OUTPUTS", str(tmp_path))
    return AppTest.from_file(str(APP), default_timeout=90).run()


def _click(at, label):
    [b for b in at.button if b.label == label][0].click()
    return at.run()


def test_app_loads_with_five_tabs(app):
    assert not app.exception
    assert [t.label for t in app.tabs] == ["Overview", "Find promos", "How it works", "Evaluation", "Status"]


def test_demo_run_shows_a_card_and_the_clip(app):
    _click(app, "Try the demo")
    assert not app.exception
    assert any("#1 · E01-P1" in str(m.value) for m in app.markdown)
    # the demo's finder and judge differ, so nothing counts as self-graded
    assert dict((m.label, m.value) for m in app.metric)["Judged by the finder's model"] == "0"
    _click(app, "Show clip")
    assert not app.exception and any("on screen" in c.value for c in app.code)


def test_status_selftest_button(app):
    _click(app, "Run self-test")
    assert any("working" in s.value for s in app.success)


def test_session_key_is_restored(monkeypatch):
    from kukuads.ui import state
    monkeypatch.setattr(state, "settings", lambda: {**state.DEFAULTS, "api_key": "secret"})
    monkeypatch.delenv("GROQ_API_KEY", raising=False)
    cfg = {"providers": {"groq": {"api_key_env": "GROQ_API_KEY"}}, "stages": {"finder": [{"provider": "groq", "model": "m"}]}}
    with state.session_key(cfg):
        assert os.environ["GROQ_API_KEY"] == "secret"
    assert "GROQ_API_KEY" not in os.environ
