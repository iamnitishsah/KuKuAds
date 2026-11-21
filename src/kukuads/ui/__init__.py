"""Streamlit app: five tabs (Overview, Find promos, How it works, Evaluation, Status) and a Settings dialog.

    streamlit run app.py
"""
from __future__ import annotations

import streamlit as st

from . import state
from .pages import evaluation, find, how_it_works, overview, status
from .settings import settings_dialog


def main() -> None:
    st.set_page_config(page_title="KuKuAds", layout="wide")
    head = st.columns([6, 1])
    head[0].title("KuKuAds")
    head[0].caption("Finds 20–60 s promos in microdrama screenplays: a hook in the first 3 s, a cliffhanger at the end, "
                    "clear to someone who has never seen the show.")
    if head[1].button("Settings", icon=":material/settings:"):
        settings_dialog()
    t_over, t_find, t_how, t_eval, t_status = st.tabs(["Overview", "Find promos", "How it works", "Evaluation", "Status"])
    with t_over:
        overview.render()
    with t_find:
        find.render()
    with t_how:
        how_it_works.render()
    with t_eval:
        evaluation.render()
    with t_status:
        status.render()
