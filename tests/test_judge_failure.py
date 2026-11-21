import pytest

from kukuads.llm import LLMError
from kukuads.pipeline.judge import judge_promo
from kukuads.pipeline.parse import parse_screenplay
from kukuads.pipeline.runner import run_pipeline
from kukuads.pipeline.validate import validate_episode
from kukuads.selftest import SAMPLE

RAW = {"segments": [{"start_beat": "E01-B002", "end_beat": "E01-B008"}], "hook_beat": "E01-B002",
       "cliffhanger_beat": "E01-B008", "hook": "h", "cliffhanger": "c", "why": "w"}
OK = {"hook": 4, "cliffhanger": 4, "clarity": 4, "summary": "s"}
META = {"model": "stub", "served_by": "stub", "fallback": False}


class Scripted:
    """complete_json answers from a list; an Exception in the list is raised."""

    def __init__(self, replies):
        self.replies = list(replies)

    def complete_json(self, system, user, tag="", variant=0):
        r = self.replies.pop(0)
        if isinstance(r, Exception):
            raise r
        return r, META


def _promo():
    ep = parse_screenplay(SAMPLE)
    return ep, validate_episode([RAW], ep, {"min_s": 20, "max_s": 60, "hook_window_s": 3})[0]


def test_one_failed_repeat_keeps_the_other_and_says_so():
    ep, p = _promo()
    judge_promo(p, {1: ep}, Scripted([OK, LLMError("boom")]), repeats=2)
    assert p.judge["hook"] == 4 and len(p.judge["repeats"]) == 1
    assert any("1 of 2" in n for n in p.notes)


def test_all_repeats_failing_raises():
    ep, p = _promo()
    with pytest.raises(LLMError):
        judge_promo(p, {1: ep}, Scripted([LLMError("a"), LLMError("b")]), repeats=2)


def _run(tmp_path, monkeypatch, judge):
    (tmp_path / "in").mkdir()
    (tmp_path / "in" / "episode-001.txt").write_text(SAMPLE, encoding="utf-8")
    finder = Scripted([{"promos": [RAW]}])
    monkeypatch.setattr("kukuads.pipeline.runner.make_clients", lambda cfg, out, cache: {"finder": finder, "judge": judge})
    cfg = {"stages": {"finder": [{"provider": "s", "model": "f"}], "judge": [{"provider": "s", "model": "j"}]},
           "promo": {"min_s": 20, "max_s": 60, "hook_window_s": 3}, "judge_repeats": 1,
           "ranking": {"weights": {"hook": .3, "cliffhanger": .3, "clarity": .3, "intensity": .1}}}
    return run_pipeline(tmp_path / "in", tmp_path / "out", cfg, do_baseline=False, progress=lambda *a: None,
                        cache_dir=tmp_path / "cache")


def test_a_promo_that_cannot_be_judged_is_left_out_of_the_ranking(tmp_path, monkeypatch):
    res = _run(tmp_path, monkeypatch, Scripted([LLMError("rate limited")]))
    assert res["ranked"] == [] and res["meta"]["unjudged"] == ["E01-P1"]
    assert "Could not be judged: 1" in (tmp_path / "out" / "report.md").read_text(encoding="utf-8")
    import json
    assert json.loads((tmp_path / "out" / "candidates.json").read_text())[0]["status"] == "unjudged"


def test_a_judged_promo_is_ranked(tmp_path, monkeypatch):
    res = _run(tmp_path, monkeypatch, Scripted([OK]))
    assert [r["promo_id"] for r in res["ranked"]] == ["E01-P1"] and res["meta"]["unjudged"] == []
