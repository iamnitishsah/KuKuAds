"""Live demo: check the system, run on screenplays (or the demo), read the ranked promos."""
from __future__ import annotations

import time
from pathlib import Path

import streamlit as st

from ...health import check_backends
from ...pipeline.runner import run_pipeline
from ...selftest import run_selftest, write_demo_run
from .. import state, theme
from ..components import promo_card, run_summary


def _folder_default() -> str:
    raw = state.ROOT / "data" / "raw"
    found = sorted(p for p in raw.glob("*") if p.is_dir()) if raw.exists() else []
    return str(found[0]) if found else ""


def _run(files, folder: str, episodes: str) -> None:
    s, cfg = state.settings(), state.effective_cfg()
    name = f"run-{time.strftime('%Y%m%d-%H%M%S')}"
    out = state.outputs_dir() / name
    if files:
        scripts = out / "input"
        scripts.mkdir(parents=True, exist_ok=True)
        for f in files:
            (scripts / Path(f.name).name).write_bytes(f.getvalue())
    elif folder and Path(folder).is_dir():
        scripts = Path(folder)
    else:
        st.error("Upload screenplays, or give a folder that exists.")
        return
    bar, log, lines = st.progress(0.0), st.empty(), []

    def progress(stage: str, i: int, n: int, msg: str) -> None:
        bar.progress(min(1.0, i / max(n, 1)), text=f"{stage} {i}/{n}")
        lines.append(f"[{stage} {i}/{n}] {msg}")
        log.code("\n".join(lines[-10:]), language=None)

    try:
        with state.session_key(cfg):
            res = run_pipeline(scripts, out, cfg, episodes=episodes or None, do_judge=s["judge"], do_baseline=s["baseline"],
                               progress=progress, cache_dir=state.ROOT / ".cache" / "llm")
    except Exception as e:
        st.error(f"Run failed: {type(e).__name__}: {e}")
        return
    st.session_state["run"] = name
    if res["meta"]["errors"]:
        st.warning(f"Finished with {len(res['meta']['errors'])} error(s); see the run summary.")


def _system_check(cfg: dict) -> None:
    """Self-test and model reachability, on demand (a model check is a network call, so it never runs on page load)."""
    with st.container(border=True):
        a, b, c = st.columns([2, 2, 5])
        if a.button("Run self-test", icon=":material/rule:", help="Offline, on a made-up episode with a stub model."):
            steps = run_selftest()
            st.session_state["selftest"] = all(s["ok"] for s in steps) and len(steps) == 4
            st.session_state["selftest_steps"] = steps
        if b.button("Check models", icon=":material/wifi:", help="Is each configured model reachable?"):
            st.session_state["backends"] = check_backends(state.base_cfg())
        c.caption(state.model_summary(cfg) + " · change in **Settings**")
        steps = st.session_state.get("selftest_steps")
        if steps:
            theme.show("".join(theme.chip(s["step"], "green" if s["ok"] else "red") for s in steps)
                       + (theme.chip("pipeline code is working", "green") if st.session_state.get("selftest") else ""))
        rows = st.session_state.get("backends")
        if rows:
            theme.show("".join(theme.chip(f"{r['stage']}: {r['provider']}/{r['model']}",
                                          "green" if r["reachable"] else "amber" if r["key_set"] and r["reachable"] is None else "red")
                               for r in rows))
            if not any(r["reachable"] or (r["key_set"] and r["reachable"] is None) for r in rows):
                st.warning("No model is reachable, so a real run will fail. Add a key in `.env` or in Settings.")


def render() -> None:
    cfg = state.effective_cfg()
    _system_check(cfg)
    with st.container(border=True):
        left, right = st.columns([3, 2], gap="large")
        with left:
            src = st.radio("Screenplays", ["Upload .txt files", "Folder on this machine"], horizontal=True)
            files, folder = None, ""
            if src.startswith("Upload"):
                files = st.file_uploader("One .txt per episode", type="txt", accept_multiple_files=True)
            else:
                folder = st.text_input("Folder", _folder_default())
        with right:
            episodes = st.text_input("Episodes (optional)", placeholder="1-5,12")
            c = st.columns(3)
            go = c[0].button("Run", type="primary", width="stretch")
            demo = c[1].button("Try the demo", width="stretch", help="A made-up episode and a stub model: no key, no data.")
            if c[2].button("Clear", width="stretch"):
                st.session_state["run"] = None
            runs = [d.name for d in state.list_runs()]
            if runs:
                pick = st.selectbox("Open an earlier run", runs, index=None, placeholder="Choose a run")
                if pick:
                    st.session_state["run"] = pick
    if go:
        _run(files, folder, episodes)
    if demo:
        st.session_state["run"] = write_demo_run(state.outputs_dir() / "demo")

    name = st.session_state.get("run")
    run_dir = state.outputs_dir() / name if name else None
    if not run_dir or not (run_dir / "promos_ranked.json").exists():
        st.info("No run yet. Add screenplays and press **Run**, or press **Try the demo**.")
        return
    run = state.load_run(run_dir)
    rows, meta = run["rows"], run["meta"]
    finder = (meta.get("finder_chain") or [{}])[0].get("model", "-")
    selfg = sum(1 for r in rows if (r.get("judge") or {}).get("served_by") and finder in str(r["judge"]["served_by"]))
    if "demo" in name:
        theme.show('<div class="demo-banner"><b>Demo data.</b> A made-up episode and a stub model, to show the layout. '
                   'These are not real results.</div>')
    top = [r for r in rows if r.get("in_top_list")]
    m = st.columns(4)
    m[0].markdown(theme.stat(len(rows), "valid promos", f"{len(top)} in the top list"), unsafe_allow_html=True)
    m[1].markdown(theme.stat(len(meta.get("episodes", [])), "episodes read"), unsafe_allow_html=True)
    m[2].markdown(theme.stat(selfg, "judged by the finder's model", "should be 0: self-graded scores run generous"), unsafe_allow_html=True)
    m[3].markdown(theme.stat(f"{meta.get('wall_time_s', '-')} s", "wall time", name), unsafe_allow_html=True)
    st.write("")
    st.markdown(f"##### Post these first ({len(top)})")
    for r in top:
        promo_card(r, run["episodes"], meta.get("promo_rules"), key=r["promo_id"])
    rest = [r for r in rows if not r.get("in_top_list")]
    if rest:
        with st.expander(f"Other valid promos ({len(rest)})"):
            for r in rest:
                promo_card(r, run["episodes"], meta.get("promo_rules"), key=r["promo_id"])
    with st.expander("Run summary and downloads"):
        run_summary(run)
    with st.expander("Full report"):
        st.markdown(run["report"] or "No report.")
