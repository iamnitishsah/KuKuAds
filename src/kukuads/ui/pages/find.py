"""Find promos: choose screenplays, run, read the ranked promos."""
from __future__ import annotations

import time
from pathlib import Path

import streamlit as st

from ...pipeline.runner import run_pipeline
from ...selftest import write_demo_run
from .. import state
from ..components import promo_card, side_panel


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
    st.session_state["run"], st.session_state["selected"] = name, None
    if res["meta"]["errors"]:
        st.warning(f"Finished with {len(res['meta']['errors'])} error(s); see the Run panel.")


def render() -> None:
    cfg = state.effective_cfg()
    left, right = st.columns([3, 2], gap="large")
    with left:
        with st.container(border=True):
            src = st.radio("Screenplays", ["Upload .txt files", "Folder on this machine"], horizontal=True)
            files, folder = None, ""
            if src.startswith("Upload"):
                files = st.file_uploader("One .txt per episode", type="txt", accept_multiple_files=True)
            else:
                folder = st.text_input("Folder", _folder_default())
            episodes = st.text_input("Episodes (optional)", placeholder="1-5,12")
            st.caption(state.model_summary(cfg) + " · change in **Settings**")
            c = st.columns([1, 1, 1, 3])
            go = c[0].button("Run", type="primary")
            demo = c[1].button("Try the demo", help="A made-up episode and a stub model: no key, no data.")
            if c[2].button("New run"):
                st.session_state["run"] = st.session_state["selected"] = None
        if go:
            _run(files, folder, episodes)
        if demo:
            st.session_state["run"], st.session_state["selected"] = write_demo_run(state.outputs_dir() / "demo"), None

        runs = state.list_runs()
        names = [d.name for d in runs]
        if names:
            with st.expander("Open an earlier run"):
                pick = st.selectbox("Run", names, index=None, placeholder="Choose a run")
                if pick:
                    st.session_state["run"] = pick

        name = st.session_state.get("run")
        run_dir = state.outputs_dir() / name if name else None
        if not run_dir or not (run_dir / "promos_ranked.json").exists():
            st.info("No run yet. Add screenplays and press **Run**, or **Try the demo**.")
            return
        run = state.load_run(run_dir)
        rows, meta = run["rows"], run["meta"]
        finder = (meta.get("finder_chain") or [{}])[0].get("model", "-")
        selfg = sum(1 for r in rows if (r.get("judge") or {}).get("served_by") and finder in str(r["judge"]["served_by"]))
        m = st.columns(4)
        m[0].metric("Valid promos", len(rows))
        m[1].metric("Episodes", len(meta.get("episodes", [])))
        m[2].metric("Judged by the finder's model", selfg, help="Should be 0: a model grading its own picks scores generously.")
        m[3].metric("Run", name)
        top = [r for r in rows if r.get("in_top_list")]
        st.subheader(f"Post these first ({len(top)})")
        for r in top:
            promo_card(r, run["episodes"], meta.get("promo_rules"), key=r["promo_id"])
        rest = [r for r in rows if not r.get("in_top_list")]
        if rest:
            with st.expander(f"Other valid promos ({len(rest)})"):
                for r in rest:
                    promo_card(r, run["episodes"], meta.get("promo_rules"), key=r["promo_id"])
        with st.expander("Full report"):
            st.markdown(run["report"] or "No report.")
    with right:
        if st.session_state.get("run") and run_dir and (run_dir / "promos_ranked.json").exists():
            side_panel(run)
        else:
            st.caption("The run summary, the clip the judge saw, and downloads appear here after a run.")
