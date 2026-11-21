import streamlit as st

DOT = """digraph G { rankdir=LR; node [shape=box, style="rounded,filled", fontname="Helvetica"];
  parse [label="1 Parse\\n(code)", fillcolor="#dbeafe"]; find [label="2 Find\\n(AI)", fillcolor="#fde68a"];
  validate [label="3 Validate\\n(code)", fillcolor="#dbeafe"]; judge [label="4 Judge\\n(a different AI)", fillcolor="#fde68a"];
  rank [label="5 Rank\\n(code)", fillcolor="#dbeafe"]; base [label="Baseline\\n(rules only)", fillcolor="#e5e7eb"];
  parse -> find -> validate -> judge -> rank; parse -> base -> judge; }"""


def render() -> None:
    st.graphviz_chart(DOT)
    st.caption("Blue = code, yellow = AI, grey = the rules-only control.")
    steps = [
        ("1 · Parse (code)", "Splits each screenplay into **beats**: one timed line of dialogue, action, shot or sound, with an ID like "
                             "`E01-B008`, the speaker, tone tags, and cheap signals (intensity, physical action, cliffhanger cues)."),
        ("2 · Find (AI, one call per episode)", "Reads the beats and proposes promos as **beat IDs only**. It never writes a timestamp."),
        ("3 · Validate (code)", "Turns IDs into timestamps and enforces 20–60 s, hook within 3 s, ending on the cliffhanger, never cutting a "
                               "spoken line, snapping to shot edges. Every fix or rejection is logged."),
        ("4 · Judge (a different AI)", "Sees **only the clip transcript**, like a stranger scrolling, and scores hook, cliffhanger and clarity from 1 to 5, "
                                       "twice, averaged. It is never the finder's model, so it does not grade its own picks."),
        ("5 · Rank (code)", "0.3 hook + 0.3 cliffhanger + 0.3 clarity + 0.1 intensity (+0.05 for episodes 1–5); at most one promo per episode in the top 15."),
    ]
    for title, body in steps:
        with st.expander(title):
            st.write(body)
    st.subheader("How invented timestamps are stopped")
    st.write("The AI answers with beat IDs that exist in the screenplay. Code looks each ID up and computes the times, so a promo "
             "can only start and end where the script says something happens. IDs that do not exist are rejected.")
    st.subheader("Data and keys")
    st.write("Screenplays stay on this machine (`data/raw/`, gitignored). Uploaded files are saved under `outputs/run-…/input/`. "
             "Model replies are cached in `.cache/llm`, so re-running is free. Your API key from **Settings** lives only in this "
             "session's memory: never written to disk, forgotten on reload. Every model call is logged with the model that "
             "actually answered (`llm_calls.jsonl`).")
