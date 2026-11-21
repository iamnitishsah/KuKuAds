# Findings

What the runs showed: what we would post first, how that was measured, and where it fails. Open fixes are in
[ROADMAP.md](ROADMAP.md); the long evidence reports are in [`eval/reports/`](../eval/reports/).

## In short

- It finds usable promos: 78 valid across 49 of 50 episodes in the archived run, and 72 valid across **50 of 50** after the
  validator fixes, all within the length and hook rules.
- Its real value is **where to cut**. It beat a rules-only baseline on the cliffhanger in 20 of 49 episodes (lost 7).
  On hook and clarity it is not clearly better, and the overall win (31 of 49) is not statistically proven.
- The ranking is a shortlist, not a verdict: changing the finder model changes 7 of the top 15, and re-running the same model changes 9 of 15.
  E31-P2 was #1 in the first two runs and the blinded check, but the re-run did not propose it.
- Nothing has been checked against a human yet, so "good" means "an AI judge agrees".

## What we'd post first

**Archived run** (`gpt-oss-120b` finder + `qwen3.8:27b` judge): **E31-P2, E43-P1, E32-P1, E01-P1, E13-P1**
(then E02-P1, E33-P1, E45-P1, E16-P1, E18-P1 …).

**All-qwen run** (same judge, `qwen3.8:27b` finder): **E31-P2, E01-P1, E15-P1, E02-P1, E42-P1**
(then E10-P1, E05-P2, E16-P1, E18-P1, E32-P1 …).

**Re-run with the fixed validator** (`gpt-oss-120b` finder + Groq `qwen3.8-27b` judge): **E32-P1, E01-P1, E02-P1, E45-P1, E15-P1**
(then E31-P1, E05-P1, E18-P2, E41-P2, E03-P1 …).

- **E31-P2 was #1** in the archived run, the all-qwen run and the blinded LLM-2 check. The re-run did not propose it (E31-P1, a different clip of
  the same episode, is #6), so no single pick is guaranteed. E01-P1 is in the top five of all three finder runs.
- The exact order is **finder-dependent**: top-5 overlap is **2/5**, top-10 **6/10**, top-15 **8/15**.
- Pattern: a cruel or shocking line, then a threat, accusation or betrayal left hanging. Two of the top five fit that wording exactly; the other three are a looser "unresolved danger or betrayal". See the detailed report.

**Run-to-run check:** changing the finder model changes 7 of the 15 top-list entries even with the same judge. Treat the ranking as a shortlist, not a fixed verdict.

## How it was evaluated

Cheapest layer first. Each says what was measured, and what has not been done.

### 1. Hard checks in code (every output)
| Check | Result |
|---|---|
| Quoted hook/cliffhanger text really exists in the screenplay (hallucination check) | 0 invented quotes (two apparent misses: one merge of two real lines, one truncated SOUND FX line) |
| Duration 20–60 s | 78 / 78 |
| Hook within the first 3 s | 78 / 78 |
| Ends on the cliffhanger beat | 77 / 78 by end-beat label; **76 / 78 by timestamp** (E04-P2 runs 4.0 s past, E06-P2 3.2 s past) |
| Episodes with at least one promo | 49 / 50 in both runs: archived misses Ep 42; all-qwen misses Ep 33. See section 4. |

Funnel: 84 proposed → 78 valid, 6 rejected (4 too short, 2 duplicates).

### 2. Baseline comparison
Control = rules-only sliding window, scored by the same judge. Best promo per episode from each method (49 episodes):

| Dimension | Mean diff (LLM − baseline) | LLM better | Baseline better | Sign-test p |
|---|---|---|---|---|
| cliffhanger | +0.27 | 20 | 7 | **0.019** |
| hook | +0.11 | 17 | 8 | 0.108 |
| clarity | +0.10 | 17 | 10 | 0.248 |
| overall | – | 31 | 18 | 0.085 |

Honest reading: the LLM is clearly better at choosing **where to cut** (the cliffhanger); on hook and clarity the
simple baseline is close and the difference is not statistically proven.

#### Second run: all-qwen (same judge, `qwen3.8:27b` finder)

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

### 3. Judge reliability
Single judge model for every clip (`qwen3.8:27b`, self-hosted), each clip judged twice:
- Identical score 79% of the time **per dimension**; within 1 point 99%. Only **51.6%** of clips had all three
  dimensions identical across repeats.
- Rank correlation between the two passes: 0.90. Top-15 overlap 11/15, top-5 overlap 4/5.
- 0 of 78 clips graded by the model that found them in the archived run. In the all-qwen run, **83 of 83** were
  self-graded (see section 4), so those scores may be generous.
- **Leniency:** 72.2% of the archived averaged LLM dimension scores are 4 or 5 (75.1% in the all-qwen run).
  The often-quoted 79% only reproduces by pooling raw repeats across all 128 clips, including the baseline.
  Ordering is stable but small gaps near the top are weak evidence.

Earlier, with 20 mixed judge models (router fallback), agreement was poor (hook correlation 0.19, top-15 overlap 6/15)
and average score rose 2.95 → 4.47. That run is kept as `outputs/full-run-v3-mixed-judges` as evidence.

### 4. Run-to-run stability (all-qwen)

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

- **E31-P2 is #1 in both runs**, and also #1 in the blinded LLM-2 check. It was not proposed in the later re-run, so
  it is robust to the model that finds it, but not guaranteed to appear.
- **Ep 42 is not a fixed gap.** The all-qwen finder found E42-P1 (17.9–77.8 s, 59.9 s, judged 4.5/5/4.5, rank #5).
  The archived finder’s E42-P1 was rejected at 17.4 s. The missing episode is model-dependent.
- **Ep 33 becomes the new gap.** E33-P1 started at 100.3 s; the validator moved the start to B064, leaving 60.3 s,
  0.3 s over the cap, and rejected it. No other Ep33 candidate existed.
- The exact top order is **finder-dependent**: 7 of 15 entries change. E43-P1 (#2 archived) becomes E43-P3 (#12);
  E32-P1 falls #3 → #10; E13-P1 falls out of the top 15. E15-P1, E42-P1, E10-P1, E05-P2, E12-P2 and E47-P1 enter.
- Because the all-qwen scores are self-graded, do **not** compare them to the archived scores as if they were
  independent. Use the archived run (different finder and judge) for judge evidence, and the all-qwen run for
  coverage and finder-sensitivity evidence.

### 5. Blinded second-LLM check
24 anonymised clips (8 top, 6 mid, 6 bottom, 4 baseline) plus a top-5 supplement, rated twice by a different model
family (DeepSeek V4.1 Flash, "LLM-2") that sees only the clip, with no pipeline context. Method, exact prompts and every
per-clip score: [`eval/reports/LLM2_EVALUATION.md`](../eval/reports/LLM2_EVALUATION.md).

**Agreement with the Qwen judge** (mean delta = LLM-2 minus Qwen):

| Dimension | Qwen mean | LLM-2 mean | Mean delta | Spearman | Within 1 point |
|---|---|---|---|---|---|
| Hook | 4.08 | 3.48 | −0.60 | 0.73 | 20/24 |
| Cliffhanger | 4.08 | 3.23 | −0.85 | 0.80 | 16/24 |
| Clarity | 3.96 | 3.75 | −0.21 | 0.54 | 23/24 |
| **Composite** | **4.04** | **3.49** | **−0.56** | **0.73** | **21/24** |

**The ranking signal survives:**

| Stratum | n | Qwen composite | LLM-2 composite | LLM-2 would-post |
|---|---|---|---|---|
| Top | 8 | 4.60 | 3.83 | 94% |
| Mid | 6 | 4.19 | 3.54 | 75% |
| Bottom | 6 | 3.33 | 2.96 | **25%** |
| Baseline | 4 | 3.75 | 3.50 | 75% |

**Self-consistency on the same 24 clips** (two passes each):

| Dimension | Qwen exact | Qwen Spearman | LLM-2 exact | LLM-2 Spearman |
|---|---|---|---|---|
| Hook | 18/24 | 0.72 | 10/24 | 0.76 |
| Cliffhanger | 20/24 | **0.91** | 7/24 | **0.53** |
| Clarity | 18/24 | 0.84 | 12/24 | 0.74 |

What it shows and what it does not:
- The Qwen ranking is not purely Qwen-specific: a different model family reproduces top > mid > bottom, and its
  would-post rate falls to 25% on the bottom stratum.
- Qwen is lenient, by about +0.56 composite and +0.85 on cliffhanger.
- The top-1 pick (E31-P2) was stable across models (the re-run did not propose it); the top-10 overlap is 6/10, so the exact order is only partly stable.
- Cliffhanger is the weakest dimension: Qwen overrates it most, and LLM-2's own two passes agree least there (ρ 0.53).
- Biggest disagreements (Qwen vs LLM-2): E07-P1 4.67 vs 3.42, E29-P2 4.50 vs 3.33, E11-P1 4.50 vs 3.33.
- It does **not** show that either model matches a human viewer, that the absolute scores are right, or that this holds
  for another show or for video and audio. 24 clips is a directional check, not a precise estimate.

### 6. Human gold set

### 7. Real-world metric

## Where it picks badly (real, from the runs)

| Issue | Detail | Status |
|---|---|---|
| Missed episode | **Model-dependent.** The archived `gpt-oss` run misses **Ep 42** (E42-P1 rejected at 17.4 s after the hook move). The all-qwen run covers Ep 42 (E42-P1 59.9 s, #5) but misses **Ep 33**: E33-P1 started at 100.3 s, the start moved to B064, leaving **60.3 s** — 0.3 s over the 60 s cap — and was rejected. The stable issue is the hard 60 s boundary, not one episode. | **fixed in code** (see below); archived run not regenerated |
| Cut edges | **E04-P2** ends 0.1 s inside a spoken line; **E32-P1** starts 0.2 s inside one. **E01-P1** does include Gerald's "I changed my mind."; Clarissa's sting ("People change their minds, sister.") starts 3.5 s after the cut. **E47-P1** does not end mid-sentence — the complete line is B067 and the next line is omitted whole. | **fixed in code** (see below); archived run not regenerated |
| Lenient judge | **72.2%** of the archived averaged LLM dimension scores are ≥4; **75.1%** in the all-qwen run. The often-quoted **79%** only appears when pooling raw repeats across all 128 clips, including the baseline. | open, fix planned (pairwise) |
| Self-grading | The archived run has **0/78** LLM promos graded by the finder model. The all-qwen run has **83/83** — the same model found and judged every promo, so its scores may be generous and are not independent. | known limit |
| Brand safety | Ep 31/32 are real and high-ranked: E31-P2 is **#1**, E32-P1 is **#3**, both with a red-hot iron inches from an eye (threat, no contact). Ep 39 is **#47** and the guard is knocked **unconscious**, not killed. Ep 50 is **#63**: the intimate scene is real, but the promo is near the bottom. In the re-run E32-P1 is **#1** and E31-P1 is **#6**, both again with the iron. | open, no check yet |
| Low-clarity picks | E49-P1 (2.5), then E06-P2, E17-P1, E19-P3, E07-P2, E20-P1, E09-P1, E14-P1, E33-P3, E37-P3 (all 3.0). Every one is low-ranked (ranks 56–78); none is a top-15 pick. | known limit |
| Useless field | `context_needed` came back `"low"` for **84/84** proposals. Zero variance, no signal; `rank.py` never reads it. | field removed from the prompt |
| Late-episode skew | **Not supported** by the delivered top 15: mean episode 23.2 vs 23.97 for all promos; only the top 3 are late. Removing the 0.05 early-episode bonus changes no top-15 membership, only the order. | not supported |

## Fixed since the archived run

The validator and the judge-failure handling were changed after the archived runs. Checked by replaying every promo
from both archived runs through the new code against the screenplays:

| Problem | Fix | Replay result |
|---|---|---|
| Too-short clips rejected (Ep 42 and 8 others) | repair before rejecting: start back to a strong beat, else end extended past the cliffhanger, else start back to a weaker hook; every repair is logged in `notes` | all 9 previously rejected short clips are now valid (Ep 42 becomes 30.2 s with a weaker hook) |
| Boundary clip rejected (Ep 33: 60.3 s) | shot snapping can no longer push a clip past the cap; a too-long clip falls back to a later beat | valid at exactly 60.0 s |
| Cuts inside a spoken line (E04-P2 end, E32-P1 start) | both edges are checked after shot snapping | 6 edges moved, all off a spoken line; 155 of 161 previously valid promos unchanged |
| Hook pushed past 3 s by shot snapping | the start only snaps back while the hook stays inside the window; a final check rejects otherwise | 0 of 171 replayed promos break the length, hook-window or cut-inside-a-line rules |
| A promo whose judge call failed stayed "valid" with a score of 0 | it becomes `unjudged`, is left out of the ranking, and the report and app say so; one failed repeat no longer discards the other | covered by tests |

This table is a replay of the finder's archived picks. The end-to-end re-run is in the next section. A repaired clip
ends past the finder's cliffhanger, so the judge scores the cliffhanger of the clip as it now ends.

## Re-run with the fixed validator (all 50 episodes)

A new end-to-end run on 2026-11-21: finder `gpt-oss-120b` (Groq), judge `qwen3.8-27b` (Groq), the validator and
judge handling above. Files: `outputs/full-run-groq/` (gitignored, like all outputs). The judge here is the Groq-hosted
Qwen, the archived run used a self-hosted one, so the two runs are not identical in serving. 3 of 50 finder replies were
reused from an earlier cache; the rest are fresh. The same comparison method reproduces the archived numbers exactly
(20 vs 7, p = 0.019), so the two columns are comparable.

| Check | Archived run | Re-run |
|---|---|---|
| Valid promos (proposed) | 78 (84) | 72 (73) |
| Episodes with at least one promo | 49 / 50 (misses Ep 42) | **50 / 50** (Ep 33 and Ep 42 both covered) |
| Duration 20–60 s | 78 / 78 | 72 / 72 |
| Clip edges inside a spoken line | 2 (E04-P2 end, E32-P1 start) | **0 of 154** |
| Promos judged by the finder's model | 0 | 0 |
| Promos that could not be judged | not tracked | 0 |
| Automatic repairs | none (rejected instead) | 14 length repairs (7 too short, 7 too long) + 3 other fixes |

Baseline comparison, best promo per episode from each method, same judge (50 episodes in the re-run):

| Dimension | Archived: mean diff, AI better / baseline better, p | Re-run |
|---|---|---|
| cliffhanger | +0.27, 20 / 7, **0.019** | **+0.41, 25 / 7, 0.002** |
| hook | +0.11, 17 / 8, 0.108 | 0.00, 9 / 9, 1.0 |
| clarity | +0.10, 17 / 10, 0.248 | +0.06, 19 / 13, 0.377 |
| overall | 31 / 18, 0.085 | 30 / 20, 0.203 |

Leniency: 76.9% of averaged judge dimension scores are 4 or 5 (72.2% archived).

Judge reliability (each clip judged twice; the 72 AI promos, no clip had fewer than two repeats):

| Measure | Archived | Re-run |
|---|---|---|
| Identical score per dimension | 79% | 77% |
| Within 1 point | 99% | 100% |
| Clips identical on all three dimensions | 51.6% | 48.6% |
| Rank correlation between the two passes | 0.90 | 0.80 (my computation, on the mean of the three scores; the archived figure may have been computed slightly differently) |
| Top-15 overlap between the two passes | 11/15 | 11/15 |

Reading: the judge is about as steady as before on scores, and a little less steady on ordering. Not re-done for the
re-run: the blinded second-model check (24 clips) and the human gold set.

What this says:
- The cliffhanger result holds and is stronger. Hook and clarity still show no clear gain over the baseline, and the
  overall win is still not statistically proven.
- **The same finder model gave a different shortlist.** Top-5 overlap with the archived run is 2/5, top-10 4/10 and
  top-15 6/15. The re-run's #1 is E32-P1 (archived #3); E31-P2, the archived #1, was not proposed this time, and E31-P1
  (same episode, another clip) is #6. Only E01-P1 and E32-P1 are in both top fives. So the ranking varies between runs
  of one model, not only between models: treat it as a shortlist.
- The comparison is still judged by one model on one show, and no human has rated a clip.

Re-run top five: E32-P1, E01-P1, E02-P1, E45-P1, E15-P1.


## What it does not do

Judge from video or audio; know the audience; guarantee a promo performs. It finds candidates and explains why;
an editor decides. The all-qwen run adds a second warning: when the finder and judge are the same model, the
scores are **self-graded**, so use a different judge for a clean evaluation.
