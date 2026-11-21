import pandas as pd
import streamlit as st

from ...health import check_backends
from ...selftest import run_selftest
from .. import state


@st.cache_data(ttl=60, show_spinner="Checking backends...")
def _backends() -> list[dict]:
    return check_backends(state.base_cfg())


def render() -> None:
    st.subheader("1. Does the code run?")
    st.caption("Offline test on a made-up episode with a stub model: no network, no key, no screenplay data.")
    if st.button("Run self-test", type="primary"):
        steps = run_selftest()
        for s in steps:
            (st.success if s["ok"] else st.error)(f"{s['step']}: {s['detail']}")
        if len(steps) == 4 and all(s["ok"] for s in steps):
            st.success("Pipeline code is working.")

    st.subheader("2. Can it reach the models?")
    if st.button("Re-check"):
        _backends.clear()
    rows = _backends()
    df = pd.DataFrame(rows)
    df["status"] = ["OK" if r["reachable"] else "key set" if r["key_set"] and r["reachable"] is None else "DOWN" for r in rows]
    st.dataframe(df[["stage", "provider", "model", "status", "detail"]], hide_index=True, width="stretch")
    if not any(r["reachable"] or (r["key_set"] and r["reachable"] is None) for r in rows):
        st.warning("No model is reachable, so a real run will fail. Add a key in `.env` or in Settings, or start your local model.")
    st.caption("To send a real request to the current models, use **Test connection** in Settings.")
