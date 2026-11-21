# Promo Finder: Solution (Problem 1)

**Prototype:** https://github.com/iamnitishsah/KuKuAds · **Raw outputs:** `outputs/full-run/` (shared via Drive link, not in the repo, because the input pack is confidential)

## Why this problem
An editor watches every episode to pick promos, and new shows arrive weekly. It's the one problem where the output is checkable (a timestamp range, a hook, a cliffhanger) and where code and AI each have a clear job. I scoped it to *finding* promos only: no editing, music or overlays.

## Assumptions
- Screenplay timestamps match the final video. A promo is 20–60 s, with the hook in the first 3 s and the cut on an unresolved moment.
- I judge from text (dialogue plus shot descriptions); I cannot see video or hear audio.
- One promo per episode in the "post first" list, so the top 15 isn't one storyline.
- Early episodes get a small bonus (0.05 for Ep ≤ 5): a new viewer can enter there.

## How it works
| Stage | Owner | What it does |
|---|---|---|
| Parse | code | Screenplay → 3,727 beats with stable IDs (`E01-B008`), 0 parse mismatches |
| Find | LLM, 1 call per episode | Picks candidate promos as **beat IDs only**, so it cannot invent timestamps |
| Validate | code | IDs → timestamps; enforce 20–60 s, hook ≤ 3 s, end on the cliffhanger, never cut a line; every fix or rejection is logged |
| Judge | a *different* LLM | A "cold viewer" sees only the clip and scores hook, cliffhanger, clarity (anchored 1–5) |
| Rank | code | 0.3 hook + 0.3 cliffhanger + 0.3 clarity + 0.1 intensity (+ early bonus), one per episode in the top 15 |
| Baseline | code | Rules-only sliding window, scored by the same judge, as the control |

**Human in the loop:** the tool outputs a ranked list with reasons; an editor approves what gets posted.
**Swappable model:** one model per stage in `configs/config.yaml`, or `python run.py --provider anthropic --model <id>`. Adapters cover OpenAI, Gemini, Groq, Anthropic, Ollama and any OpenAI-compatible router. Calls are cached and logged, including which model actually answered. A new show runs with `python run.py --scripts <folder>`.

## Scale and cost
50 episodes ≈ 169k tokens. One full run ≈ **517k tokens** (finder 50 calls; judge 256 calls) and took ~51 min on a free self-hosted 27B model. Cost grows linearly with episodes; re-runs are free from the cache. With a paid API I'd use a stronger model for the finder and judge and run shows in parallel, but the pipeline wouldn't change.

## How I know it's good
| Check | Result |
|---|---|
| Format rules in code | 78/78 promos are 20–60 s with the hook within 3 s; 77/78 end on the cliffhanger by label (76/78 by timestamp) |
| Hallucination | 0 invented quotes |
| Coverage | 84 proposed → 78 valid; 49 of 50 episodes covered |
| vs. rules-only baseline (best per episode, 49 eps) | LLM wins 31–18 overall (p = 0.085, not proven); cliffhanger +0.27 (20 vs 7, unadjusted p = 0.019, does **not** survive Holm correction for four tests); hook (p = 0.11) and clarity (p = 0.25) are not |
| Judge stability (one model, two passes) | identical score 79% of the time **per dimension**, within 1 point 99%; rank correlation 0.90; top-15 overlap 11/15 |
| Self-grading | 0 of 78 clips graded by the model that found them |
| Run-to-run check (all-qwen) | Only **2 of the archived top 5** survive (top-10 6/10, top-15 8/15). **E31-P2 is #1 in both runs** and in the blinded LLM-2 check. All 83 promos in that run were self-graded, so it is a coverage/finder check, not independent quality. |

So the LLM's real value is **choosing where to cut**; on hook and clarity a simple baseline is close.
**Not yet done:** a human-labelled gold set (about 20 blind clips, to check the judge against a person). Until then, "good" means "agrees with an LLM judge", which is a proxy. The real metric would be 3-second hold and click-through in A/B-tested ads.

## Where it fails
- **Coverage is model-dependent.** The archived run misses Ep 42 (17.4 s, rejected); an all-qwen run covers Ep 42 but misses Ep 33 (60.3 s after repair, 0.3 s over the cap). The stable issue is the hard 60 s boundary, not one episode.
- **Cut edges:** E04-P2 ends 0.1 s inside a line; E32-P1 starts 0.2 s inside one. E01-P1 does include Gerald's "I changed my mind."; Clarissa's sting starts 3.5 s after the cut. E47-P1 does not end mid-sentence.
- **Lenient judge:** 72.2% of the archived averaged LLM scores are 4–5 (75.1% in the all-qwen run), so small gaps at the top are weak evidence.
- **Self-grading:** in the all-qwen run, all 83 promos were judged by the finder model; those scores may be generous.
- **Brand safety:** Ep 31/32 are high-ranked (#1/#3) and use a red-hot iron inches from an eye (threat, no contact). Ep 39's guard is knocked unconscious, not killed, and ranks #47; Ep 50's intimate scene is real but ranks #63. There's no check yet.
- **Low clarity:** mid-story scenes with unexplained names or relationships (e.g. E49-P1, E06-P2, E17-P1).

I'd fix these next: repair-or-retry for short and boundary-length clips, edge checks, head-to-head ranking for the top clips, a safety flag, then the gold set.

## AI tools used, and one place they got it wrong
Claude (Claude Code) for research, code and auditing; `gpt-oss-120b` / `command-a` through a local router as the finder; self-hosted `qwen3.8:27b` as the judge. A second all-qwen run (qwen finder + judge) is reported in the evaluation as a coverage/finder check; it is self-graded and not used as independent quality evidence.
**Where it went wrong:** my router silently fell back to the finder model when the judge was rate-limited, so the finder graded 108 of 128 clips itself. The per-call log showed the real model; I made the client wait out the limit and keep the pinned model, and the report now counts self-graded clips. Details of 12 such problems: `docs/DEV_LOG.md`.
