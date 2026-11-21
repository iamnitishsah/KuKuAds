"""Streamlit app for KuKuAds: check that it runs, run the pipeline, browse results.

    streamlit run app.py
"""
from __future__ import annotations

import json
import time
from pathlib import Path

import pandas as pd
import streamlit as st
from dotenv import load_dotenv

from .health import check_backends
from .llm import apply_overrides, load_config
from .pipeline.models import fmt_ts
from .pipeline.runner import run_pipeline
from .selftest import run_selftest

ROOT = Path(__file__).resolve().parents[2]
OUTPUTS = ROOT / "outputs"
PROVIDERS = ["anthropic", "openai", "gemini", "groq", "ollama", "freellm"]


def _cfg() -> dict:
    load_dotenv(ROOT / ".env")
    return load_config(ROOT / "configs" / "config.yaml")


@st.cache_data(ttl=60, show_spinner="Checking backends...")
def _backends() -> list[dict]:
    return check_backends(_cfg())


def list_runs() -> list[Path]:
    if not OUTPUTS.exists():
        return []
    runs = [d for d in OUTPUTS.iterdir() if d.is_dir() and (d / "promos_ranked.json").exists()]
    return sorted(runs, key=lambda d: d.stat().st_mtime, reverse=True)


def _segments(p: dict) -> str:
    return "; ".join(f"Ep {s['episode']} {fmt_ts(s['start'])}-{fmt_ts(s['end'])}" for s in p["segments"])


# ---------------------------------------------------------------- Status
def tab_status() -> None:
    st.subheader("1. Does the code run?")
    st.caption("Offline test on a made-up episode with a stub model: no network, no key, no screenplay data.")
    if st.button("Run self-test", type="primary"):
        steps = run_selftest()
        for s in steps:
            (st.success if s["ok"] else st.error)(f"{s['step']}: {s['detail']}")
        if all(s["ok"] for s in steps) and len(steps) == 4:
            st.success("Pipeline code is working.")

    st.subheader("2. Can it reach the models?")
    if st.button("Re-check"):
        _backends.clear()
    rows = _backends()
    df = pd.DataFrame(rows)
    df["status"] = [("OK" if r["reachable"] else "key set" if r["key_set"] and r["reachable"] is None
                     else "DOWN") for r in rows]
    st.dataframe(df[["stage", "provider", "model", "status", "detail"]], hide_index=True, width="stretch")
    if not any(r["reachable"] or (r["key_set"] and r["reachable"] is None) for r in rows):
        st.warning("No model is reachable, so a real run will fail. Start the router / tunnel, or pick a hosted "
                   "model with its key in `.env` on the Run tab.")


# ---------------------------------------------------------------- Run
def tab_run() -> None:
    cfg = _cfg()
    src = st.radio("Screenplays", ["Upload .txt files", "Folder on this machine"], horizontal=True)
    files, folder = None, ""
    if src.startswith("Upload"):
        files = st.file_uploader("One .txt per episode", type="txt", accept_multiple_files=True)
    else:
        found = sorted(p for p in (ROOT / "data" / "raw").glob("*") if p.is_dir()) if (ROOT / "data" / "raw").exists() else []
        folder = st.text_input("Folder", str(found[0]) if found else "")

    c1, c2 = st.columns(2)
    episodes = c1.text_input("Episodes (optional)", placeholder="1-5,12")
    do_judge = c2.checkbox("Run the cold-viewer judge", True)
    do_baseline = c2.checkbox("Run the rules-only baseline", True)

    with st.expander("Model (default: configs/config.yaml)"):
        override = st.checkbox("Use one model for every stage")
        provider = st.selectbox("Provider", PROVIDERS, disabled=not override)
        model = st.text_input("Model id", disabled=not override)
        j_over = st.checkbox("Use a different model for the judge only")
        jprov = st.selectbox("Judge provider", PROVIDERS, disabled=not j_over)
        jmodel = st.text_input("Judge model id", disabled=not j_over)

    if not st.button("Run", type="primary"):
        return
    if override and not model:
        st.error("Enter a model id.")
        return
    run_name = f"run-{time.strftime('%Y%m%d-%H%M%S')}"
    out = OUTPUTS / run_name
    if files:
        scripts = out / "input"
        scripts.mkdir(parents=True, exist_ok=True)
        for f in files:
            (scripts / Path(f.name).name).write_bytes(f.getvalue())
    elif folder and Path(folder).is_dir():
        scripts = Path(folder)
    else:
        st.error("Upload screenplays or give a folder that exists.")
        return

    cfg = apply_overrides(cfg, provider if override else None, model if override else None,
                          jprov if j_over else None, jmodel if j_over else None)
    bar, log, lines = st.progress(0.0), st.empty(), []

    def progress(stage: str, i: int, n: int, msg: str) -> None:
        bar.progress(min(1.0, i / max(n, 1)), text=f"{stage} {i}/{n}")
        lines.append(f"[{stage} {i}/{n}] {msg}")
        log.code("\n".join(lines[-12:]))

    try:
        res = run_pipeline(scripts, out, cfg, episodes=episodes or None, do_judge=do_judge,
                           do_baseline=do_baseline, progress=progress, cache_dir=ROOT / ".cache" / "llm")
    except Exception as e:
        st.error(f"Run failed: {type(e).__name__}: {e}")
        return
    st.session_state["selected_run"] = run_name
    if res["meta"]["errors"]:
        st.warning(f"Finished with {len(res['meta']['errors'])} error(s); see the report.")
    else:
        st.success(f"Done. Open the Results tab ({run_name}).")


# ---------------------------------------------------------------- Results
def tab_results() -> None:
    runs = list_runs()
    if not runs:
        st.info("No runs yet. Use the Run tab.")
        return
    names = [d.name for d in runs]
    default = names.index(st.session_state["selected_run"]) if st.session_state.get("selected_run") in names else 0
    run = OUTPUTS / st.selectbox("Run", names, index=default)
    rows = json.loads((run / "promos_ranked.json").read_text(encoding="utf-8"))
    meta = json.loads((run / "run_meta.json").read_text(encoding="utf-8")) if (run / "run_meta.json").exists() else {}
    top = [r for r in rows if r.get("in_top_list")]

    m = st.columns(4)
    m[0].metric("Valid promos", len(rows))
    m[1].metric("Episodes", len(meta.get("episodes", [])))
    m[2].metric("Finder", (meta.get("finder_chain") or [{}])[0].get("model", "-"))
    m[3].metric("Judge", (meta.get("judge_chain") or [{}])[0].get("model", "-"))
    if meta.get("errors"):
        st.warning(f"{len(meta['errors'])} error(s) in this run.")

    st.subheader("Post these first")
    st.dataframe(pd.DataFrame([{
        "#": r["rank"], "Promo": r["promo_id"], "Segments": _segments(r), "Length (s)": round(r["duration_s"]),
        "Hook": r["hook"], "Cliffhanger": r["cliffhanger"],
        "H/C/Cl": "/".join(str((r.get("judge") or {}).get(k, "-")) for k in ("hook", "cliffhanger", "clarity")),
        "Score": (r.get("scores") or {}).get("final"),
    } for r in top]), hide_index=True, width="stretch")

    st.subheader("Promo detail")
    pick = st.selectbox("Promo", [f"#{r['rank']} {r['promo_id']}" for r in rows])
    r = rows[int(pick.split()[0][1:]) - 1]
    st.markdown(f"**Segments:** {_segments(r)} ({r['duration_s']:.0f} s)  \n**Hook:** {r['hook']}  \n"
                f"**Cliffhanger:** {r['cliffhanger']}  \n**Why it works:** {r['why']}")
    j = r.get("judge") or {}
    if j:
        st.markdown(f"**Cold viewer saw:** {j.get('summary', '')}  \n**Confusing:** {j.get('confusing', '')}  \n"
                    f"**Wants next:** {j.get('want_next', '')}")
    if r.get("notes"):
        st.caption("Automatic fixes: " + " | ".join(r["notes"]))

    with st.expander("Full report"):
        rep = run / "report.md"
        st.markdown(rep.read_text(encoding="utf-8") if rep.exists() else "No report.", unsafe_allow_html=False)
    d = st.columns(3)
    for col, name in zip(d, ["promos_ranked.csv", "promos_ranked.json", "report.md"]):
        if (run / name).exists():
            col.download_button(f"Download {name}", (run / name).read_bytes(), file_name=name)


def main() -> None:
    st.set_page_config(page_title="KuKuAds", layout="wide")
    st.title("KuKuAds")
    st.caption("Finds 20-60 s promos in microdrama screenplays: a hook in the first 3 s, a cliffhanger at the end, "
               "clear to someone who has never seen the show.")
    status, run, results = st.tabs(["Status", "Run", "Results"])
    with status:
        tab_status()
    with run:
        tab_run()
    with results:
        tab_results()
