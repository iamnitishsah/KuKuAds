# Findings

## What we'd post first

**Archived run** (`gpt-oss-120b` finder + `qwen3.8:27b` judge): **E31-P2, E43-P1, E32-P1, E01-P1, E13-P1**
(then E02-P1, E33-P1, E45-P1, E16-P1, E18-P1 …).

**All-qwen run** (same judge, `qwen3.8:27b` finder): **E31-P2, E01-P1, E15-P1, E02-P1, E42-P1**
(then E10-P1, E05-P2, E16-P1, E18-P1, E32-P1 …).

- **E31-P2 is the stable #1** in both runs and in the blinded LLM-2 check. It is the one pick that survives every configuration.
- The exact order is **finder-dependent**: top-5 overlap is **2/5**, top-10 **6/10**, top-15 **8/15**.
- Pattern: a cruel or shocking line, then a threat, accusation or betrayal left hanging. Two of the top five fit that wording exactly; the other three are a looser "unresolved danger or betrayal". See the detailed report.

**Run-to-run check:** changing the finder model changes 7 of the 15 top-list entries even with the same judge. Treat the ranking as a shortlist, not a fixed verdict.

## Where it picks badly (real, from the runs)

| Issue | Detail | Status |
|---|---|---|
| Missed episode | **Model-dependent.** The archived `gpt-oss` run misses **Ep 42** (E42-P1 rejected at 17.4 s after the hook move). The all-qwen run covers Ep 42 (E42-P1 59.9 s, #5) but misses **Ep 33**: E33-P1 started at 100.3 s, the start moved to B064, leaving **60.3 s** — 0.3 s over the 60 s cap — and was rejected. The stable issue is the hard 60 s boundary, not one episode. | open, fix planned |
| Cut edges | **E04-P2** ends 0.1 s inside a spoken line; **E32-P1** starts 0.2 s inside one. **E01-P1** does include Gerald's "I changed my mind."; Clarissa's sting ("People change their minds, sister.") starts 3.5 s after the cut. **E47-P1** does not end mid-sentence — the complete line is B067 and the next line is omitted whole. | open, fix planned |
| Lenient judge | **72.2%** of the archived averaged LLM dimension scores are ≥4; **75.1%** in the all-qwen run. The often-quoted **79%** only appears when pooling raw repeats across all 128 clips, including the baseline. | open, fix planned (pairwise) |
| Self-grading | The archived run has **0/78** LLM promos graded by the finder model. The all-qwen run has **83/83** — the same model found and judged every promo, so its scores may be generous and are not independent. | known limit |
| Brand safety | Ep 31/32 are real and high-ranked: E31-P2 is **#1**, E32-P1 is **#3**, both with a red-hot iron inches from an eye (threat, no contact). Ep 39 is **#47** and the guard is knocked **unconscious**, not killed. Ep 50 is **#63**: the intimate scene is real, but the promo is near the bottom. | open, no check yet |
| Low-clarity picks | E49-P1 (2.5), then E06-P2, E17-P1, E19-P3, E07-P2, E20-P1, E09-P1, E14-P1, E33-P3, E37-P3 (all 3.0). Every one is low-ranked (ranks 56–78); none is a top-15 pick. | known limit |
| Useless field | `context_needed` came back `"low"` for **84/84** proposals. Zero variance, no signal; `rank.py` never reads it. | ignored in ranking |
| Late-episode skew | **Not supported** by the delivered top 15: mean episode 23.2 vs 23.97 for all promos; only the top 3 are late. Removing the 0.05 early-episode bonus changes no top-15 membership, only the order. | not supported |

## What it does not do

Judge from video or audio; know the audience; guarantee a promo performs. It finds candidates and explains why;
an editor decides. The all-qwen run adds a second warning: when the finder and judge are the same model, the
scores are **self-graded**, so use a different judge for a clean evaluation.
