import streamlit as st

from ..state import ROOT


def render() -> None:
    f = ROOT / "docs" / "findings.md"
    if not f.exists():
        st.info("docs/findings.md not found.")
        return
    st.caption("Measured on the archived 50-episode run, written up in docs/findings.md. Not recomputed live.")
    text = f.read_text(encoding="utf-8").split("\n", 1)[1]      # drop the file's own title
    st.markdown(text)
