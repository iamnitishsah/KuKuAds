"""KuKuAds CLI.

Examples
  python run.py --selftest                                                # offline check, no LLM
  python run.py --scripts "path/to/show"                                  # full run, models from configs/config.yaml
  python run.py --scripts "path/to/show" --episodes 1-5                   # a few episodes
  python run.py --scripts "path/to/show" --provider anthropic --model claude-sonnet-5-5   # swap model
  python run.py --scripts "path/to/show" --judge-provider openai --judge-model <id>       # swap judge only
"""
from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

from dotenv import load_dotenv

sys.path.insert(0, str(Path(__file__).resolve().parent / "src"))  # run without installing the package

from kukuads.llm import apply_overrides, load_config
from kukuads.pipeline.runner import run_pipeline


def main() -> int:
    ap = argparse.ArgumentParser(description="Find, validate, judge and rank promos in a microdrama screenplay.")
    ap.add_argument("--scripts", help="folder of episode screenplays (.txt)")
    ap.add_argument("--selftest", action="store_true", help="offline check of the pipeline code (no LLM, no key)")
    ap.add_argument("--out", help="output folder (default: outputs/run-<timestamp>)")
    ap.add_argument("--episodes", help="subset, e.g. '1-5,12'")
    ap.add_argument("--config", default="configs/config.yaml")
    ap.add_argument("--provider", help="pin ALL stages to this provider (needs --model)")
    ap.add_argument("--model", help="model id for --provider")
    ap.add_argument("--judge-provider", help="pin only the judge stage")
    ap.add_argument("--judge-model")
    ap.add_argument("--no-judge", action="store_true", help="skip the cold-viewer judge")
    ap.add_argument("--no-baseline", action="store_true", help="skip the rules-only baseline")
    ap.add_argument("--no-cache", action="store_true", help="ignore cached LLM replies")
    args = ap.parse_args()
    if args.selftest:
        from kukuads.selftest import run_selftest
        steps = run_selftest()
        for s in steps:
            print(f"[{'ok' if s['ok'] else 'FAIL'}] {s['step']}: {s['detail']}")
        return 0 if len(steps) == 4 and all(s["ok"] for s in steps) else 1
    if not args.scripts:
        ap.error("--scripts is required (or use --selftest)")

    # Windows consoles default to cp1252; model text often has non-ASCII punctuation.
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="replace")
    if bool(args.provider) != bool(args.model):
        ap.error("--provider and --model go together")
    load_dotenv()
    cfg = apply_overrides(load_config(args.config), args.provider, args.model, args.judge_provider, args.judge_model)
    out = args.out or f"outputs/run-{time.strftime('%Y%m%d-%H%M%S')}"
    cache = f".cache/nocache-{time.time_ns()}" if args.no_cache else ".cache/llm"

    result = run_pipeline(args.scripts, out, cfg, episodes=args.episodes, do_judge=not args.no_judge,
                          do_baseline=not args.no_baseline, cache_dir=cache)
    top = [r for r in result["ranked"] if r.get("in_top_list")][:5]
    print("\nTop promos:")
    for r in top:
        segs = "; ".join(f"Ep {s['episode']} {s['start']:.1f}-{s['end']:.1f}s" for s in r["segments"])
        print(f"  #{r['rank']} {r['promo_id']}  {segs}  score {r['scores'].get('final')}  | {r['hook'][:70]}")
    print(f"\nReport: {Path(out) / 'report.md'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
