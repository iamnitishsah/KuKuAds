"""Evaluation: the measured results, as tiles and bars. Numbers are from docs/findings.md (the archived 50-episode run)."""
import pandas as pd
import streamlit as st

from .. import theme
from ..state import ROOT

BASELINE = [("Cliffhanger", 20, 7, "+0.27", "p = 0.019"), ("Hook", 17, 8, "+0.11", "p = 0.108"),
            ("Clarity", 17, 10, "+0.10", "p = 0.248"), ("Overall", 31, 18, "", "p = 0.085")]
LLM2 = pd.DataFrame({"Dimension": ["Hook", "Cliffhanger", "Clarity", "Composite"], "Qwen mean": [4.08, 4.08, 3.96, 4.04],
                     "LLM-2 mean": [3.48, 3.23, 3.75, 3.49], "Spearman": [0.73, 0.80, 0.54, 0.73]})
RERUN = [("Cliffhanger", 25, 7, "+0.41", "p = 0.002"), ("Hook", 9, 9, "0.00", "p = 1.0"),
         ("Clarity", 19, 13, "+0.06", "p = 0.377"), ("Overall", 30, 20, "", "p = 0.203")]
STRATA = [("Top", 8, 94), ("Mid", 6, 75), ("Bottom", 6, 25), ("Baseline", 4, 75)]


def render() -> None:
    st.caption("Measured on the archived 50-episode run, then re-run after the fixes. Written up in docs/findings.md, not recomputed live.")
    cols = st.columns(4)
    for col, (v, l, s) in zip(cols, [("78 / 78", "within 20–60 s", "and hook inside 3 s"), ("0", "invented quotes", "checked against the script"),
                                      ("31 vs 18", "episodes won vs baseline", "p = 0.085, not proven overall"),
                                      ("0", "human ratings so far", "the biggest open gap")]):
        col.markdown(theme.stat(v, l, s), unsafe_allow_html=True)

    st.markdown("##### Does the AI beat a rules-only baseline?")
    st.caption("Best promo per episode from each method (49 episodes), scored by the same judge.")
    theme.show('<div class="legend"><i style="background:#7C3AED"></i>AI better<i style="background:#6B7280"></i>baseline better</div>')
    for name, a, b, diff, p in BASELINE:
        theme.show(f'<div class="row"><span class="n">{name}</span>{theme.split_bar(a, b)}<span class="e">{(diff + " · ") if diff else ""}{p}</span></div>')
    st.info("The AI is clearly better at choosing **where to cut** (the cliffhanger). On hook and clarity the baseline is close, "
            "and the differences are not statistically proven.")

    st.markdown("##### Re-run with the fixed validator (all 50 episodes)")
    st.caption("A new end-to-end run after the validator and judge fixes. Same method, 50 episodes compared.")
    cols = st.columns(4)
    for col, (v, l, s) in zip(cols, [("50 / 50", "episodes covered", "Ep 33 and Ep 42 both found (archived: 49)"), ("72 / 72", "within 20–60 s", "14 clips repaired instead of rejected"),
                                      ("0 of 154", "edges inside a spoken line", "archived run: 2"), ("2 / 5", "top-5 overlap with archived", "same model, different shortlist")]):
        col.markdown(theme.stat(v, l, s), unsafe_allow_html=True)
    st.write("")
    for name, a, b, diff, p in RERUN:
        theme.show(f'<div class="row"><span class="n">{name}</span>{theme.split_bar(a, b)}<span class="e">{(diff + " · ") if diff else ""}{p}</span></div>')
    st.dataframe(pd.DataFrame({"Judge reliability (two passes per clip)": ["Identical score per dimension", "Within 1 point", "All three identical", "Rank correlation", "Top-15 overlap"],
                               "Archived": ["79%", "99%", "51.6%", "0.90", "11/15"], "Re-run": ["77%", "100%", "48.6%", "0.80", "11/15"]}),
                 hide_index=True, width="stretch")
    st.caption("The cliffhanger gain holds and is stronger. Hook and clarity are still not clearly better than the baseline. "
               "The ranking changes between runs of the same model, so it is a shortlist.")

    st.markdown("##### Does a second model agree?")
    st.caption("24 anonymised clips rated twice by a different model family (LLM-2). It scores lower across the board but keeps the order.")
    c = st.columns([3, 2], gap="large")
    with c[0]:
        theme.show('<div class="legend">would-post rate, by stratum (LLM-2)</div>')
        for name, n, pct in STRATA:
            theme.show(f'<div class="row"><span class="n">{name} (n={n})</span>{theme.meter(pct, 100, "#16A34A" if pct >= 70 else "#DC2626")}<span class="e">{pct}%</span></div>')
        st.caption("Top > mid > bottom survives a model swap, and the bottom group falls to 25%. That is the strongest sign the ranking is not noise.")
    with c[1]:
        st.dataframe(LLM2.style.format({"Qwen mean": "{:.2f}", "LLM-2 mean": "{:.2f}", "Spearman": "{:.2f}"}), hide_index=True, width="stretch")
        st.caption("Qwen, our judge, is lenient by about +0.56 composite (+0.85 on cliffhanger).")

    st.markdown("##### Where it is weak")
    w = st.columns(3)
    w[0].markdown(theme.card("The ranking is a shortlist", ["changing the finder model changes 7 of the top 15", "re-running the same model changes 9 of 15",
                                                            "top-10 overlap with LLM-2 is 6/10"]), unsafe_allow_html=True)
    w[1].markdown(theme.card("The judge is lenient", ["72–77% of averaged scores are 4 or 5", "its two passes are identical on all three scores for only about half the clips",
                                                      "cliffhanger is the least reliable dimension"]), unsafe_allow_html=True)
    w[2].markdown(theme.card("Not yet checked", ["no human has rated a clip", "no brand-safety check", "text only: no video or audio"]),
                  unsafe_allow_html=True)

    f = ROOT / "docs" / "findings.md"
    if f.exists():
        with st.expander("Full write-up (docs/findings.md)"):
            st.markdown(f.read_text(encoding="utf-8").split("\n", 1)[1])
