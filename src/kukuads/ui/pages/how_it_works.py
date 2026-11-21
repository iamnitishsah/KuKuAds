import streamlit as st

from .. import theme

STEPS = [
    ("Parse", "code", "Splits each screenplay into timed beats with IDs like E01-B008, the speaker, tone and cheap signals."),
    ("Find", "AI", "Reads each episode and proposes promos as beat IDs only. It never writes a timestamp."),
    ("Validate", "code", "Turns IDs into times. Enforces 20–60 s, hook within 3 s, no cut mid-line. Repairs clips that miss the length."),
    ("Judge", "AI", "A different model reads only the clip, like a stranger, and scores hook, cliffhanger and clarity from 1 to 5, twice."),
    ("Rank", "code", "Weighted score, at most one promo per episode in the top 15."),
]


def render() -> None:
    st.markdown("##### Five stages: code does structure and timing, AI does judgment")
    cols = st.columns([4, 1, 4, 1, 4, 1, 4, 1, 4])
    for i, (title, owner, body) in enumerate(STEPS):
        cols[i * 2].markdown(theme.step(i + 1, title, owner, body), unsafe_allow_html=True)
        if i < len(STEPS) - 1:
            cols[i * 2 + 1].markdown('<div class="arrow">→</div>', unsafe_allow_html=True)
    st.caption("Alongside, a rules-only baseline attempts the same task and is scored by the same judge, as the control.")

    st.markdown("##### How the final score is built")
    theme.show(theme.formula([("hook", 0.3, "#7C3AED"), ("cliffhanger", 0.3, "#DB2777"), ("clarity", 0.3, "#0EA5E9"), ("intensity", 0.1, "#6B7280")]))
    st.caption("Plus 0.05 for episodes 1–5, where a new viewer is most likely to land.")

    st.markdown("##### Guardrails")
    c = st.columns(3)
    c[0].markdown(theme.card("No invented timestamps", ["the AI answers with beat IDs from the script", "code looks each ID up and computes the times",
                                                         "unknown IDs are rejected"]), unsafe_allow_html=True)
    c[1].markdown(theme.card("The judge is not the finder", ["a different model grades each clip", "the clip is shown without any context",
                                                             "every call logs which model actually answered"]), unsafe_allow_html=True)
    c[2].markdown(theme.card("Nothing fails silently", ["every automatic fix or rejection is logged", "a promo that cannot be judged is marked, not scored 0",
                                                        "re-running resumes from the cache"]), unsafe_allow_html=True)

    st.markdown("##### Data and keys")
    st.write("Screenplays stay on this machine (`data/raw/`, gitignored). Uploaded files are saved under `outputs/run-…/input/`. "
             "Model replies are cached in `.cache/llm`. Your API key from **Settings** lives only in this session's memory: "
             "never written to disk, forgotten on reload.")
