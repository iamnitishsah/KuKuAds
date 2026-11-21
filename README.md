# KuKuAds

Reads a microdrama's episode screenplays and finds the best **20–60 second promos** for TikTok, Instagram and
YouTube Shorts: clips that open on a **hook** in the first 3 seconds, end on a **cliffhanger**, and **make sense
to someone who has never seen the show**. For each promo it gives the episode, the start and end timestamps of
every segment, the hook, the cliffhanger, one line on why it works, and a rank.

Built for the Kuku AI Generalist assignment (Problem 1: Find the Promos). The Python package is named `promofinder`.

## How it works

```
screenplays ─► 1. PARSE (code)     beats with stable IDs, speaker, tone tags, start/end, cheap signals
            ─► 2. FIND (LLM)       one call per episode; proposes promos as BEAT IDs, never timestamps
            ─► 3. VALIDATE (code)  IDs → timestamps; 20–60 s; hook within 3 s; ends on the cliffhanger;
                                   snaps to shot edges; never cuts a spoken line; logs every fix/rejection
            ─► 4. JUDGE (LLM)      a different model sees ONLY the clip transcript, like a stranger,
                                   and scores hook / cliffhanger / clarity (1–5), twice, averaged
            ─► 5. RANK (code)      weighted judge scores + intensity + early-episode bonus, one per episode in the top list
   + BASELINE (code, no LLM)       sliding-window rules, judged by the same judge, as the control
```

Code does structure and timing; the LLM does judgment. The judge is a different model from the finder, every call logs
which model actually answered, and every LLM reply is cached so re-runs are free.

## Quickstart

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env                  # only the keys you use
python -m pytest -q                   # 15 tests, no network needed

# episodes 1-3 with one hosted model for every stage
python run.py --scripts "data/raw/<show folder>" --episodes 1-3 \
              --provider anthropic --model claude-sonnet-5-5
```

Each run writes `outputs/run-<timestamp>/` with `report.md`, `promos_ranked.csv/json`, `candidates.json`,
`baseline.json`, `llm_calls.jsonl` and `run_meta.json`. Start with `report.md`.

More commands (full show, swap the model or only the judge, new show, web app, HTTP API): [docs/API.md](docs/API.md).
`make test`, `make run SCRIPTS=...` and `make serve` are shortcuts.

## Evaluating

- **Tests:** `python -m pytest -q` (parser, validator, ranker, LLM client).
- **Every run self-evaluates in `report.md`:** top list, validation funnel, judge models and how many clips the finder
  graded itself, LLM vs baseline with sign tests, clarity by episode range, worst picks, and token/latency usage.
- **Independent checks** (run-to-run, blinded second-LLM check) and their results: [docs/findings.md](docs/findings.md).

## Docs

| File | What it covers |
|---|---|
| [ARCHITECTURE.md](docs/ARCHITECTURE.md) | stages, who owns each (code or LLM), components, data flow, scale and cost |
| [API.md](docs/API.md) | CLI flags, HTTP endpoints, output schema |
| [DATASET.md](docs/DATASET.md) | screenplay format, beat signals, promo patterns, judge rubric |
| [DEVELOPMENT.md](docs/DEVELOPMENT.md) | setup, how to change things, rules that matter, mistakes log |
| [findings.md](docs/findings.md) | what we'd post first, how it was evaluated, where it picks badly |
| [AI_LOG.md](docs/AI_LOG.md) | AI tools used and where they got it wrong |
| [ROADMAP.md](docs/ROADMAP.md) | open fixes and next steps |
| [SOURCES.md](docs/SOURCES.md) | input data, models, references |
| [DEPLOYMENT.md](docs/DEPLOYMENT.md) | not done yet (empty) |

Long evidence reports (every stage with real prompts and outputs; the blinded second-LLM check) are in
[`eval/reports/`](eval/reports/).

## Repository layout

```
.
├── configs/config.yaml      models, providers, promo rules, ranking weights
├── src/promofinder/
│   ├── pipeline/            parse, find, validate, judge, rank, baseline, report, runner, prompts
│   ├── llm/                 LLMClient (pin, fallback, cache, logging) and provider adapters
│   └── api/                 FastAPI app + static UI
├── run.py                   CLI entry point (no install needed)
├── data/raw/                screenplays (confidential, gitignored)
├── eval/                    llm2/ scripts, reports/ evidence
├── outputs/                 one folder per run (gitignored except its README)
├── docs/                    the nine docs above
├── submission/              assignment brief and the submitted solution PDF
├── tests/
└── Makefile  pyproject.toml  requirements.txt
```

## Limits

- Works from screenplays, not the final video: timings assume the edit follows the script.
- The judge is an LLM; its scores are a proxy for viewer behaviour, not a replacement for A/B tests.
- Multi-segment promos stay within one episode; later episodes are less clear to strangers.
- Open issues (a clip 0.3 s over the cap rejected, cuts 0.1–0.2 s inside a line, no brand-safety check): [docs/findings.md](docs/findings.md).
- Screenplays are confidential and are not part of this repository.
