r"""Compare the blinded LLM-2 pass against the Qwen judge on the 24-clip packet.

Inputs (all under outputs/eval-llm2 unless noted):
  key.json                     map clip_id -> promo_id / stratum / Qwen scores
  C:\...\Temp\opencode\llm2\pass1\scores.json
  C:\...\Temp\opencode\llm2\pass2\scores.json

Outputs:
  comparison.md                human-readable tables
  comparison.json              machine-readable metrics
  per_clip.csv                 unblinded per-clip scores and deltas

No dependency on scipy: Spearman is computed with average-tie ranks.
"""
from __future__ import annotations

import csv
import json
import sys
from pathlib import Path
from statistics import mean

ROOT = Path(r"C:\Users\kunal\nitish\promo-finder")
OUT = ROOT / "outputs" / "eval-llm2"
TEMP = Path(r"C:\Users\kunal\AppData\Local\Temp\opencode\llm2")
DIMS = ("hook", "cliffhanger", "clarity")


def load_scores(path: Path) -> dict[str, dict]:
    data = json.loads(path.read_text(encoding="utf-8"))
    rows = data["scores"] if isinstance(data, dict) else data
    return {r["clip_id"]: r for r in rows}


def ranks(xs: list[float]) -> list[float]:
    """Average ranks, ties share the mean rank (1-based)."""
    order = sorted(range(len(xs)), key=lambda i: xs[i])
    out = [0.0] * len(xs)
    i = 0
    while i < len(order):
        j = i
        while j + 1 < len(order) and xs[order[j + 1]] == xs[order[i]]:
            j += 1
        avg = (i + j) / 2 + 1
        for k in range(i, j + 1):
            out[order[k]] = avg
        i = j + 1
    return out


def pearson(xs: list[float], ys: list[float]) -> float:
    n = len(xs)
    mx, my = sum(xs) / n, sum(ys) / n
    num = sum((x - mx) * (y - my) for x, y in zip(xs, ys))
    dx = sum((x - mx) ** 2 for x in xs) ** 0.5
    dy = sum((y - my) ** 2 for y in ys) ** 0.5
    return num / (dx * dy) if dx and dy else float("nan")


def spearman(xs: list[float], ys: list[float]) -> float:
    return pearson(ranks(xs), ranks(ys))


def comp(row: dict) -> float:
    return mean(float(row[d]) for d in DIMS)


def fmt(x: float, nd: int = 2) -> str:
    return "n/a" if x != x else f"{x:.{nd}f}"


def main() -> None:
    key = json.loads((OUT / "key.json").read_text(encoding="utf-8"))
    key_by_id = {r["clip_id"]: r for r in key}
    p1 = load_scores(TEMP / "pass1" / "scores.json")
    p2 = load_scores(TEMP / "pass2" / "scores.json")

    rows = []
    for cid in sorted(key_by_id):
        k = key_by_id[cid]
        s1, s2 = p1[cid], p2[cid]
        l2 = {d: (float(s1[d]) + float(s2[d])) / 2 for d in DIMS}
        rows.append(
            {
                "clip_id": cid,
                "promo_id": k["promo_id"],
                "stratum": k["stratum"],
                "rank": k["rank"],
                "qwen": {d: float(k["qwen"][d]) for d in DIMS},
                "llm2": l2,
                "pass1": {d: float(s1[d]) for d in DIMS},
                "pass2": {d: float(s2[d]) for d in DIMS},
                "would_post_1": bool(s1.get("would_post")),
                "would_post_2": bool(s2.get("would_post")),
                "safety_1": str(s1.get("safety", "")),
                "safety_2": str(s2.get("safety", "")),
            }
        )

    for r in rows:
        r["qwen_comp"] = comp(r["qwen"])
        r["llm2_comp"] = comp(r["llm2"])
        r["delta"] = r["llm2_comp"] - r["qwen_comp"]

    metrics: dict = {"n": len(rows), "per_dimension": {}, "pass_consistency": {}}

    for d in DIMS:
        q = [r["qwen"][d] for r in rows]
        l = [r["llm2"][d] for r in rows]
        diffs = [b - a for a, b in zip(q, l)]
        metrics["per_dimension"][d] = {
            "qwen_mean": round(mean(q), 3),
            "llm2_mean": round(mean(l), 3),
            "mean_delta": round(mean(diffs), 3),
            "spearman": round(spearman(q, l), 3),
            "mae": round(mean(abs(x) for x in diffs), 3),
            "exact": sum(1 for x in diffs if abs(x) < 1e-9),
            "within_1": sum(1 for x in diffs if abs(x) <= 1.0 + 1e-9),
            "n": len(diffs),
        }

    qc = [r["qwen_comp"] for r in rows]
    lc = [r["llm2_comp"] for r in rows]
    dc = [b - a for a, b in zip(qc, lc)]
    qwen_order = sorted(rows, key=lambda r: (-r["qwen_comp"], r["clip_id"]))
    llm2_order = sorted(rows, key=lambda r: (-r["llm2_comp"], r["clip_id"]))
    q10 = {r["clip_id"] for r in qwen_order[:10]}
    l10 = {r["clip_id"] for r in llm2_order[:10]}

    metrics["composite"] = {
        "qwen_mean": round(mean(qc), 3),
        "llm2_mean": round(mean(lc), 3),
        "mean_delta": round(mean(dc), 3),
        "spearman": round(spearman(qc, lc), 3),
        "mae": round(mean(abs(x) for x in dc), 3),
        "within_1": sum(1 for x in dc if abs(x) <= 1.0 + 1e-9),
        "top10_overlap": len(q10 & l10),
        "top10_qwen": [r["clip_id"] for r in qwen_order[:10]],
        "top10_llm2": [r["clip_id"] for r in llm2_order[:10]],
    }

    for d in DIMS:
        a = [r["pass1"][d] for r in rows]
        b = [r["pass2"][d] for r in rows]
        diffs = [y - x for x, y in zip(a, b)]
        metrics["pass_consistency"][d] = {
            "exact": sum(1 for x in diffs if abs(x) < 1e-9),
            "within_1": sum(1 for x in diffs if abs(x) <= 1.0 + 1e-9),
            "spearman": round(spearman(a, b), 3),
            "n": len(diffs),
        }

    strata = ("top", "mid", "bottom", "baseline")
    metrics["by_stratum"] = {}
    for s in strata:
        sub = [r for r in rows if r["stratum"] == s]
        metrics["by_stratum"][s] = {
            "n": len(sub),
            "qwen_comp": round(mean(r["qwen_comp"] for r in sub), 3),
            "llm2_comp": round(mean(r["llm2_comp"] for r in sub), 3),
            "llm2_would_post": round(mean(1.0 if (r["would_post_1"] and r["would_post_2"]) else
                                          0.5 if (r["would_post_1"] or r["would_post_2"]) else 0.0
                                          for r in sub), 3),
            "qwen_would_watch": round(mean(1.0 if key_by_id[r["clip_id"]]["qwen"]["would_watch_next_episode"] else 0.0
                                          for r in sub), 3),
        }

    safety_counts: dict[str, int] = {}
    for r in rows:
        for s in (r["safety_1"], r["safety_2"]):
            safety_counts[s] = safety_counts.get(s, 0) + 1
    metrics["safety_counts"] = safety_counts

    metrics["biggest_disagreements"] = sorted(rows, key=lambda r: -abs(r["delta"]))[:6]
    metrics["biggest_disagreements"] = [
        {
            "clip_id": r["clip_id"], "promo_id": r["promo_id"], "stratum": r["stratum"],
            "qwen": round(r["qwen_comp"], 2), "llm2": round(r["llm2_comp"], 2), "delta": round(r["delta"], 2),
        }
        for r in metrics["biggest_disagreements"]
    ]

    (OUT / "comparison.json").write_text(json.dumps(metrics, indent=1), encoding="utf-8")

    with (OUT / "per_clip.csv").open("w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f)
        w.writerow(["clip_id", "promo_id", "stratum", "qwen_rank", "qwen_hook", "qwen_cliff", "qwen_clarity",
                    "llm2_hook", "llm2_cliff", "llm2_clarity", "qwen_comp", "llm2_comp", "delta",
                    "would_post_p1", "would_post_p2", "safety_p1", "safety_p2"])
        for r in sorted(rows, key=lambda r: r["qwen_comp"], reverse=True):
            w.writerow([
                r["clip_id"], r["promo_id"], r["stratum"], r["rank"],
                *[fmt(r["qwen"][d], 2) for d in DIMS],
                *[fmt(r["llm2"][d], 2) for d in DIMS],
                fmt(r["qwen_comp"]), fmt(r["llm2_comp"]), fmt(r["delta"]),
                r["would_post_1"], r["would_post_2"], r["safety_1"], r["safety_2"],
            ])

    lines = []
    lines.append("# LLM-2 (DeepSeek V4.1 Flash) vs Qwen judge - blinded 24-clip packet\n")
    lines.append(f"- Clips: {metrics['n']} (8 top, 6 mid, 6 bottom, 4 baseline; distinct episodes)")
    lines.append("- Both judges saw only the clip transcript; LLM-2 had no ranks, scores, source or episode numbers.")
    lines.append("- LLM-2 scored twice in independent contexts; scores below are the mean of both passes.\n")
    lines.append("## Agreement\n")
    lines.append("| Dimension | Qwen mean | LLM-2 mean | Mean delta | Spearman | MAE | Exact | Within 1 |")
    lines.append("|---|---|---|---|---|---|---|---|")
    for d in DIMS:
        m = metrics["per_dimension"][d]
        lines.append(f"| {d} | {m['qwen_mean']:.2f} | {m['llm2_mean']:.2f} | {m['mean_delta']:+.2f} | "
                     f"{m['spearman']:.2f} | {m['mae']:.2f} | {m['exact']}/{m['n']} | {m['within_1']}/{m['n']} |")
    c = metrics["composite"]
    lines.append(f"| **composite** | {c['qwen_mean']:.2f} | {c['llm2_mean']:.2f} | {c['mean_delta']:+.2f} | "
                 f"{c['spearman']:.2f} | {c['mae']:.2f} | - | {c['within_1']}/{metrics['n']} |")
    lines.append(f"\nTop-10 overlap: **{c['top10_overlap']}/10**.\n")

    lines.append("## Does LLM-2 recover the rank strata?\n")
    lines.append("| Stratum | n | Qwen composite | LLM-2 composite | LLM-2 would-post | Qwen would-watch-next |")
    lines.append("|---|---|---|---|---|---|")
    for s in strata:
        m = metrics["by_stratum"][s]
        lines.append(f"| {s} | {m['n']} | {m['qwen_comp']:.2f} | {m['llm2_comp']:.2f} | "
                     f"{m['llm2_would_post']:.0%} | {m['qwen_would_watch']:.0%} |")

    lines.append("\n## LLM-2 pass 1 vs pass 2\n")
    lines.append("| Dimension | Exact | Within 1 | Spearman |")
    lines.append("|---|---|---|---|")
    for d in DIMS:
        m = metrics["pass_consistency"][d]
        lines.append(f"| {d} | {m['exact']}/{m['n']} | {m['within_1']}/{m['n']} | {m['spearman']:.2f} |")

    lines.append("\n## Biggest composite disagreements\n")
    lines.append("| Clip | Promo | Stratum | Qwen | LLM-2 | Delta |")
    lines.append("|---|---|---|---|---|---|")
    for r in metrics["biggest_disagreements"]:
        lines.append(f"| {r['clip_id']} | {r['promo_id']} | {r['stratum']} | {r['qwen']:.2f} | "
                     f"{r['llm2']:.2f} | {r['delta']:+.2f} |")

    lines.append("\n## Caveats\n")
    lines.append("- This is **cross-model agreement, not human validation**. LLM-2 is an LLM, not a viewer.")
    lines.append("- The packet is stratified by Qwen rank on purpose, so it spans the range; it is not a random sample.")
    lines.append("- n=24, text-only, one show. Treat effect sizes as directional.")
    lines.append("- Safety labels are subjective and not platform policy.")
    (OUT / "comparison.md").write_text("\n".join(lines), encoding="utf-8")

    print("\n".join(lines))
    print(f"\nwrote {OUT / 'comparison.md'}, comparison.json, per_clip.csv")


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    main()
