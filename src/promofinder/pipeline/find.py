"""Stage 2 - Find candidate promos (LLM, one call per episode).

The LLM sees numbered beats and answers with beat IDs only; code turns IDs into
timestamps later, so the model can never invent a timestamp.
"""
from __future__ import annotations

from .models import Beat, Episode, fmt_ts
from .prompts import FINDER_SYSTEM, FINDER_USER


def beat_line(b: Beat) -> str:
    span = f"[{fmt_ts(b.start)}-{fmt_ts(b.end)}]"
    if b.type == "dialogue":
        tone = f" ({', '.join(b.tags)})" if b.tags else ""
        return f"{b.id} {span} {b.speaker}{tone}: {b.text}"
    if b.type == "action":
        return f"{b.id} {span} [ACTION] {b.text}"
    if b.type == "sfx":
        return f"{b.id} {span} [SOUND] {b.text}"
    return f"{b.id} {span} [SHOT] {b.text}"


def prompt_beats(ep: Episode) -> list[Beat]:
    """Dialogue, action and sound go to the LLM; camera lines only when they carry a key visual."""
    return [b for b in ep.beats if b.type != "camera" or b.physical or b.cliff_cue]


def build_finder_prompt(ep: Episode, episodes: list[Episode], max_promos: int = 3) -> tuple[str, str]:
    by_num = {e.number: e for e in episodes}
    first = episodes[0]
    prev = by_num.get(ep.number - 1)
    user = FINDER_USER.format(
        premise=first.logline if ep.number != first.number else "(this is episode 1)",
        prev_num=prev.number if prev else "-",
        previously=prev.logline if prev else "(none - first episode)",
        num=ep.number, length=fmt_ts(ep.duration), logline=ep.logline,
        beats="\n".join(beat_line(b) for b in prompt_beats(ep)),
    )
    return FINDER_SYSTEM.format(max_promos=max_promos), user


def find_candidates(ep: Episode, episodes: list[Episode], client, max_promos: int = 3) -> tuple[list[dict], dict]:
    """Returns the raw promo dicts proposed by the LLM plus call metadata."""
    system, user = build_finder_prompt(ep, episodes, max_promos)
    data, meta = client.complete_json(system, user, tag=f"find:E{ep.number:02d}")
    promos = data.get("promos", []) if isinstance(data, dict) else []
    return [p for p in promos if isinstance(p, dict)][:max_promos], meta
