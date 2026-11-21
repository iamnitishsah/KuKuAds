import json
from pathlib import Path

T = Path(r"C:\Users\kunal\AppData\Local\Temp\opencode\llm2")
k = {r["clip_id"]: r for r in json.load(open("outputs/eval-llm2/supplement_key.json", encoding="utf-8"))}
p1 = {r["clip_id"]: r for r in json.load(open(T / "supplement1" / "scores.json", encoding="utf-8"))["scores"]}
p2 = {r["clip_id"]: r for r in json.load(open(T / "supplement2" / "scores.json", encoding="utf-8"))["scores"]}
D = ("hook", "cliffhanger", "clarity")
rows = []
for c in sorted(k):
    q = k[c]["qwen"]
    a, b = p1[c], p2[c]
    l = {d: (a[d] + b[d]) / 2 for d in D}
    qc = sum(q[d] for d in D) / 3
    lc = sum(l[d] for d in D) / 3
    rows.append((c, k[c]["promo_id"], k[c]["rank"], q, l, qc, lc, lc - qc))

print("clip promo rank | Qwen H/C/Cl -> comp | LLM2 H/C/Cl -> comp | delta")
for c, p, r, q, l, qc, lc, d in sorted(rows, key=lambda x: x[2]):
    print(f"{c} {p} #{r} | {q['hook']}/{q['cliffhanger']}/{q['clarity']} -> {qc:.2f} | "
          f"{l['hook']:.2f}/{l['cliffhanger']:.2f}/{l['clarity']:.2f} -> {lc:.2f} | {d:+.2f}")

print("\norder by LLM2:", [x[1] for x in sorted(rows, key=lambda x: -x[6])])
print("order by Qwen (actual overall rank):", [x[1] for x in sorted(rows, key=lambda x: x[2])])
print("LLM2 mean:", round(sum(x[6] for x in rows) / len(rows), 3))
print("Qwen mean:", round(sum(x[5] for x in rows) / len(rows), 3))
