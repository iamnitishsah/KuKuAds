import json
from pathlib import Path

ROOT = Path(r"C:\Users\kunal\nitish\promo-finder")
OUT = ROOT / "outputs" / "eval-llm2"
TEMP = Path(r"C:\Users\kunal\AppData\Local\Temp\opencode\llm2")
DIMS = ("hook", "cliffhanger", "clarity")

key = {r["clip_id"]: r for r in json.load(open(OUT / "key.json", encoding="utf-8"))}
p1 = {r["clip_id"]: r for r in json.load(open(TEMP / "pass1" / "scores.json", encoding="utf-8"))["scores"]}
p2 = {r["clip_id"]: r for r in json.load(open(TEMP / "pass2" / "scores.json", encoding="utf-8"))["scores"]}
packet = {r["clip_id"]: r for r in json.load(open(OUT / "packet.json", encoding="utf-8"))}

rows = []
for cid in sorted(key):
    k = key[cid]
    a, b = p1[cid], p2[cid]
    avg = {d: (a[d] + b[d]) / 2 for d in DIMS}
    qc = sum(k["qwen"][d] for d in DIMS) / 3
    lc = sum(avg[d] for d in DIMS) / 3
    rows.append(dict(cid=cid, promo=k["promo_id"], stratum=k["stratum"], rank=k["rank"],
                     q=k["qwen"], qc=qc, a=a, b=b, avg=avg, lc=lc, delta=lc - qc))

def triple(d):
    return f"{d['hook']:g}/{d['cliffhanger']:g}/{d['clarity']:g}"

lines = []
lines.append("### A. Qwen vs LLM-2 averages\n")
lines.append("| Clip | Promo | Stratum | Rank* | Qwen H/C/Cl | Qwen comp | LLM-2 avg H/C/Cl | LLM-2 comp | Delta |")
lines.append("|---|---|---|---|---|---|---|---|---|")
for r in rows:
    lines.append(f"| {r['cid']} | {r['promo']} | {r['stratum']} | {r['rank']} | {triple(r['q'])} | "
                 f"{r['qc']:.2f} | {triple(r['avg'])} | {r['lc']:.2f} | {r['delta']:+.2f} |")

lines.append("\n### B. The two LLM-2 passes and binary labels\n")
lines.append("| Clip | Promo | Pass 1 H/C/Cl | Pass 2 H/C/Cl | Post P1 | Post P2 | Safety P1 | Safety P2 |")
lines.append("|---|---|---|---|---|---|---|---|")
for r in rows:
    lines.append(f"| {r['cid']} | {r['promo']} | {triple(r['a'])} | {triple(r['b'])} | "
                 f"{'yes' if r['a'].get('would_post') else 'no'} | {'yes' if r['b'].get('would_post') else 'no'} | "
                 f"{r['a'].get('safety','')} | {r['b'].get('safety','')} |")

lines.append("\n### C. Stratum summary\n")
lines.append("| Stratum | n | Qwen comp | LLM-2 comp | LLM-2 would-post | Qwen would-watch-next |")
lines.append("|---|---|---|---|---|---|")
for s in ("top", "mid", "bottom", "baseline"):
    sub = [r for r in rows if r["stratum"] == s]
    post = sum(1.0 if (r["a"].get("would_post") and r["b"].get("would_post")) else
               0.5 if (r["a"].get("would_post") or r["b"].get("would_post")) else 0.0 for r in sub) / len(sub)
    ww = sum(1 for r in sub if key[r["cid"]]["qwen"]["would_watch_next_episode"]) / len(sub)
    lines.append(f"| {s} | {len(sub)} | {sum(r['qc'] for r in sub)/len(sub):.2f} | "
                 f"{sum(r['lc'] for r in sub)/len(sub):.2f} | {post:.0%} | {ww:.0%} |")

lines.append("\n### D. Top 10 by each judge (within the 24 clips)\n")
qtop = [r["cid"] for r in sorted(rows, key=lambda r: (-r["qc"], r["cid"]))[:10]]
ltop = [r["cid"] for r in sorted(rows, key=lambda r: (-r["lc"], r["cid"]))[:10]]
lines.append("Qwen: " + ", ".join(f"{c} ({key[c]['promo_id']})" for c in qtop))
lines.append("\nLLM-2: " + ", ".join(f"{c} ({key[c]['promo_id']})" for c in ltop))
lines.append(f"\nOverlap: {len(set(qtop) & set(ltop))}/10")

lines.append("\n### E. Biggest composite disagreements\n")
lines.append("| Clip | Promo | Stratum | Qwen | LLM-2 | Delta |")
lines.append("|---|---|---|---|---|---|")
for r in sorted(rows, key=lambda r: -abs(r["delta"]))[:8]:
    lines.append(f"| {r['cid']} | {r['promo']} | {r['stratum']} | {r['qc']:.2f} | {r['lc']:.2f} | {r['delta']:+.2f} |")

lines.append("\n### F. Example transcripts\n")
for cid in ("C01", "C04"):
    lines.append(f"\n**{cid} - {key[cid]['promo_id']} ({packet[cid]['duration_s']} s)**\n")
    lines.append("```")
    lines.append(packet[cid]["transcript"])
    lines.append("```")

(OUT / "llm2_tables.md").write_text("\n".join(lines), encoding="utf-8")
print("\n".join(lines))
