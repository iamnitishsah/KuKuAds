"""Writes report.md: top promos, validation funnel, quality numbers, LLM-vs-baseline, failures, cost."""
from __future__ import annotations

import json
from collections import Counter
from pathlib import Path
from statistics import mean

from .models import Episode, Promo, fmt_ts


def _avg(xs) -> str:
    xs = [x for x in xs if x is not None]
    return f"{mean(xs):.2f}" if xs else "-"


def _rate(xs, thr=4) -> str:
    xs = [x for x in xs if x is not None]
    return f"{100 * sum(x >= thr for x in xs) / len(xs):.0f}%" if xs else "-"


def _sign_p(wins: int, losses: int) -> float:
    """Two-sided sign test: chance of a split at least this uneven if both methods were equal."""
    from math import comb
    n = wins + losses
    if n == 0:
        return 1.0
    k = max(wins, losses)
    return min(1.0, 2 * sum(comb(n, i) for i in range(k, n + 1)) / 2 ** n)


def _cell(s: str, n: int = 90) -> str:
    s = " ".join(str(s).split()).replace("|", "/")
    return s if len(s) <= n else s[: n - 1] + "…"


def _segs(p: dict) -> str:
    return "<br>".join(f"Ep {s['episode']} {fmt_ts(s['start'])}–{fmt_ts(s['end'])}" for s in p["segments"])


def _best_per_episode(promos: list[Promo], source: str) -> dict[int, Promo]:
    best: dict[int, Promo] = {}
    for p in promos:
        if p.source != source or p.status != "valid" or not p.judge:
            continue
        ep = min(p.episodes)
        key = lambda q: (q.scores.get("final", 0) if q.scores else 0)
        if ep not in best or key(p) > key(best[ep]):
            best[ep] = p
    return best


def _quality_row(name: str, ps: list[Promo]) -> str:
    h = [p.judge.get("hook") for p in ps]
    c = [p.judge.get("cliffhanger") for p in ps]
    cl = [p.judge.get("clarity") for p in ps]
    return (f"| {name} | {len(ps)} | {_avg(h)} | {_avg(c)} | {_avg(cl)} | {_rate(h)} | {_rate(c)} | {_rate(cl)} | "
            f"{_avg([p.duration for p in ps])}s |")


def _llm_usage(out: Path) -> list[str]:
    log = out / "llm_calls.jsonl"
    if not log.exists():
        return ["No LLM calls logged."]
    recs = [json.loads(l) for l in log.read_text(encoding="utf-8").splitlines() if l.strip()]
    lines = ["| Stage | Calls | From cache | Fallback used | Rate-limit waits | Failed attempts | Input tokens | Output tokens | Avg latency (live) | Served by |",
             "|---|---|---|---|---|---|---|---|---|---|"]
    for stage in sorted({r["stage"] for r in recs}):
        rs = [r for r in recs if r["stage"] == stage]
        waits = [r for r in rs if r.get("rate_limited")]
        errs = [r for r in rs if "error" in r]
        ok = [r for r in rs if "error" not in r and not r.get("rate_limited")]
        live = [r for r in ok if not r.get("cached")]
        served = Counter(r.get("served_by", "?") for r in ok)
        lines.append(
            f"| {stage} | {len(ok)} | {sum(1 for r in ok if r.get('cached'))} | {sum(1 for r in ok if r.get('fallback'))} | "
            f"{len(waits)} ({sum(r.get('wait_s', 0) for r in waits):.0f}s) | {len(errs)} | "
            f"{sum(r.get('input_tokens', 0) for r in ok):,} | {sum(r.get('output_tokens', 0) for r in ok):,} | "
            f"{_avg([r.get('latency_s') for r in live])}s | {', '.join(f'{k} ×{v}' for k, v in served.most_common())} |")
    return lines


def write_report(out: Path, episodes: list[Episode], promos: list[Promo], rows: list[dict],
                 baseline: list[Promo], meta: dict) -> None:
    valid = [p for p in promos if p.status == "valid"]
    rejected = [p for p in promos if p.status == "rejected"]
    judged = [p for p in valid if p.judge]
    L: list[str] = []
    L += [f"# KuKuAds report", "",
          f"- Episodes: {len(episodes)} ({episodes[0].number}–{episodes[-1].number})" if episodes else "- Episodes: 0",
          f"- Finder model: `{meta['finder_chain'][0]['model']}` (fallbacks: {', '.join(m['model'] for m in meta['finder_chain'][1:]) or 'none'})",
          f"- Judge model: `{meta['judge_chain'][0]['model']}` (fallbacks: {', '.join(m['model'] for m in meta['judge_chain'][1:]) or 'none'})",
          f"- Rules: {meta['promo_rules'].get('min_s')}–{meta['promo_rules'].get('max_s')}s, hook within "
          f"{meta['promo_rules'].get('hook_window_s')}s",
          f"- Wall time: {meta['wall_time_s']}s · finished {meta['finished_at']}",
          f"- Errors: {len(meta['errors'])}", ""]

    # Top list
    top = [r for r in rows if r.get("in_top_list")]
    L += ["## Post these first", "",
          "| # | Promo | Segments | Len | Hook | Cliffhanger | Why it works | H/C/Cl | Score |",
          "|---|---|---|---|---|---|---|---|---|"]
    for r in top:
        j = r.get("judge") or {}
        L.append(f"| {r['rank']} | {r['promo_id']} | {_segs(r)} | {r['duration_s']:.0f}s | {_cell(r['hook'], 70)} | "
                 f"{_cell(r['cliffhanger'], 70)} | {_cell(r['why'], 90)} | {j.get('hook', '-')}/{j.get('cliffhanger', '-')}/"
                 f"{j.get('clarity', '-')} | {(r.get('scores') or {}).get('final', '-')} |")
    L += ["", "H/C/Cl = cold-viewer judge scores (1–5) for hook, cliffhanger and clarity to a stranger. "
              "Score = weighted judge scores + screenplay intensity + early-episode bonus. "
              "Top list allows at most one promo per episode; the full ranked list is in `promos_ranked.csv`.", ""]

    # Funnel
    reasons = Counter(p.notes[-1].split(" (")[0] for p in rejected if p.notes)
    fixes = Counter(n.split(" (")[0] for p in valid for n in p.notes if "judge" not in n)
    L += ["## Validation funnel", "",
          f"- Proposed by the finder: **{len(promos)}**  ·  valid: **{len(valid)}**  ·  rejected: **{len(rejected)}**",
          "- Rejection reasons: " + (", ".join(f"{k} ×{v}" for k, v in reasons.most_common()) or "none"),
          "- Automatic fixes applied to valid promos: " + (", ".join(f"{k} ×{v}" for k, v in fixes.most_common()) or "none"),
          ""]

    # Quality
    llm_best = _best_per_episode(promos, "llm")
    base_best = _best_per_episode(baseline, "baseline")
    common = sorted(set(llm_best) & set(base_best))
    all_judged = judged + [p for p in baseline if p.judge]
    mix = Counter(p.judge.get("served_by") or p.judge.get("model") or "?" for p in all_judged)
    finder_name = meta["finder_chain"][0]["model"]
    self_graded = [p for p in judged if finder_name in str(p.judge.get("served_by", ""))]
    L += ["## Quality (cold-viewer judge)", "",
          f"Judge models used ({len(mix)}): " + ", ".join(f"{k} ×{v}" for k, v in mix.most_common()) + ".",
          f"Pipeline promos judged by the finder's own model ({finder_name}): **{len(self_graded)} of {len(judged)}**"
          + (" — these may be scored generously." if self_graded else "."),
          ("When several judge models are mixed, scores are noisier and LLM-vs-baseline comparisons are only indicative."
           if len(mix) > 1 else "A single judge model scored every clip, so scores are comparable across promos and methods."),
          ]
    reps = [p for p in all_judged if len(p.judge.get("repeats") or []) > 1]
    if reps:
        pairs = [(r[0][d], r[1][d]) for p in reps for r in [p.judge["repeats"]] for d in ("hook", "cliffhanger", "clarity")]
        L += [f"Judge consistency: each clip judged {len(reps[0].judge['repeats'])}×; the repeats gave the identical "
              f"score {100 * sum(a == b for a, b in pairs) / len(pairs):.0f}% of the time and were within 1 point "
              f"{100 * sum(abs(a - b) <= 1 for a, b in pairs) / len(pairs):.0f}% of the time. Scores shown are averages."]
    L += [
          "", "Rates = share of promos scoring 4 or 5. Comparison uses the best promo per episode from each method.", "",
          "| Method | Promos | Hook | Cliffhanger | Clarity | Hook rate | Suspense rate | Standalone rate | Avg length |",
          "|---|---|---|---|---|---|---|---|---|",
          _quality_row("All valid LLM promos", judged),
          _quality_row("LLM pipeline, best per episode", [llm_best[e] for e in common]),
          _quality_row("Rules-only baseline, best per episode", [base_best[e] for e in common]), ""]
    if common:
        diffs = [llm_best[e].scores.get("final", 0) - base_best[e].scores.get("final", 0) for e in common]
        wins, losses = sum(d > 1e-9 for d in diffs), sum(d < -1e-9 for d in diffs)
        L += [f"LLM pipeline's best promo beat the baseline's best promo in **{wins} of {len(common)}** episodes "
              f"(lost {losses}; two-sided sign test p = {_sign_p(wins, losses):.3f}).", ""]
        L += ["| Dimension | Mean difference (LLM − baseline) | LLM better | Baseline better | Sign test p |",
              "|---|---|---|---|---|"]
        for d in ("hook", "cliffhanger", "clarity"):
            dd = [llm_best[e].judge[d] - base_best[e].judge[d] for e in common]
            w, l = sum(x > 0 for x in dd), sum(x < 0 for x in dd)
            L.append(f"| {d} | {mean(dd):+.2f} | {w} | {l} | {_sign_p(w, l):.3f} |")
        L.append("")

    # Clarity by arc
    L += ["### Standalone clarity by episode range", "", "| Episodes | Promos | Avg clarity | Standalone rate |",
          "|---|---|---|---|"]
    for lo in range(1, (max((e.number for e in episodes), default=0)) + 1, 10):
        ps = [p for p in judged if lo <= min(p.episodes) < lo + 10]
        if ps:
            L.append(f"| {lo}–{lo + 9} | {len(ps)} | {_avg([p.judge['clarity'] for p in ps])} | "
                     f"{_rate([p.judge['clarity'] for p in ps])} |")
    L.append("")

    # Failures
    weak = [p for p in judged if min(p.judge["clarity"], p.judge["hook"], p.judge["cliffhanger"]) <= 3]
    worst = sorted(weak, key=lambda p: (p.judge["clarity"], p.judge["hook"] + p.judge["cliffhanger"]))[:10]
    L += ["## Where it picks badly", "", "Lowest-clarity picks, with what confused the cold viewer:", "",
          "| Promo | H/C/Cl | Judge saw | Confusing |", "|---|---|---|---|"]
    for p in worst:
        j = p.judge
        L.append(f"| {p.promo_id} | {j['hook']}/{j['cliffhanger']}/{j['clarity']} | {_cell(j['summary'], 90)} | "
                 f"{_cell(j['confusing'], 110)} |")
    if rejected:
        L += ["", "Sample rejected candidates:", ""]
        L += [f"- {p.promo_id}: {'; '.join(p.notes)}" for p in rejected[:8]]
    L.append("")

    # Cost / usage
    L += ["## LLM usage", ""] + _llm_usage(out) + [""]
    if meta["errors"]:
        L += ["## Errors", ""] + [f"- {_cell(e, 300)}" for e in meta["errors"]] + [""]
    (out / "report.md").write_text("\n".join(L), encoding="utf-8")
