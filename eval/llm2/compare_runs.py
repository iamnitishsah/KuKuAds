import json
from collections import Counter
from pathlib import Path

ROOT = Path(r"C:\Users\kunal\nitish\promo-finder")
a = json.loads((ROOT / "outputs/full-run/promos_ranked.json").read_text(encoding="utf-8"))
q = json.loads((ROOT / "outputs/full-run-qwen-both/promos_ranked.json").read_text(encoding="utf-8"))
qb = json.loads((ROOT / "outputs/full-run-qwen-both/baseline.json").read_text(encoding="utf-8"))
qa = json.loads((ROOT / "outputs/full-run-qwen-both/candidates.json").read_text(encoding="utf-8"))

for label, rows in (("archived (gpt-oss finder)", a), ("qwen-only", q)):
    print(label, "valid", len(rows), "episodes", len({r["episodes"][0] for r in rows}),
          "top", sum(r["in_top_list"] for r in rows),
          "missing", sorted(set(range(1, 51)) - {r["episodes"][0] for r in rows}))
    vals = [r["judge"][d] for r in rows for d in ("hook", "cliffhanger", "clarity")]
    print("  mean H/C/Cl", [round(sum(r["judge"][d] for r in rows) / len(rows), 2) for d in ("hook", "cliffhanger", "clarity")],
          "share>=4", round(sum(1 for v in vals if v >= 4) / len(vals), 3),
          "share>=4.5", round(sum(1 for v in vals if v >= 4.5) / len(vals), 3))

for k in (5, 10, 15):
    A = {r["promo_id"] for r in a[:k]}
    Q = {r["promo_id"] for r in q[:k]}
    print(f"top{k} overlap", len(A & Q), "shared", sorted(A & Q))
    print("  only archived", sorted(A - Q))
    print("  only qwen", sorted(Q - A))

print("\nqwen-only top 15:")
for r in q[:15]:
    print(r["rank"], r["promo_id"], r["segments"][0]["episode"], r["duration_s"],
          r["judge"]["hook"], r["judge"]["cliffhanger"], r["judge"]["clarity"], r["scores"]["final"])

print("\nqwen-only candidates:", len(qa), Counter(r["status"] for r in qa))
notes = Counter()
for r in qa:
    for n in r["notes"]:
        notes["too short" if "too short" in n else "too long" if "too long" in n else "start moved" if "start moved" in n else "duplicate" if "duplicate" in n else n] += 1
print("notes", notes, "total", sum(notes.values()))
print("rejected", [(r["promo_id"], r["notes"]) for r in qa if r["status"] == "rejected"])
print("baseline judged", len(qb))
print("self-graded", sum(1 for r in q if r.get("finder_model") and r["judge"].get("served_by") == "qwen3.8:27b"), "/", len(q))
