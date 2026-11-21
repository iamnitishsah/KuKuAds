"""Settings modal: model choice, your own API key (memory only), what to run, test connection."""
from __future__ import annotations

import os

import streamlit as st

from ..health import ping
from . import state


@st.dialog("Settings", width="large")
def settings_dialog() -> None:
    s, cfg = state.settings(), state.base_cfg()
    providers = list(cfg["providers"])

    def label(p: str) -> str:
        env = cfg["providers"][p].get("api_key_env")
        have = bool(os.getenv(env or "")) or (bool(s["api_key"]) and p == state.key_provider(state.effective_cfg()))
        return p if have or not env else f"{p} (needs a key)"

    st.markdown("**Models**")
    s["override"] = st.toggle("Use one model for every stage", s["override"],
                              help="Otherwise the models in configs/config.yaml are used.")
    if s["override"]:
        c1, c2 = st.columns(2)
        s["provider"] = c1.selectbox("Provider", providers, index=providers.index(s["provider"]), format_func=label)
        s["model"] = c2.text_input("Model id", s["model"], placeholder="e.g. claude-sonnet-5-5")
    s["judge_override"] = st.toggle("Use a different model for the judge", s["judge_override"],
                                    help="The judge should not be the finder's model, or it grades its own picks.")
    if s["judge_override"]:
        c1, c2 = st.columns(2)
        s["jprovider"] = c1.selectbox("Judge provider", providers, index=providers.index(s["jprovider"]), format_func=label)
        s["jmodel"] = c2.text_input("Judge model id", s["jmodel"])
    st.caption(state.model_summary(state.effective_cfg()))

    st.markdown("**Your API key**")
    cfg_now = state.effective_cfg()
    s["api_key"] = st.text_input(f"Key for `{state.key_provider(cfg_now)}` (optional)", s["api_key"], type="password",
                                 help="Kept in this session's memory only. Never written to disk, forgotten on reload.")

    st.markdown("**What to run**")
    c1, c2 = st.columns(2)
    s["judge"] = c1.checkbox("Cold-viewer judge", s["judge"])
    s["baseline"] = c2.checkbox("Rules-only baseline", s["baseline"])

    if st.button("Test connection"):
        for stage in ("finder", "judge"):
            entry = cfg_now["stages"][stage][0]
            with state.session_key(cfg_now):
                ok, detail = ping(entry, cfg_now)
            (st.success if ok else st.error)(f"{stage}: `{entry['provider']}/{entry['model']}`: {detail}")
    if st.button("Done", type="primary"):
        st.rerun()
