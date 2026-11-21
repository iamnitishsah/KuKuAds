# Evaluation: how we know it's good

Five layers, cheapest first. Each says what was actually measured and what has **not** been done yet.

## 1. Hard checks in code (done, 100% of outputs)
| Check | Result |
|---|---|
| Quoted hook/cliffhanger text really exists in the screenplay (hallucination check) | 0 invented quotes (two apparent misses: one merge of two real lines, one truncated SOUND FX line) |
| Duration 20–60 s | 78 / 78 |
| Hook within the first 3 s | 78 / 78 |
| Ends on the cliffhanger beat | 77 / 78 by end-beat label; **76 / 78 by timestamp** (E04-P2 runs 4.0 s past, E06-P2 3.2 s past) |
| Episodes with at least one promo | 49 / 50 in both runs: archived misses Ep 42; all-qwen misses Ep 33. See §6. |

Funnel: 84 proposed → 78 valid, 6 rejected (4 too short, 2 duplicates).

## 2. Baseline comparison (done)
Control = rules-only sliding window, scored by the same judge. Best promo per episode from each method (49 episodes):

| Dimension | Mean diff (LLM − baseline) | LLM better | Baseline better | Sign-test p |
|---|---|---|---|---|
| cliffhanger | +0.27 | 20 | 7 | **0.019** |
| hook | +0.11 | 17 | 8 | 0.108 |
| clarity | +0.10 | 17 | 10 | 0.248 |
| overall | – | 31 | 18 | 0.085 |

Honest reading: the LLM is clearly better at choosing **where to cut** (the cliffhanger); on hook and clarity the
simple baseline is close and the difference is not statistically proven.

### 2.1 Second run: all-qwen (same judge, `qwen3.8:27b` finder)

A second 50-episode run used the **same model for both stages**. It is an end-to-end demonstration and a
finder-sensitivity check, **not** an independent quality evaluation: all 83 LLM promos were judged by the
model that found them.

| Dimension | Mean diff (LLM − baseline) | LLM better | Baseline better | Sign-test p |
|---|---|---|---|---|
| cliffhanger | +0.20 | 20 | 10 | 0.099 |
| hook | +0.13 | 18 | 10 | 0.185 |
| clarity | **+0.27** | 21 | 5 | **0.002** |

Overall: LLM wins **30 of 49** episodes (p = 0.079). Clarity is the only dimension that survives correction
(three tests, Holm threshold 0.0167), but it is also the dimension most exposed to self-grading. Treat it as
suggestive, not proven.

## 3. Judge reliability (done)
Single judge model for every clip (`qwen3.8:27b`, self-hosted), each clip judged twice:
- Identical score 79% of the time **per dimension**; within 1 point 99%. Only **51.6%** of clips had all three
  dimensions identical across repeats.
- Rank correlation between the two passes: 0.90. Top-15 overlap 11/15, top-5 overlap 4/5.
- 0 of 78 clips graded by the model that found them in the archived run. In the all-qwen run, **83 of 83** were
  self-graded (see §6), so those scores may be generous.
- **Leniency:** 72.2% of the archived averaged LLM dimension scores are 4 or 5 (75.1% in the all-qwen run).
  The often-quoted 79% only reproduces by pooling raw repeats across all 128 clips, including the baseline.
  Ordering is stable but small gaps near the top are weak evidence.

Earlier, with 20 mixed judge models (router fallback), agreement was poor (hook correlation 0.19, top-15 overlap 6/15)
and average score rose 2.95 → 4.47. That run is kept as `outputs/full-run-v3-mixed-judges` as evidence.

## 4. Human gold set (NOT done yet)
The judge is an LLM, so a human must check it. Plan: ~20 clips (8 top, 6 middle, 6 bottom/baseline), shuffled and blind;
the human scores hook/cliffhanger/clarity and answers "would I post this?". Report: precision@10 (target ≥ 7/10),
judge-vs-human Spearman (target ≥ 0.5), and % within 1 point (target ≥ 80%). Results go here once collected.

## 5. Planned fixes to the weak spots (not built yet)
- Head-to-head comparisons (both orders) for the top ~24 to fix leniency.
- Repair instead of reject for too-short clips (Ep 42) and boundary-length clips (Ep 33: 60.3 s after repair).
- Start/end edge checks; the validator still lets E04-P2 end 0.1 s inside a line and E32-P1 start 0.2 s inside one.
- A second, unrelated judge model on the same clips; do not let the finder judge its own picks.

## 6. Run-to-run stability (all-qwen)

Same judge, same episodes, different finder. This isolates **finder sensitivity**; it does not isolate judge
quality, because the all-qwen run is self-graded.

| Metric | Archived (`gpt-oss` finder) | All-qwen |
|---|---|---|
| Valid LLM promos | 78 | 83 |
| Proposed → valid → rejected | 84 → 78 → 6 | 89 → 83 → 6 |
| Episodes covered | 49/50 (missing **Ep 42**) | 49/50 (missing **Ep 33**) |
| Self-graded LLM promos | 0/78 | **83/83** |
| Dimension scores ≥4 | 72.2% | 75.1% |
| Judge repeats identical / within 1 | 79% / 99% | 80% / 99% |
| Top-5 overlap between runs | — | **2/5** |
| Top-10 overlap between runs | — | **6/10** |
| Top-15 overlap between runs | — | **8/15** |

**Archived top five:** E31-P2, E43-P1, E32-P1, E01-P1, E13-P1.

**All-qwen top five:** E31-P2, E01-P1, E15-P1, E02-P1, E42-P1.

- **E31-P2 is #1 in both runs**, and also #1 in the blinded LLM-2 check. It is the only pick that survives every
  configuration; treat it as the robust one.
- **Ep 42 is not a fixed gap.** The all-qwen finder found E42-P1 (17.9–77.8 s, 59.9 s, judged 4.5/5/4.5, rank #5).
  The archived finder’s E42-P1 was rejected at 17.4 s. The missing episode is model-dependent.
- **Ep 33 becomes the new gap.** E33-P1 started at 100.3 s; the validator moved the start to B064, leaving 60.3 s,
  0.3 s over the cap, and rejected it. No other Ep33 candidate existed.
- The exact top order is **finder-dependent**: 7 of 15 entries change. E43-P1 (#2 archived) becomes E43-P3 (#12);
  E32-P1 falls #3 → #10; E13-P1 falls out of the top 15. E15-P1, E42-P1, E10-P1, E05-P2, E12-P2 and E47-P1 enter.
- Because the all-qwen scores are self-graded, do **not** compare them to the archived scores as if they were
  independent. Use the archived run (different finder and judge) for judge evidence, and the all-qwen run for
  coverage and finder-sensitivity evidence.

## What the real-world metric would be
Hold rate at 3 s, completion rate, click-through and installs from A/B-tested ads. The offline judge is only a proxy.
