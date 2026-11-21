# Roadmap

Open items from the evaluation and findings. Nothing below is built yet. (The validator repair, edge checks and judge-failure handling are done: see findings.md, "Fixed since the archived run".) Details and evidence are in
[findings.md](findings.md).

## Judging and ranking
- Head-to-head comparisons (both orders) for the top ~24 clips, to counter the lenient judge.
- A second, unrelated judge model on the same clips; the finder never judges its own picks.
- A brand-safety flag (E31-P2 is #1 and E32-P1 is #3 and both show a red-hot iron near an eye).

## Evaluation
- A human-labelled gold set (about 20 blind clips) to check the judge against a person.

## Product
- Cross-episode promos (multi-segment promos currently stay within one episode).
- Real-world metric: 3-second hold, completion and click-through from A/B-tested ads.
