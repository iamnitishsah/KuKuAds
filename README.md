# Promo Finder

Reads a microdrama's episode screenplays and finds the best **20–60 second promos** for TikTok, Instagram and
YouTube Shorts: clips that open on a **hook** in the first 3 seconds, end on a **cliffhanger**, and **make sense
to someone who has never seen the show**. For each promo it gives the episode, the start and end timestamps of
every segment, the hook, the cliffhanger, one line on why it works, and a rank.

Built for the Kuku AI Generalist assignment (Problem 1: Find the Promos).

## Contents
1. [Quickstart](#quickstart)
2. [Pipeline](#pipeline)
3. [Running it](#running-it)
4. [Evaluating it](#evaluating-it)
5. [Outputs](#outputs)
6. [Web app / API](#web-app--api)
7. [Configuration](#configuration)
8. [Repository layout](#repository-layout)
9. [Limits](#limits)

## Quickstart

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env                 # fill in only the keys you use
python -m pytest -q                  # 15 tests, no network or API key needed

# smallest real run: episodes 1-3 with a single hosted model for every stage
python run.py --scripts "data/raw/<show folder>" --episodes 1-3 \
              --provider anthropic --model claude-sonnet-5-5
open outputs/run-*/report.md         # newest run
```

`make test`, `make run SCRIPTS=...` and `make serve` are shortcuts for the same commands.
The screenplays are confidential and live in `data/raw/` (gitignored). One `.txt` file per episode.

## Pipeline

```
screenplays ─► 1. PARSE (code)     beats with stable IDs, speaker, tone tags, start/end, cheap signals
            ─► 2. FIND (LLM)       one call per episode; proposes promos as BEAT IDs, never timestamps
            ─► 3. VALIDATE (code)  IDs → timestamps; 20–60 s; hook within 3 s; ends on the cliffhanger;
                                   snaps to shot edges; never cuts a spoken line; logs every fix/rejection
            ─► 4. JUDGE (LLM)      a different model sees ONLY the clip transcript, like a stranger
                                   scrolling, and scores hook / cliffhanger / clarity (1–5), twice, averaged
            ─► 5. RANK (code)      weighted judge scores + screenplay intensity + early-episode bonus,
                                   max one promo per episode in the top list
   + BASELINE (code, no LLM)       sliding-window rules, judged by the same judge, as the control
            ─► REPORT              report.md, promos_ranked.csv/json, candidates, call log
```

| # | Stage | Module (`src/promofinder/`) | Owner | Output |
|---|---|---|---|---|
| 1 | Parse | `pipeline/parse.py` | code | `Episode` / `Beat` objects (`beats.json`) |
| 2 | Find | `pipeline/find.py`, `prompts.py` | LLM | raw candidate promos (beat IDs) |
| 3 | Validate | `pipeline/validate.py` | code | `Promo` with timestamps, status `valid`/`rejected`, `notes` |
| 4 | Judge | `pipeline/judge.py` | LLM (a different model) | hook / cliffhanger / clarity, repeat spread |
| 5 | Rank | `pipeline/rank.py` | code | ranked rows, `in_top_list` flag |
| – | Baseline | `pipeline/baseline.py` | code | rules-only promos for comparison |
| – | Report | `pipeline/report.py` | code | `report.md` |
| – | Orchestration | `pipeline/runner.py` | code | used by both the CLI and the API |

**Design choices**

- **Code does structure and timing, the LLM does judgment.** The model answers with beat IDs; code computes every
  timestamp, so timestamps cannot be hallucinated.
- **Cold-viewer judge.** "Makes sense on its own" is measured by a model that gets no series context.
  The judge is a different model from the finder, so it does not grade its own picks.
- **Pinned models.** Each stage uses one named model; fallbacks are used only when a call fails, and every call
  logs which model actually answered (`llm_calls.jsonl`).
- **Resumable and cheap to re-run.** Every LLM reply is cached in `.cache/llm`; re-running the same command is free.
- Related work: ByteDance/USTC's HIVE (arXiv 2507.02790) cuts short dramas into ads from video. Screenplays already
  contain the dialogue, speakers and scenes HIVE has to recover, so this tool starts at the highlight step and adds
  length control and a standalone-clarity check.

More detail: [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md).

## Running it

Run from the repo root. `run.py` needs no install; `--scripts` is the folder of episode `.txt` files.

```bash
# full show, models from configs/config.yaml
python run.py --scripts "data/raw/<show folder>"

# a subset of episodes
python run.py --scripts "data/raw/<show folder>" --episodes 1-5,12

# swap the model for EVERY stage (what to do in the interview)
python run.py --scripts DIR --provider anthropic --model claude-sonnet-5-5
python run.py --scripts DIR --provider openai    --model <model-id>
python run.py --scripts DIR --provider gemini    --model <model-id>

# swap only the judge (keep it different from the finder)
python run.py --scripts DIR --judge-provider openai --judge-model <model-id>

# a new show: same command, different folder
python run.py --scripts "path/to/another-show" --out outputs/another-show
```

| Flag | Meaning |
|---|---|
| `--scripts DIR` | folder of screenplays (required) |
| `--out DIR` | output folder (default `outputs/run-<timestamp>`) |
| `--episodes SPEC` | e.g. `1-5,12` |
| `--config FILE` | default `configs/config.yaml` |
| `--provider P --model M` | pin all stages to one model (go together) |
| `--judge-provider P --judge-model M` | pin only the judge |
| `--no-judge` | skip the judge (finder + validator only; no ranking scores) |
| `--no-baseline` | skip the rules-only baseline |
| `--no-cache` | ignore cached LLM replies and call the models again |

Providers available out of the box: `freellm` (local OpenAI-compatible router), `openai`, `gemini`, `groq`,
`anthropic`, `ollama`. Add more in `configs/config.yaml`; two adapter types (`openai_compatible`, `anthropic`)
cover practically everything. Keys go in `.env` (see `.env.example`).

If the judge is rate-limited the client waits for the reset and keeps the pinned model rather than silently
switching. If the run stops, run the same command again: finished calls come from the cache.

## Evaluating it

Evaluation has three layers, from cheapest to most expensive. Results from the archived run are in
[`docs/EVALUATION.md`](docs/EVALUATION.md) and [`docs/findings.md`](docs/findings.md).

**1. Unit tests (code correctness, free)**

```bash
python -m pytest -q                      # all tests
python -m pytest tests/test_validate.py  # one module
```

Covers the parser, validator, ranker and the LLM client (fallback, rate-limit wait, cache, JSON repair).

**2. Every run self-evaluates (`report.md`)**

Each run writes `outputs/<run>/report.md`. Read it in this order:

| Section | Answers |
|---|---|
| Post these first | the top-15 list with hook, cliffhanger, why, judge scores |
| Validation funnel | proposed → valid → rejected, with reasons and automatic fixes |
| Quality (cold-viewer judge) | judge models used, **how many clips the finder graded itself**, judge consistency between repeats |
| LLM vs rules-only baseline | best promo per episode from each method, mean differences, sign tests |
| Standalone clarity by episode range | later episodes depend on earlier plot |
| Where it picks badly | lowest-clarity picks and what confused the judge, sample rejections |
| LLM usage | calls, cache hits, fallbacks, rate-limit waits, tokens, latency per stage |

Checks to run on any new output: every promo is 20–60 s, `hook` is within 3 s of the start, no clip starts or
ends inside a spoken line (compare `segments` against `beats.json`), and the "graded by the finder's own model"
count is 0. `candidates.json` keeps rejected promos with the reason, and `llm_calls.jsonl` shows which model
actually answered each call.

**3. Independent checks (manual, one-off)**

- **Run-to-run / finder sensitivity:** run twice with different finders and compare `promos_ranked.json`
  (top-N overlap). See `docs/EVALUATION.md` §2.1 and `docs/findings.md`.
- **Blinded second-LLM check:** `eval/llm2/` builds a packet of anonymised clips, a key, and comparison tables;
  results are in `outputs/eval-llm2/`, write-up in [`docs/LLM2_EVALUATION.md`](docs/LLM2_EVALUATION.md). These
  scripts have hard-coded paths from the machine they were written on; see [`eval/README.md`](eval/README.md).
- **Not done yet:** a human-labelled gold set (about 20 blind clips) to check the judge against a person, and A/B
  tests on real ad performance (3-second hold, click-through).

## Outputs

One folder per run (`outputs/<run>/`). See [`outputs/README.md`](outputs/README.md) for the archived runs.

| File | What |
|---|---|
| `report.md` | Top list, funnel, LLM vs baseline, clarity by episode range, where it picks badly, usage |
| `promos_ranked.csv` / `.json` | Every valid promo in posting order: segments, hook, cliffhanger, why, judge scores, notes |
| `candidates.json` | Everything the finder proposed, including rejected promos and the reason |
| `baseline.json` | The rules-only baseline's promos and scores |
| `beats.json` | Parsed screenplays (contains screenplay text; gitignored) |
| `llm_calls.jsonl` | Every LLM call: model requested, model that answered, tokens, latency, fallback, cache |
| `run_meta.json` | Models, rules, ranking config, wall time, errors |

## Web app / API

Same pipeline behind a small FastAPI app (in-memory job list, no auth: for local use).

```bash
PYTHONPATH=src uvicorn promofinder.api.main:app --port 8000     # or: make serve
# open http://127.0.0.1:8000
```

| Endpoint | |
|---|---|
| `GET /api/health`, `GET /api/config` | liveness; pinned models per stage (never keys) |
| `POST /api/jobs` | upload `.txt` files or give `scripts_dir`; optional `episodes`, `provider`, `model`, `judge_provider`, `judge_model`, `judge`; runs in the background |
| `GET /api/jobs/{run}` | status and progress log |
| `GET /api/runs` | runs under `outputs/` |
| `GET /api/runs/{run}/promos?top_only=true` | ranked promos (JSON) |
| `GET /api/runs/{run}/report`, `/files/{name}` | `report.md` / any output file |

```bash
curl -F "files=@episode-001.txt" -F "episodes=1" http://127.0.0.1:8000/api/jobs
curl http://127.0.0.1:8000/api/jobs/<run>
```

## Configuration

Everything tunable is in [`configs/config.yaml`](configs/config.yaml):

| Key | What |
|---|---|
| `providers` | endpoints and key env vars |
| `stages.finder`, `stages.judge` | pinned model per stage; later entries are failure-only fallbacks |
| `judge_repeats` | judge each clip N times and average (also measures judge consistency) |
| `llm` | `max_tokens`, `temperature`, timeout, retries, rate-limit wait |
| `promo` | `min_s`, `max_s`, `hook_window_s`, `promos_per_episode` |
| `ranking` | weights, early-episode bonus, per-episode cap in the top list, `top_n` |

Ranking: `final = 0.3·hook + 0.3·cliffhanger + 0.3·clarity + 0.1·intensity (+0.05 for episodes ≤ 5)`.

## Repository layout

```
.
├── configs/config.yaml      models, providers, promo rules, ranking weights
├── src/promofinder/
│   ├── pipeline/            parse, find, validate, judge, rank, baseline, report, runner, prompts
│   ├── llm/                 LLMClient (pin, fallback, cache, logging) and provider adapters
│   └── api/                 FastAPI app + static UI
├── run.py                   CLI entry point (adds src/ to the path; no install needed)
├── data/raw/                screenplays (confidential, gitignored)
├── eval/llm2/               one-off scripts behind the blinded LLM-2 check
├── outputs/                 one folder per run, plus eval-llm2/ results
├── docs/                    architecture, evaluation, dev/AI logs, findings, detailed reports
├── submission/              assignment brief, solution doc (solution.md / solution.pdf)
├── tests/
└── Makefile  pyproject.toml  requirements.txt
```

## Limits

- Works from screenplays, not the final video: timings assume the edit follows the script.
- The judge is itself an LLM; its scores are a proxy for real viewer behaviour, not a replacement for A/B tests.
- Cross-episode stitching is not attempted (multi-segment promos stay within one episode).
- Later episodes depend on earlier plot, so their promos are less clear to strangers (see `report.md`).
- Known open issues (clips 0.3 s over the 60 s cap rejected, a few cuts 0.1–0.2 s inside a line, no brand-safety
  check) are listed in `docs/findings.md`.
- Screenplays are confidential and are not part of this repository.
