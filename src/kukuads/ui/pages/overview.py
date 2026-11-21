import streamlit as st


def render() -> None:
    st.subheader("What it helps with")
    st.write("An editor today watches every episode to pick promo moments by hand. KuKuAds reads the screenplays and "
             "proposes the best **20–60 second promos** for TikTok, Instagram and YouTube Shorts, ranked, each with the "
             "episode, start and end timestamps, the hook, the cliffhanger and one line on why it works.")
    c = st.columns(3)
    with c[0].container(border=True):
        st.markdown("**A good promo**")
        st.markdown("- opens on a **hook** in the first 3 seconds\n- ends on a **cliffhanger**\n"
                    "- **makes sense** to someone who has never seen the show")
    with c[1].container(border=True):
        st.markdown("**How**")
        st.markdown("- code splits the script into timed beats\n- an AI proposes promos as beat IDs\n"
                    "- code turns them into timestamps and enforces the rules\n- a second AI reads each clip like a stranger and scores it\n"
                    "- code ranks them")
    with c[2].container(border=True):
        st.markdown("**What it will not do**")
        st.markdown("- edit video, add music or text\n- watch the video: it works from the screenplay\n"
                    "- post anything: an editor decides\n- promise a promo will perform")
    st.info("Start in **Find promos**. No key yet? Press **Try the demo** there, or run the self-test in **Status**.")
