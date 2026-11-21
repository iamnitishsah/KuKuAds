# Roadmap

Open items already recorded in the evaluation and findings. Nothing below is built yet. Details and evidence are in
[findings.md](findings.md).

## Validator
- Repair instead of reject for too-short clips (Ep 42: 17.4 s after the start moved to the hook).
- Repair boundary-length clips (Ep 33: 60.3 s after repair, 0.3 s over the 60 s cap).
- Start/end edge checks: E04-P2 ends 0.1 s inside a spoken line; E32-P1 starts 0.2 s inside one.

## Judging and ranking
- Head-to-head comparisons (both orders) for the top ~24 clips, to counter the lenient judge.
- A second, unrelated judge model on the same clips; the finder never judges its own picks.
- A brand-safety flag (E31-P2 is #1 and E32-P1 is #3 and both show a red-hot iron near an eye).

## Evaluation
- A human-labelled gold set (about 20 blind clips) to check the judge against a person.

## Product
- Cross-episode promos (multi-segment promos currently stay within one episode).
- Real-world metric: 3-second hold, completion and click-through from A/B-tested ads.
