"""Stage 4b - Rank promos (pure code).

final = weighted judge scores (hook, cliffhanger, clarity, each scaled 0-1)
      + weight * intensity (from the screenplay's own tone tags)
      + entry-point bonus for early episodes (a viewer who taps the ad lands on episode 1)
Then a diversity pass: at most N promos per episode in the top list.
"""
from __future__ import annotations

from .models import Promo


def score(p: Promo, cfg: dict) -> float:
    w = cfg.get("weights", {})
    j = p.judge or {}
    if not j:
        p.scores = {"final": 0.0, "note": "not judged"}
        return 0.0
    s = {k: round((j.get(k, 1) - 1) / 4, 3) for k in ("hook", "cliffhanger", "clarity")}
    s["intensity"] = p.intensity
    final = sum(w.get(k, 0) * v for k, v in s.items())
    bonus = cfg.get("entry_point_bonus", 0) if min(p.episodes) <= cfg.get("entry_point_episodes", 0) else 0
    s["entry_bonus"] = bonus
    s["final"] = round(final + bonus, 4)
    p.scores = s
    return s["final"]


def rank(promos: list[Promo], cfg: dict) -> list[dict]:
    """Returns rows in posting order. Promos held back for diversity come after the top list."""
    valid = [p for p in promos if p.status == "valid"]
    for p in valid:
        score(p, cfg)
    valid.sort(key=lambda p: p.scores.get("final", 0), reverse=True)

    cap = cfg.get("max_per_episode_in_top", 1)
    top_n = cfg.get("top_n", 15)
    per_ep: dict[int, int] = {}
    top, rest = [], []
    for p in valid:
        key = min(p.episodes)
        if len(top) < top_n and per_ep.get(key, 0) < cap:
            top.append(p)
            per_ep[key] = per_ep.get(key, 0) + 1
        else:
            rest.append(p)

    rows = []
    for i, p in enumerate(top + rest, 1):
        rows.append({"rank": i, "in_top_list": i <= len(top), **p.to_dict()})
    return rows
