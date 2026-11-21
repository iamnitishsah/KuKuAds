# KuKuAds

Finds the best **20–60 second promo clips** in a microdrama's episode screenplays, for TikTok, Instagram and YouTube
Shorts. A good promo opens on a **hook** in the first 3 seconds, ends on a **cliffhanger**, and makes sense to someone
who has never seen the show. For each promo you get the episode, the start and end time of every segment, the hook,
the cliffhanger, one line on why it works, and a rank.

Built for the Kuku AI Generalist assignment, Problem 1 (Find the Promos).

**Result on the 50-episode show:** 78 valid promos, at least one in 49 of 50 episodes; every promo is 20–60 s with
the hook inside 3 s. The AI's real contribution is *where to cut*: it picked a better cliffhanger than a rules-only
baseline in 20 of 49 episodes (worse in 7). On hook and clarity it is not clearly better. There is no human-labelled
check yet. Details and limits: [docs/findings.md](docs/findings.md).

## How it works

```
screenplay ─► 1 PARSE     (code)  split into timed "beats" with IDs like E01-B008
           ─► 2 FIND      (AI)    per episode, propose promos as beat IDs (never timestamps)
           ─► 3 VALIDATE  (code)  turn IDs into times; enforce 20–60 s, hook ≤ 3 s, cut on the cliffhanger, no cut mid-line
           ─► 4 JUDGE     (AI)    a different model reads only the clip, like a stranger, and scores it 1–5
           ─► 5 RANK      (code)  weighted scores, one promo per episode in the top 15
   baseline: a rules-only version of the same task, scored by the same judge, as the control
```

Code handles structure and timing, so timestamps cannot be invented. The AI handles judgment. The judge is never the
same model as the finder, and every call logs which model actually answered.

## Run it

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env            # defaults need GROQ_API_KEY and GEMINI_API_KEY

python run.py --selftest        # offline check that the code works (no key, no data)
python -m pytest -q             # 22 tests
streamlit run app.py            # the app (tabs: Overview, Find promos, How it works, Evaluation, Status)

# command line, real run (screenplays go in data/raw/, which is gitignored)
python run.py --scripts "data/raw/<show folder>" --episodes 1-3        # models from configs/config.yaml
```

The app's **Status** tab answers "is it running?": a self-test button and a table of which configured models are
reachable; **Settings** has your own API key (memory only) and a real **Test connection**; **Try the demo** shows a
full result with no key and no data. Every flag and the output format: [docs/API.md](docs/API.md).

Each run writes `outputs/run-<time>/` with `report.md` (start here), `promos_ranked.csv/json`, `candidates.json`,
`baseline.json` and `llm_calls.jsonl`.

## Docs

| File | What it covers |
|---|---|
| [ARCHITECTURE.md](docs/ARCHITECTURE.md) | stages, who owns each, components, cost |
| [API.md](docs/API.md) | CLI flags, the Streamlit app, output format |
| [DATASET.md](docs/DATASET.md) | screenplay format, beats, signals, judge rubric |
| [DEVELOPMENT.md](docs/DEVELOPMENT.md) | setup, how to change things, mistakes log |
| [findings.md](docs/findings.md) | results, how they were checked, where it fails |
| [AI_LOG.md](docs/AI_LOG.md) | AI tools used and where they got it wrong |
| [ROADMAP.md](docs/ROADMAP.md) | open fixes |
| [SOURCES.md](docs/SOURCES.md) | input data, models, references |
| [DEPLOYMENT.md](docs/DEPLOYMENT.md) | not done yet (empty) |

Longer evidence (real prompts and outputs per stage; a second-LLM check): [eval/reports/](eval/reports/).

## Layout

```
configs/config.yaml     models, rules, ranking weights
src/kukuads/        pipeline/ (the 5 stages + report), llm/ (model client), ui/ (Streamlit app), selftest.py, health.py
run.py  app.py          command line and Streamlit entry points
data/raw/               screenplays (confidential, gitignored)
outputs/                one folder per run (gitignored except its README)
docs/  eval/reports/    documentation and evidence
submission/             assignment brief and solution doc
tests/
```

## Limits

- Works from the screenplay, not the video: it assumes the final edit follows the script's timings.
- The judge is an AI, so its scores are a proxy for real viewer behaviour, not a replacement for A/B tests.
- Promos stay within one episode; later episodes are harder for a stranger to follow.
- Known open issues (one clip 0.3 s over the cap is rejected, a few cuts land 0.1–0.2 s inside a line, no brand-safety
  check): [docs/ROADMAP.md](docs/ROADMAP.md).
- The screenplays are Kuku's confidential content and are not in this repository.
