"""Reusable pieces: promo card, the code-checked badges, the side panel."""
from __future__ import annotations

import streamlit as st

from ..pipeline.judge import clip_transcript
from ..pipeline.models import Promo, Segment, fmt_ts


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


def promo_card(row: dict, episodes: dict | None, rules: dict | None, key: str) -> None:
    j = row.get("judge") or {}
    with st.container(border=True):
        top = st.columns([5, 2])
        top[0].markdown(f"### #{row['rank']} · {row['promo_id']}")
        top[1].markdown(f"`{(row.get('finder_model') or '').split('/')[-1] or 'model'}`")
        st.caption(f"{segments_text(row)} · {row['duration_s']:.0f} s")
        badges = st.container(horizontal=True)
        for text, ok in code_checks(row, episodes, rules):
            badges.badge(text, icon=":material/check:" if ok else ":material/warning:", color="green" if ok else "orange")
        if j and j.get("clarity", 5) <= 3:
            badges.badge("low clarity for a stranger", icon=":material/help:", color="orange")
        if not row.get("in_top_list"):
            badges.badge("held back: same episode as a higher pick", color="gray")
        st.markdown(f"**Hook:** {row['hook']}  \n**Cliffhanger:** {row['cliffhanger']}  \n**Why it works:** {row['why']}")
        if j:
            c = st.columns(4)
            c[0].metric("Hook", j.get("hook", "-"))
            c[1].metric("Cliffhanger", j.get("cliffhanger", "-"))
            c[2].metric("Clarity", j.get("clarity", "-"))
            c[3].metric("Score", (row.get("scores") or {}).get("final", "-"))
        a, b = st.columns([1, 3])
        if a.button("Show clip", key=f"show-{key}"):
            st.session_state["selected"] = row["promo_id"]
        with b.expander("Why this pick?"):
            st.markdown("**Steps**")
            st.markdown("1. The finder proposed these beats; **code** turned them into timestamps.\n"
                        + "\n".join(f"2. Automatic fix: {n}" for n in row.get("notes") or [])
                        + ("\n" if row.get("notes") else "") + "3. A **different model** read only the clip as a stranger.")
            if j:
                st.markdown(f"**Cold viewer saw:** {j.get('summary', '')}  \n**Confusing:** {j.get('confusing', '')}  \n"
                            f"**Wants next:** {j.get('want_next', '')}")
                st.caption(f"Judge: {j.get('served_by') or j.get('model')} · repeats {j.get('repeats')} · spread {j.get('spread')}"
                           + (" · FALLBACK model used" if j.get("fallback") else ""))
            sc = row.get("scores") or {}
            if sc:
                st.caption(f"Score parts: hook {sc.get('hook')}, cliffhanger {sc.get('cliffhanger')}, clarity {sc.get('clarity')}, "
                           f"intensity {sc.get('intensity')}, early-episode bonus {sc.get('entry_bonus')}")


def side_panel(run: dict) -> None:
    rows, meta = run["rows"], run["meta"]
    t_run, t_clip, t_export = st.tabs(["Run", "Clip", "Export"])
    with t_run:
        cands = run["candidates"]
        valid = sum(c["status"] == "valid" for c in cands)
        st.markdown(f"**Funnel:** {len(cands)} proposed → {valid} valid → {len(cands) - valid} rejected")
        for c in [c for c in cands if c["status"] == "rejected"][:5]:
            st.caption(f"{c['promo_id']}: {'; '.join(c['notes'])}")
        st.markdown(f"**Wall time:** {meta.get('wall_time_s', '-')} s · **errors:** {len(meta.get('errors') or [])}")
        for e in (meta.get("errors") or [])[:3]:
            st.error(e[:200])
        calls = [c for c in run["calls"] if "error" not in c and not c.get("rate_limited")]
        if calls:
            st.caption(f"{len(calls)} model calls, {sum(c.get('input_tokens', 0) for c in calls):,} tokens in, "
                       f"{sum(c.get('output_tokens', 0) for c in calls):,} out, "
                       f"{sum(1 for c in calls if c.get('cached'))} from cache")
    with t_clip:
        pid = st.session_state.get("selected")
        row = next((r for r in rows if r["promo_id"] == pid), None)
        if not row:
            st.info("Press **Show clip** on a promo to read exactly what the judge saw.")
        elif not run["episodes"]:
            st.warning("beats.json is not in this run, so the clip transcript cannot be rebuilt.")
        else:
            promo = Promo(row["promo_id"], row["source"], [Segment(**{k: s[k] for k in ("episode", "start", "end", "start_beat", "end_beat")})
                                                           for s in row["segments"]])
            st.markdown(f"**{row['promo_id']}** · {segments_text(row)}")
            st.code(clip_transcript(promo, run["episodes"]), language=None)
    with t_export:
        for name in ("promos_ranked.csv", "promos_ranked.json", "report.md", "candidates.json"):
            f = run["dir"] / name
            if f.exists():
                st.download_button(f"Download {name}", f.read_bytes(), file_name=name, key=f"dl-{name}")
        st.caption(f"Saved in `{run['dir']}`")
