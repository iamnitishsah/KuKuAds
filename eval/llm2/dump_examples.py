import json
from pathlib import Path
import sys

ROOT = Path(r"C:\Users\kunal\nitish\promo-finder")
SCRIPTS = Path(r"C:\Users\kunal\nitish\I Married a Broken Soldier. He was a Duke-scripts (2) (1)")
sys.path.insert(0, str(ROOT))

from promofinder.pipeline.find import build_finder_prompt, prompt_beats
from promofinder.pipeline.judge import clip_transcript
from promofinder.pipeline.models import Promo, Segment
from promofinder.pipeline.parse import load_show
from promofinder.pipeline.prompts import FINDER_SYSTEM, JUDGE_SYSTEM, JUDGE_USER

beats = json.loads((ROOT / "outputs/full-run/beats.json").read_text(encoding="utf-8"))
cands = json.loads((ROOT / "outputs/full-run/candidates.json").read_text(encoding="utf-8"))
ranked = json.loads((ROOT / "outputs/full-run/promos_ranked.json").read_text(encoding="utf-8"))
base = json.loads((ROOT / "outputs/full-run/baseline.json").read_text(encoding="utf-8"))
show = load_show(SCRIPTS)
by_num = {e.number: e for e in show}

def beat_dict(bid):
    for ep in beats:
        for b in ep["beats"]:
            if b["id"] == bid:
                return b
    return None

print("=" * 30, "BEATS E01-B004..B012")
for i in range(4, 13):
    print(json.dumps(beat_dict(f"E01-B{i:03d}"), ensure_ascii=False))

print("=" * 30, "RAW SCRIPT EP1 (first 45 lines)")
raw = (SCRIPTS / "episode-001-Episode 1671703.txt").read_text(encoding="utf-8").splitlines()
print("\n".join(raw[:45]))

print("=" * 30, "FINDER PROMPT E01")
system, user = build_finder_prompt(show[0], show, 3)
print("SYSTEM chars", len(system))
print(system)
print("USER chars", len(user), "beats in prompt", len(prompt_beats(show[0])))
print("\n".join(user.splitlines()[:28]))
print("... [truncated in dump] ...")
print("\n".join(user.splitlines()[-8:]))

print("=" * 30, "RAW FINDER OUTPUTS E01")
for c in cands:
    if c["promo_id"].startswith("E01-"):
        print(json.dumps(c, ensure_ascii=False, indent=1))

print("=" * 30, "VALIDATED E01-P1")
for r in ranked:
    if r["promo_id"] == "E01-P1":
        print(json.dumps(r, ensure_ascii=False, indent=1))

print("=" * 30, "E42-P1 REJECTED")
for c in cands:
    if c["promo_id"] == "E42-P1":
        print(json.dumps(c, ensure_ascii=False, indent=1))

print("=" * 30, "FIX EXAMPLES")
for c in cands:
    if c.get("notes"):
        print(c["promo_id"], c["status"], c["notes"])

print("=" * 30, "BASELINE E01-B1")
for b in base:
    if b["promo_id"] == "E01-B1":
        print(json.dumps(b, ensure_ascii=False, indent=1))

print("=" * 30, "JUDGE TRANSCRIPT E01-P1")
row = next(r for r in ranked if r["promo_id"] == "E01-P1")
p = Promo("E01-P1", "llm", [Segment(s["episode"], s["start"], s["end"], s["start_beat"], s["end_beat"]) for s in row["segments"]])
tr = clip_transcript(p, by_num)
print("duration", p.duration)
print(tr)
print("=" * 30, "JUDGE USER PROMPT")
print(JUDGE_USER.format(duration=p.duration, clip=tr))
print("=" * 30, "JUDGE SYSTEM")
print(JUDGE_SYSTEM)

print("=" * 30, "RANK MATH E01-P1")
print(json.dumps(row["scores"], indent=1), "intensity", row["intensity"], "judge", json.dumps(row["judge"], indent=1))

print("=" * 30, "TOP 15")
for r in ranked[:15]:
    print(r["rank"], r["promo_id"], r["episodes"], r["duration_s"], r["judge"]["hook"], r["judge"]["cliffhanger"], r["judge"]["clarity"], r["scores"]["final"], r["in_top_list"])

print("=" * 30, "COUNTS")
print("beats", sum(len(e["beats"]) for e in beats), "episodes", len(beats), "scenes", len({(e["number"], b["scene"]) for e in beats for b in e["beats"]}))
print("candidates", len(cands), "valid", sum(c["status"] == "valid" for c in cands), "rejected", sum(c["status"] == "rejected" for c in cands))
print("ranked", len(ranked), "top", sum(r["in_top_list"] for r in ranked), "episodes covered", len({r["episodes"][0] for r in ranked}))
print("baseline", len(base))
