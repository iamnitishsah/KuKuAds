"""Rules-only baseline (no LLM) - the comparison point for the LLM pipeline.

For every possible clip (start at a non-camera beat, 25-45 s long) score:
  hook    = strongest beat in the first 3 s (tone intensity, physical action, ?/!)
  ending  = cliffhanger cue or episode end within the last 3 s, plus intensity of the last line
  heat    = average intensity of the spoken lines
and keep the top non-overlapping clips per episode.
"""
from __future__ import annotations

from .models import Episode, Promo, Segment
from .validate import _overlap, _snap, clip_beats, is_strong, promo_intensity


def _beat_heat(b) -> float:
    return b.intensity + (2 if b.physical else 0) + (1 if b.type == "dialogue" and ("!" in b.text or "?" in b.text) else 0)


def baseline_episode(ep: Episode, per_episode: int = 2, min_s: float = 25, max_s: float = 45) -> list[Promo]:
    beats = [b for b in ep.beats if b.type != "camera"]
    cands = []
    for i, s in enumerate(beats):
        if not is_strong(s):
            continue
        for e in beats[i + 1:]:
            dur = e.end - s.start
            if dur < min_s:
                continue
            if dur > max_s:
                break
            inside = [b for b in beats if s.start <= b.start <= e.end]
            hook = max((_beat_heat(b) for b in inside if b.start - s.start <= 3), default=0)
            tail = [b for b in ep.beats if e.end - 3 <= b.start <= e.end + 0.5]
            ending = (2 if any(b.cliff_cue for b in tail) or ep.duration - e.end <= 3 else 0)
            ending += e.intensity if e.type == "dialogue" else 0
            spoken = [b.intensity for b in inside if b.type == "dialogue"]
            heat = sum(spoken) / len(spoken) if spoken else 0
            cands.append((hook + ending + heat, s, e))
    cands.sort(key=lambda c: c[0], reverse=True)

    chosen: list[Promo] = []
    for sc, s, e in cands:
        st, en = _snap(ep, s.start, e.end)
        p = Promo(promo_id=f"E{ep.number:02d}-B{len(chosen) + 1}", source="baseline",
                  segments=[Segment(ep.number, st, en, s.id, e.id)],
                  hook=s.text[:120], cliffhanger=e.text[:120], why=f"rule score {sc:.2f}",
                  hook_beat=s.id, cliffhanger_beat=e.id, status="valid")
        if all(_overlap(p, c) < 0.3 for c in chosen):
            p.intensity = promo_intensity(clip_beats(ep, p))
            p.scores = {"rule_score": round(sc, 3)}
            chosen.append(p)
        if len(chosen) >= per_episode:
            break
    return chosen
