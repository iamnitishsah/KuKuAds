"""Stage 4a - Cold-viewer judge (LLM).

A separate model sees ONLY the clip's transcript: no logline, no story so far, no
character list - exactly what a stranger scrolling TikTok has. It scores hook,
cliffhanger and clarity, and says what confused it.

Each clip can be judged several times (`repeats`); scores are averaged and the
spread between repeats is kept, so the report can show how consistent the judge is.
"""
from __future__ import annotations

from statistics import mean

from ..llm import LLMError
from .models import Episode, Promo
from .prompts import JUDGE_SYSTEM, JUDGE_USER

DIMS = ("hook", "cliffhanger", "clarity")


def clip_transcript(promo: Promo, episodes_by_num: dict[int, Episode]) -> str:
    lines, offset = [], 0.0
    for k, seg in enumerate(promo.segments):
        if k:
            lines.append("[CUT TO A LATER MOMENT]")
        ep = episodes_by_num[seg.episode]
        for b in ep.beats:
            if not (seg.start - 0.01 <= b.start < seg.end):
                continue
            t = offset + b.start - seg.start
            if b.type == "dialogue":
                tone = f" ({', '.join(b.tags)})" if b.tags else ""
                lines.append(f"[{t:4.1f}s] {b.speaker}{tone}: {b.text}")
            elif b.type in ("action", "camera"):
                # A real viewer SEES the shots (a bride in white, a hand held at the altar),
                # so the judge gets the visual descriptions too.
                lines.append(f"[{t:4.1f}s] (on screen) {b.text}")
            elif b.type == "sfx":
                lines.append(f"[{t:4.1f}s] (sound) {b.text}")
        offset += seg.duration
    return "\n".join(lines)


def _score(v, default=1) -> int:
    try:
        return max(1, min(5, int(round(float(v)))))
    except (TypeError, ValueError):
        return default


def judge_promo(promo: Promo, episodes_by_num: dict[int, Episode], client, repeats: int = 1) -> Promo:
    clip = clip_transcript(promo, episodes_by_num)
    user = JUDGE_USER.format(duration=promo.duration, clip=clip)
    runs, last_error = [], None
    for k in range(max(1, repeats)):
        try:
            data, meta = client.complete_json(JUDGE_SYSTEM, user, tag=f"judge:{promo.promo_id}#{k + 1}", variant=k)
        except LLMError as e:       # one failed repeat must not throw away the ones that worked
            last_error = e
            continue
        runs.append(({d: _score(data.get(d)) for d in DIMS}, data, meta))
    if not runs:
        raise last_error
    if len(runs) < max(1, repeats):
        promo.notes.append(f"judged {len(runs)} of {repeats} times (a repeat failed): scores are less reliable")

    first, meta = runs[0][1], runs[0][2]
    promo.judge = {
        "summary": str(first.get("summary", "")),
        "confusing": str(first.get("confusing", "")),
        "want_next": str(first.get("want_next", "")),
        **{d: round(mean(r[0][d] for r in runs), 2) for d in DIMS},
        "repeats": [r[0] for r in runs],
        "spread": round(max(max(r[0][d] for r in runs) - min(r[0][d] for r in runs) for d in DIMS), 2),
        "would_watch_next_episode": bool(first.get("would_watch_next_episode", False)),
        "model": meta.get("model"), "served_by": meta.get("served_by"),
        "fallback": any(r[2].get("fallback") for r in runs),
    }
    return promo
