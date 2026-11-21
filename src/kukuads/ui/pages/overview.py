import streamlit as st

from .. import theme


def render() -> None:
    theme.show('<div class="hero"><h1>Find the 20–60 second promos hiding in a microdrama</h1>'
               '<p>An editor today watches every episode to pick promo moments by hand. KuKuAds reads the screenplays and proposes '
               'the best clips for TikTok, Instagram and YouTube Shorts: ranked, with exact timestamps, the hook, the cliffhanger '
               'and one line on why each works.</p>'
               '<span class="hc">Hook in the first 3 s</span><span class="hc">Ends on a cliffhanger</span>'
               '<span class="hc">Clear to a stranger</span></div>')
    st.markdown("##### Result on the 50-episode show (re-run with the fixed validator)")
    cols = st.columns(4)
    for col, (v, l, s) in zip(cols, [("72", "valid promos", "73 proposed, 1 rejected as a duplicate"),
                                      ("50 / 50", "episodes covered", "at least one promo each (archived run: 49)"),
                                      ("25 vs 7", "cliffhanger wins", "AI vs rules-only baseline, p = 0.002"),
                                      ("0 of 154", "cut edges inside a spoken line", "all promos 20–60 s, hook in 3 s")]):
        col.markdown(theme.stat(v, l, s), unsafe_allow_html=True)
    st.write("")
    c = st.columns(3)
    c[0].markdown(theme.card("A good promo", ["opens on a hook in the first 3 seconds", "ends on a cliffhanger",
                                               "makes sense to someone who has never seen the show"]), unsafe_allow_html=True)
    c[1].markdown(theme.card("How it gets there", ["code splits the script into timed beats", "an AI proposes promos as beat IDs",
                                                   "code turns them into timestamps and enforces the rules",
                                                   "a second AI reads each clip like a stranger and scores it", "code ranks them"]),
                  unsafe_allow_html=True)
    c[2].markdown(theme.card("What it will not do", ["edit video, add music or text", "watch the video: it works from the screenplay",
                                                     "post anything: an editor decides", "promise a promo will perform"]),
                  unsafe_allow_html=True)
    st.markdown("##### What we would post first")
    theme.show('<span class="pick first">E32-P1</span><span class="pick">E01-P1</span><span class="pick">E02-P1</span>'
               '<span class="pick">E45-P1</span><span class="pick">E15-P1</span>')
    st.caption("From the re-run. The shortlist changes between runs (top-5 overlap with the archived run is 2 of 5), so treat the "
               "ranking as a shortlist, not a verdict.")
    st.info("No key yet? Open **Live demo** and press **Try the demo**: a full result from a made-up episode, no key, no data.")
