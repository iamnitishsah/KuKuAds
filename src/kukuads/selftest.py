"""Offline self-test: runs parse -> validate -> judge -> rank on a tiny synthetic episode.

No network, no API key and no confidential data: the two LLM stages are answered by a stub client.
It proves the pipeline code runs; it says nothing about how good a real model's picks are.
"""
from __future__ import annotations

from .pipeline.judge import judge_promo
from .pipeline.parse import parse_screenplay
from .pipeline.rank import rank
from .pipeline.validate import validate_episode

SAMPLE = """EPISODE NUMBER: Episode 1
EPISODE LOGLINE: A bride is abandoned at the altar.
CONTINUITY NOTES: First episode.

SCENE 01
**CAMERA:**
Start: (00:00.00) | End: (00:04.00)
Wide shot of the cathedral doors.

**MATRIARCH (Cold, Commanding):**
Start: (00:04.00) | End: (00:07.00)
"You should turn around, Anna!"

**ANNA (Desperate, Unbelieving):**
Start: (00:07.50) | End: (00:10.00)
"Ben is waiting for me."

**BEN (Cruel, Smug):**
Start: (00:11.00) | End: (00:15.00)
"I changed my mind. I am marrying your sister."

**ACTION:**
Start: (00:15.00) | End: (00:19.00)
Anna's bouquet falls to the floor as the guests stare.

**ANNA (Devastated, Furious):**
Start: (00:20.00) | End: (00:24.00)
"You promised me everything!"

**SISTER (Gloating, Menacing):**
Start: (00:25.00) | End: (00:30.00)
"Everything was never yours, sister."

**SOUND FX:**
Start: (00:30.00) | End: (00:36.00)
Strings swell to an ominous cliffhanger peak.
"""


class _StubClient:
    """Stands in for LLMClient: canned JSON, same `complete_json` signature."""

    def __init__(self, reply: dict):
        self.reply = reply

    def complete_json(self, system, user, tag="", variant=0):
        return self.reply, {"model": "stub/stub", "served_by": "stub", "fallback": False}


def run_selftest() -> list[dict]:
    """Returns [{"step", "ok", "detail"}, ...]; never raises."""
    steps: list[dict] = []
    state: dict = {}

    def parse():
        state["ep"] = parse_screenplay(SAMPLE)
        n = len(state["ep"].beats)
        return n == 8 and state["ep"].duration == 36.0, f"{n} beats, {state['ep'].duration:.0f} s"

    def find_and_validate():
        raw = {"segments": [{"start_beat": "E01-B002", "end_beat": "E01-B008"}], "hook_beat": "E01-B002",
               "cliffhanger_beat": "E01-B008", "hook": "turn around", "cliffhanger": "strings swell", "why": "betrayal"}
        state["promos"] = validate_episode([raw], state["ep"], {"min_s": 20, "max_s": 60, "hook_window_s": 3}, "stub")
        p = state["promos"][0]
        return p.status == "valid" and 20 <= p.duration <= 60, f"{p.status}, {p.start_end()}"

    def judge():
        p = state["promos"][0]
        judge_promo(p, {1: state["ep"]}, _StubClient({"hook": 5, "cliffhanger": 4, "clarity": 4, "summary": "x"}), repeats=2)
        return p.judge.get("hook") == 5 and p.judge.get("fallback") is False, f"hook {p.judge.get('hook')}"

    def ranking():
        rows = rank(state["promos"], {"weights": {"hook": .3, "cliffhanger": .3, "clarity": .3, "intensity": .1}})
        return rows[0]["promo_id"] == "E01-P1" and rows[0]["in_top_list"], f"top: {rows[0]['promo_id']}, score {rows[0]['scores']['final']}"

    for name, fn in [("Parse a screenplay", parse), ("Validate a proposed promo", find_and_validate),
                     ("Judge the clip (stub model)", judge), ("Rank", ranking)]:
        try:
            ok, detail = fn()
        except Exception as e:   # a crash is a failed step, not a crashed app
            ok, detail = False, f"{type(e).__name__}: {e}"
        steps.append({"step": name, "ok": bool(ok), "detail": detail})
        if not ok:
            break
    return steps


def write_demo_run(out_dir) -> str:
    """Write a complete run folder (same files a real run writes) from the synthetic episode and stub judge.

    Lets the app be shown, and its Results view tested, with no key and no screenplay data."""
    import json
    import time
    from pathlib import Path

    from .pipeline.report import write_report

    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    ep = parse_screenplay(SAMPLE)
    raws = [{"segments": [{"start_beat": "E01-B002", "end_beat": "E01-B008"}], "hook_beat": "E01-B002",
             "cliffhanger_beat": "E01-B008", "hook": "\"You should turn around, Anna!\"",
             "cliffhanger": "Strings swell after \"Everything was never yours, sister.\"",
             "why": "A public betrayal at the altar, then a cruel line left hanging.", "patterns": ["betrayal or shocking reveal"]}]
    cfg = {"min_s": 20, "max_s": 60, "hook_window_s": 3}
    promos = validate_episode(raws, ep, cfg, "demo/stub")
    stub = _StubClient({"hook": 5, "cliffhanger": 4, "clarity": 4, "summary": "A bride is jilted in public.",
                        "confusing": "nothing", "want_next": "What will Anna do?"})
    for pr in promos:
        judge_promo(pr, {1: ep}, stub, repeats=2)
    rows = rank(promos, {"weights": {"hook": .3, "cliffhanger": .3, "clarity": .3, "intensity": .1}, "top_n": 15})
    meta = {"scripts_dir": "demo", "episodes": [1], "finder_chain": [{"provider": "demo", "model": "demo-finder"}],
            "judge_chain": [{"provider": "demo", "model": "stub"}], "promo_rules": cfg, "ranking": {},
            "wall_time_s": 0.0, "errors": [], "finished_at": time.strftime("%Y-%m-%d %H:%M:%S")}
    (out / "beats.json").write_text(json.dumps([ep.to_dict()], ensure_ascii=False), encoding="utf-8")
    (out / "promos_ranked.json").write_text(json.dumps(rows, ensure_ascii=False, indent=1), encoding="utf-8")
    (out / "candidates.json").write_text(json.dumps([p.to_dict() for p in promos], ensure_ascii=False), encoding="utf-8")
    (out / "run_meta.json").write_text(json.dumps(meta, indent=1), encoding="utf-8")
    write_report(out, [ep], promos, rows, [], meta)
    return out.name
