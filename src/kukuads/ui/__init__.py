"""Streamlit app: four tabs (Overview, Live demo, How it works, Evaluation) and a Settings dialog.

    streamlit run app.py
"""
from __future__ import annotations

import streamlit as st

from . import theme
from .pages import evaluation, how_it_works, live_demo, overview
from .settings import settings_dialog


def main() -> None:
    st.set_page_config(page_title="KuKuAds", page_icon=":material/movie:", layout="wide")
    theme.inject()
    head = st.columns([6, 1])
    head[0].markdown('<div class="brand"><b>KuKu<span>Ads</span></b><i>promo finder for microdramas</i></div>', unsafe_allow_html=True)
    if head[1].button("Settings", icon=":material/settings:", width="stretch"):
        settings_dialog()
    t_over, t_demo, t_how, t_eval = st.tabs(["Overview", "Live demo", "How it works", "Evaluation"])
    with t_over:
        overview.render()
    with t_demo:
        live_demo.render()
    with t_how:
        how_it_works.render()
    with t_eval:
        evaluation.render()
