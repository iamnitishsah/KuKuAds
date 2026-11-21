"""Reusable pieces: the promo card, run summary and downloads."""
from __future__ import annotations

import streamlit as st

from ..pipeline.judge import clip_transcript
from ..pipeline.models import Promo, Segment, fmt_ts
from . import theme


def segments_text(row: dict) -> str:
    return "; ".join(f"Ep {s['episode']} {fmt_ts(s['start'])}–{fmt_ts(s['end'])}" for s in row["segments"])


def code_checks(row: dict, episodes: dict | None, rules: dict | None = None) -> list[tuple[str, bool]]:
    """Facts recomputed from the run's own data, not taken from the AI."""
    rules = rules or {}
    lo, hi, win = rules.get("min_s", 20), rules.get("max_s", 60), rules.get("hook_window_s", 3)
    out = [(f"{row['duration_s']:.0f} s, within {lo}–{hi} s", lo <= row["duration_s"] <= hi)]
    ep = (episodes or {}).get(row["segments"][0]["episode"])
    hook = ep.beat(row.get("hook_beat", "")) if ep else None
    if hook:
        off = max(0.0, hook.start - row["segments"][0]["start"])
        out.append((f"hook at +{off:.1f} s", off <= win + 1.0))   # +1 s: the start may snap back to the shot edge
    return out


def _promo(row: dict) -> Promo:
    return Promo(row["promo_id"], row["source"], [Segment(**{k: s[k] for k in ("episode", "start", "end", "start_beat", "end_beat")})
                                                  for s in row["segments"]])


def promo_card(row: dict, episodes: dict | None, rules: dict | None, key: str) -> None:
    j = row.get("judge") or {}
    sc = row.get("scores") or {}
    ep = (episodes or {}).get(row["segments"][0]["episode"])
    hook_beat = ep.beat(row.get("hook_beat", "")) if ep else None
    with st.container(border=True):
        model = (row.get("finder_model") or "").split("/")[-1]
        theme.show(f'<div class="ph"><span class="rank">#{row["rank"]}</span><span class="pid">{theme.esc(row["promo_id"])}</span>'
                   f'<span class="meta">{theme.esc(segments_text(row))} · {row["duration_s"]:.0f} s</span><span class="sp"></span>'
                   f'{theme.chip(model, "gray") if model else ""}</div>')
        theme.show(theme.timeline(row["segments"], hook_beat.start if hook_beat else None, ep.duration if ep else None))
        chips = "".join(theme.chip(t, "green" if ok else "amber") for t, ok in code_checks(row, episodes, rules))
        if j and j.get("clarity", 5) <= 3:
            chips += theme.chip("low clarity for a stranger", "amber")
        if row.get("status") == "unjudged":
            chips += theme.chip("could not be judged", "red")
        if not row.get("in_top_list"):
            chips += theme.chip("held back: same episode as a higher pick", "gray")
        for n in row.get("notes") or []:
            chips += theme.chip(f"auto-fix: {n}"[:90], "purple")
        theme.show(chips)
        left, right = st.columns([3, 2], gap="large")
        with left:
            theme.show(theme.quote("Hook", row["hook"]) + theme.quote("Cliffhanger", row["cliffhanger"], "cliff")
                       + theme.quote("Why it works", row["why"], "why"))
        with right:
            if j:
                bars = theme.score_bar("Hook", j.get("hook")) + theme.score_bar("Cliffhanger", j.get("cliffhanger")) + theme.score_bar("Clarity", j.get("clarity"))
                theme.show(bars)
                if sc.get("final") is not None:
                    theme.show(f'<div class="final"><div class="v">{sc["final"]}</div><div class="l">final score</div></div>')
            else:
                st.caption("Not judged in this run.")
        a, b = st.columns(2)
        with a.expander("Read the clip the judge saw"):
            if episodes:
                theme.show(theme.transcript(clip_transcript(_promo(row), episodes)))
            else:
                st.caption("beats.json is not in this run, so the transcript cannot be rebuilt.")
        with b.expander("Why this pick?"):
            if j:
                st.markdown(f"**A cold viewer saw:** {j.get('summary', '')}  \n**Confusing:** {j.get('confusing', '')}  \n"
                            f"**Wants next:** {j.get('want_next', '')}")
                st.caption(f"Judge: {j.get('served_by') or j.get('model')} · repeats {j.get('repeats')} · spread {j.get('spread')}"
                           + (" · FALLBACK model used" if j.get("fallback") else ""))
            if sc:
                st.caption(f"Score parts: hook {sc.get('hook')}, cliffhanger {sc.get('cliffhanger')}, clarity {sc.get('clarity')}, "
                           f"intensity {sc.get('intensity')}, early-episode bonus {sc.get('entry_bonus')}")


def run_summary(run: dict) -> None:
    """Funnel, errors, call counts and downloads for one run."""
    meta, cands = run["meta"], run["candidates"]
    valid = sum(c["status"] == "valid" for c in cands)
    unjudged = sum(c["status"] == "unjudged" for c in cands)
    rejected = len(cands) - valid - unjudged
    theme.show(theme.chip(f"{len(cands)} proposed", "gray") + theme.chip(f"{valid} valid", "green")
               + theme.chip(f"{rejected} rejected", "amber" if rejected else "gray")
               + (theme.chip(f"{unjudged} could not be judged", "red") if unjudged else ""))
    if unjudged:
        st.warning("Some promos could not be judged and are left out of the ranking. Run again to resume from the cache.")
    for c in [c for c in cands if c["status"] == "rejected"][:5]:
        st.caption(f"Rejected {c['promo_id']}: {'; '.join(c['notes'])}")
    st.caption(f"Wall time {meta.get('wall_time_s', '-')} s · errors {len(meta.get('errors') or [])}")
    for e in (meta.get("errors") or [])[:3]:
        st.error(e[:200])
    calls = [c for c in run["calls"] if "error" not in c and not c.get("rate_limited")]
    if calls:
        st.caption(f"{len(calls)} model calls · {sum(c.get('input_tokens', 0) for c in calls):,} tokens in · "
                   f"{sum(c.get('output_tokens', 0) for c in calls):,} out · {sum(1 for c in calls if c.get('cached'))} from cache")
    cols = st.columns(4)
    for col, name in zip(cols, ("promos_ranked.csv", "promos_ranked.json", "report.md", "candidates.json")):
        f = run["dir"] / name
        if f.exists():
            col.download_button(name, f.read_bytes(), file_name=name, key=f"dl-{name}", icon=":material/download:")
    st.caption(f"Saved in `{run['dir']}`")
