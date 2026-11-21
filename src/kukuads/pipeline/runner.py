"""Runs the whole pipeline on a folder of screenplays and writes the raw outputs.

Used by the Streamlit app and callable from Python.
"""
from __future__ import annotations

import csv
import json
import time
from pathlib import Path
from typing import Callable

from kukuads.llm import LLMError, make_clients

from .baseline import baseline_episode
from .find import find_candidates
from .judge import judge_promo
from .models import Promo, fmt_ts
from .parse import load_show
from .rank import rank
from .report import write_report
from .validate import validate_episode

Progress = Callable[[str, int, int, str], None]


def parse_episode_filter(spec: str | None) -> set[int] | None:
    """'1-5,12' -> {1,2,3,4,5,12}."""
    if not spec:
        return None
    out: set[int] = set()
    for part in spec.split(","):
        part = part.strip()
        if "-" in part:
            a, b = part.split("-")
            out.update(range(int(a), int(b) + 1))
        elif part:
            out.add(int(part))
    return out


def _segments_str(p: dict) -> str:
    return "; ".join(f"Ep {s['episode']} {fmt_ts(s['start'])}-{fmt_ts(s['end'])}" for s in p["segments"])


def write_csv(rows: list[dict], path: Path) -> None:
    cols = ["rank", "in_top_list", "promo_id", "episodes", "segments", "duration_s", "hook", "cliffhanger",
            "why", "patterns", "judge_hook", "judge_cliffhanger", "judge_clarity", "intensity", "final_score",
            "judge_summary", "judge_confusing", "judge_want_next", "validator_notes", "finder_model", "judge_model"]
    with path.open("w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=cols)
        w.writeheader()
        for r in rows:
            j = r.get("judge") or {}
            w.writerow({
                "rank": r.get("rank", ""), "in_top_list": r.get("in_top_list", ""), "promo_id": r["promo_id"],
                "episodes": ",".join(map(str, r["episodes"])), "segments": _segments_str(r),
                "duration_s": r["duration_s"], "hook": r["hook"], "cliffhanger": r["cliffhanger"], "why": r["why"],
                "patterns": ", ".join(r.get("patterns") or []), "judge_hook": j.get("hook", ""),
                "judge_cliffhanger": j.get("cliffhanger", ""), "judge_clarity": j.get("clarity", ""),
                "intensity": r.get("intensity", ""), "final_score": (r.get("scores") or {}).get("final", ""),
                "judge_summary": j.get("summary", ""), "judge_confusing": j.get("confusing", ""),
                "judge_want_next": j.get("want_next", ""), "validator_notes": " | ".join(r.get("notes") or []),
                "finder_model": r.get("finder_model", ""), "judge_model": j.get("model", ""),
            })


def run_pipeline(scripts_dir: str | Path, out_dir: str | Path, cfg: dict, episodes: str | None = None,
                 do_judge: bool = True, do_baseline: bool = True, progress: Progress | None = None,
                 cache_dir: str | Path = ".cache/llm") -> dict:
    t0 = time.time()
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    (out / "llm_calls.jsonl").unlink(missing_ok=True)
    say = progress or (lambda stage, i, n, msg: print(f"[{stage} {i}/{n}] {msg}", flush=True))

    show = load_show(scripts_dir)
    wanted = parse_episode_filter(episodes)
    targets = [e for e in show if wanted is None or e.number in wanted]
    by_num = {e.number: e for e in show}
    (out / "beats.json").write_text(json.dumps([e.to_dict() for e in targets], ensure_ascii=False, indent=1),
                                    encoding="utf-8")
    say("parse", len(targets), len(targets), f"{sum(len(e.beats) for e in targets)} beats from {len(targets)} episodes")

    clients = make_clients(cfg, out, cache_dir)
    pcfg = cfg.get("promo", {})
    llm_promos: list[Promo] = []
    errors: list[str] = []

    # Stage 2 + 3: find and validate, one episode at a time (sequential = no rate-limit storms)
    for i, ep in enumerate(targets, 1):
        try:
            raws, meta = find_candidates(ep, show, clients["finder"], pcfg.get("promos_per_episode", 3))
            found = validate_episode(raws, ep, pcfg, meta.get("served_by", ""))
            llm_promos += found
            ok = sum(p.status == "valid" for p in found)
            say("find", i, len(targets), f"Ep {ep.number}: {len(found)} proposed, {ok} valid ({meta.get('model')}"
                f"{', cached' if meta.get('cached') else ''})")
        except LLMError as e:
            errors.append(f"find Ep {ep.number}: {e}")
            say("find", i, len(targets), f"Ep {ep.number}: FAILED - {str(e)[:120]}")

    baseline: list[Promo] = []
    if do_baseline:
        for ep in targets:
            baseline += baseline_episode(ep, per_episode=2)
        say("baseline", len(targets), len(targets), f"{len(baseline)} rule-based promos")

    # Stage 4a: judge every valid LLM promo, plus the top baseline promo of each episode
    if do_judge:
        to_judge = [p for p in llm_promos if p.status == "valid"]
        if do_baseline:
            to_judge += [p for p in baseline if p.promo_id.endswith("-B1")]
        for i, p in enumerate(to_judge, 1):
            try:
                judge_promo(p, by_num, clients["judge"], cfg.get("judge_repeats", 1))
                j = p.judge
                say("judge", i, len(to_judge), f"{p.promo_id}: hook {j['hook']} / cliff {j['cliffhanger']} / clarity {j['clarity']}")
            except LLMError as e:
                errors.append(f"judge {p.promo_id}: {e}")
                p.status = "unjudged"        # kept out of the ranking: an unscored promo must not sit among the scored ones
                p.notes.append("judge failed: run the same command again to resume (judged clips come from the cache)")
                say("judge", i, len(to_judge), f"{p.promo_id}: FAILED - {str(e)[:120]}")

    # Stage 4b: rank
    rows = rank(llm_promos, cfg.get("ranking", {}))
    baseline_rows = rank([p for p in baseline if p.judge], cfg.get("ranking", {})) if do_judge else \
        [p.to_dict() for p in baseline]

    (out / "candidates.json").write_text(json.dumps([p.to_dict() for p in llm_promos], ensure_ascii=False, indent=1),
                                         encoding="utf-8")
    (out / "promos_ranked.json").write_text(json.dumps(rows, ensure_ascii=False, indent=1), encoding="utf-8")
    write_csv(rows, out / "promos_ranked.csv")
    (out / "baseline.json").write_text(json.dumps(baseline_rows, ensure_ascii=False, indent=1), encoding="utf-8")

    meta = {
        "scripts_dir": str(scripts_dir), "episodes": [e.number for e in targets],
        "finder_chain": cfg["stages"]["finder"], "judge_chain": cfg["stages"]["judge"],
        "promo_rules": pcfg, "ranking": cfg.get("ranking", {}),
        "wall_time_s": round(time.time() - t0, 1), "errors": errors,
        "unjudged": [p.promo_id for p in llm_promos if p.status == "unjudged"],
        "finished_at": time.strftime("%Y-%m-%d %H:%M:%S"),
    }
    (out / "run_meta.json").write_text(json.dumps(meta, indent=1), encoding="utf-8")
    write_report(out, targets, llm_promos, rows, baseline, meta)
    say("done", 1, 1, f"wrote outputs to {out} in {meta['wall_time_s']}s")
    return {"out_dir": str(out), "ranked": rows, "meta": meta}
