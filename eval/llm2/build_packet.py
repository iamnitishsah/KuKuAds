"""Build a blinded LLM-2 evaluation packet from the full run.

- 8 clips from ranks 1-15, 6 from 16-50, 6 from 51-78, 4 baseline B1.
- One clip per episode (cold-viewer independence).
- Only clip_id, duration and transcript are exposed. No rank, score, source,
  hook/cliffhanger text, promo id, finder model or judge fields.
- The transcript is built with pipeline.judge.clip_transcript, i.e. exactly the
  text the Qwen judge saw.

Key file (mapping + Qwen scores) stays in outputs/eval-llm2 and is NOT copied to
the scorer's directory.
"""
from __future__ import annotations

import json
import random
import shutil
import sys
from pathlib import Path

ROOT = Path(r"C:\Users\kunal\nitish\promo-finder")
SCRIPTS = Path(r"C:\Users\kunal\nitish\I Married a Broken Soldier. He was a Duke-scripts (2) (1)")
OUT = ROOT / "outputs" / "eval-llm2"
TEMP = Path(r"C:\Users\kunal\AppData\Local\Temp\opencode\llm2")
sys.path.insert(0, str(ROOT))

from promofinder.pipeline.judge import clip_transcript  # noqa: E402
from promofinder.pipeline.models import Promo, Segment  # noqa: E402
from promofinder.pipeline.parse import load_show  # noqa: E402

RUBRIC = """You are a typical US viewer scrolling TikTok. You have NEVER seen this show and know nothing
about it. You will read the transcript of one short video clip: dialogue and visible action, in order, with
seconds from the clip start. Speaker labels are how the characters would look on screen to you.

Judge each clip honestly and use the whole scale (1-5; half points allowed).
- hook (1-5): do the first 3 seconds make you stop scrolling?
  5 = shocking line/action instantly; 3 = mildly intriguing; 1 = nothing happens, you scroll on.
- cliffhanger (1-5): does it cut at a moment that leaves you needing to know what happens next?
  5 = cut mid-crisis, you must know what happens; 3 = some open question; 1 = resolved or just fizzles out.
- clarity (1-5): with zero background, can you follow it? You do NOT need names or full backstory - promos
  rarely give that. Judge whether the core situation and stakes are clear.
  5 = instantly obvious who is the victim, who is the villain and what is at stake;
  3 = you get the gist of the conflict but key relationships or stakes are fuzzy;
  1 = you cannot tell what is going on or why it matters.
- would_post (true/false): if you ran the show's account, would you post this clip as an ad?
- safety (safe | caution | unsafe): would Instagram/TikTok likely restrict it for violence, gore,
  sexual content or other brand-safety reasons?

Do not use outside knowledge. Judge ONLY the transcript in front of you. Do not reward a clip for being
from a later episode; you do not know the episode number.

Return ONLY valid JSON:
{"scores": [
  {"clip_id": "C01",
   "hook": 1, "cliffhanger": 1, "clarity": 1,
   "would_post": true,
   "safety": "safe",
   "summary": "<one sentence: what is happening>",
   "confusing": "<what is unclear, or 'nothing'>",
   "want_next": "<the question you are left with, or 'nothing'>",
   "would_watch_next_episode": true}
]}
"""


def as_promo(row: dict) -> Promo:
    segs = [
        Segment(
            episode=s["episode"],
            start=float(s["start"]),
            end=float(s["end"]),
            start_beat=s.get("start_beat", ""),
            end_beat=s.get("end_beat", ""),
        )
        for s in row["segments"]
    ]
    return Promo(promo_id=row["promo_id"], source=row.get("source", ""), segments=segs)


def pick(pool: list[dict], n: int, used: set[int], rng: random.Random) -> list[dict]:
    available = [r for r in pool if r["episodes"][0] not in used]
    rng.shuffle(available)
    chosen = available[:n]
    if len(chosen) < n:  # fall back to repeats only if episodes run out
        rest = [r for r in pool if r not in chosen]
        rng.shuffle(rest)
        chosen += rest[: n - len(chosen)]
    used.update(r["episodes"][0] for r in chosen)
    return chosen


def main() -> None:
    show = load_show(SCRIPTS)
    by_num = {e.number: e for e in show}
    llm = json.loads((ROOT / "outputs/full-run/promos_ranked.json").read_text(encoding="utf-8"))
    baseline = json.loads((ROOT / "outputs/full-run/baseline.json").read_text(encoding="utf-8"))

    rng = random.Random(42)
    used: set[int] = set()
    top = pick([r for r in llm if r["rank"] <= 15], 8, used, rng)
    mid = pick([r for r in llm if 16 <= r["rank"] <= 50], 6, used, rng)
    bottom = pick([r for r in llm if r["rank"] >= 51], 6, used, rng)
    base = pick(baseline, 4, used, rng)
    sample = (
        [("top", r) for r in top]
        + [("mid", r) for r in mid]
        + [("bottom", r) for r in bottom]
        + [("baseline", r) for r in base]
    )
    rng.shuffle(sample)

    packet, key = [], []
    for i, (stratum, row) in enumerate(sample, 1):
        cid = f"C{i:02d}"
        packet.append(
            {
                "clip_id": cid,
                "duration_s": row["duration_s"],
                "transcript": clip_transcript(as_promo(row), by_num),
            }
        )
        key.append(
            {
                "clip_id": cid,
                "promo_id": row["promo_id"],
                "source": row.get("source"),
                "stratum": stratum,
                "rank": row.get("rank"),
                "episodes": row.get("episodes"),
                "qwen": {
                    "hook": row["judge"].get("hook"),
                    "cliffhanger": row["judge"].get("cliffhanger"),
                    "clarity": row["judge"].get("clarity"),
                    "would_watch_next_episode": row["judge"].get("would_watch_next_episode"),
                },
                "qwen_final": (row.get("scores") or {}).get("final"),
            }
        )

    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "packet.json").write_text(json.dumps(packet, ensure_ascii=False, indent=1), encoding="utf-8")
    (OUT / "key.json").write_text(json.dumps(key, ensure_ascii=False, indent=1), encoding="utf-8")
    (OUT / "rubric.md").write_text(RUBRIC, encoding="utf-8")

    for name in ("pass1", "pass2"):
        d = TEMP / name
        d.mkdir(parents=True, exist_ok=True)
        shutil.copy2(OUT / "packet.json", d / "packet.json")
        shutil.copy2(OUT / "rubric.md", d / "rubric.md")

    print(f"packet: {len(packet)} clips -> {OUT / 'packet.json'}")
    print("composition:", {s: sum(1 for x, _ in sample if x == s) for s in ("top", "mid", "bottom", "baseline")})
    print("distinct episodes:", len({r['episodes'][0] for _, r in sample}))
    print("scorer dirs:", TEMP / "pass1", TEMP / "pass2")


if __name__ == "__main__":
    main()
