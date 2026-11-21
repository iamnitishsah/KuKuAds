# Architecture

## One-line summary
Parse the screenplay into addressable beats (code) → an LLM picks beat IDs for candidate promos (AI) → code turns IDs into
timestamps and enforces the rules (code) → a separate "cold viewer" LLM scores each clip (AI) → code ranks (code).

## Pipeline

| # | Stage | Done by | Input → Output | Why this owner |
|---|---|---|---|---|
| 1 | Parse | code | `.txt` screenplay → beats with stable IDs (`E01-B008`), type, speaker, start/end, intensity | Format is regular; code is exact and free. 3,727 beats parsed, 0 mismatches |
| 2 | Find | LLM (1 call/episode) | episode beats → candidate promos as **beat IDs only** | Needs story judgement. IDs only, so the model cannot invent a timestamp |
| 3 | Validate | code | candidates → timestamps; enforce 20–60 s, hook within 3 s, end on cliffhanger, never cut a spoken line, snap to shot edges | Rules are checkable; every fix or rejection is logged in `notes` |
| 4 | Judge | a *different* LLM | clip transcript only (dialogue + shot descriptions) → hook / cliffhanger / clarity, anchored 1–5 | Simulates a viewer who has never seen the show |
| 5 | Rank | code | judge scores + screenplay intensity + early-episode bonus | Transparent, tunable weights in `configs/config.yaml` |
| – | Baseline | code | rules-only sliding window, judged by the same judge | The control: does the LLM finder add anything? |

Ranking: hook 0.3, cliffhanger 0.3, clarity 0.3, intensity 0.1, +0.05 for episodes ≤ 5 (good entry points),
max one promo per episode in the top 15 (diversity).

## Components

| Component | Path (`src/kukuads/`) | Role |
|---|---|---|
| Pipeline stages | `pipeline/` | parse, find, validate, judge, rank, baseline, report |
| Orchestrator | `pipeline/runner.py` | runs the stages in order and writes every output file; used by the CLI and the API |
| LLM client | `llm/client.py` | pinned model per stage, fallback list, disk cache, call log, rate-limit wait |
| Provider adapters | `llm/providers.py` | `openai_compatible` and `anthropic` |
| CLI | `run.py` | see [API.md](API.md); `app.py` launches the app |
| App | `ui.py`, `health.py`, `selftest.py` | Streamlit app (status, run, results) over the same orchestrator; backend check; offline self-test |
| Config | `configs/config.yaml` | models, rules, weights |

## Data flow

```
data/raw/*.txt ─ parse ─► Episode[Beat] ─ find (LLM) ─► beat-ID candidates ─ validate ─► Promo (timestamps, notes)
                                                                                   │
                                          baseline (rules) ─────────────────────────┤
                                                                                   ▼
                                                         judge (LLM, clip transcript only) ─ rank ─► report + CSV/JSON
```

Related docs: [DATASET.md](DATASET.md) (input format and signals), [API.md](API.md) (interfaces and
output schema), [DEVELOPMENT.md](DEVELOPMENT.md), [findings.md](findings.md).

## Where a human stays in the loop
The tool outputs a ranked list with reasons and flags; an editor approves what gets posted. Nothing is auto-published.
Planned: a labelled gold set (see [findings.md](findings.md)) to check the judge against human taste.

## Swapping the model (the interviewer will ask)
All LLM calls go through `llm/client.py` (`LLMClient`). Two adapters in `llm/providers.py`:
- `openai_compatible`: OpenAI, Gemini (OpenAI endpoint), Groq, a local router, Ollama
- `anthropic`

`configs/config.yaml` pins **one model per stage** with an explicit fallback list. To change: edit the stage in `configs/config.yaml`, or
`python run.py --provider anthropic --model <id>`, or `--judge-provider/--judge-model` for the judge only.
The client also provides: robust JSON extraction, disk cache (re-runs are free), a JSONL log of every call (which model
really answered, tokens, latency), and wait-and-retry on rate limits.

## Cost and scale (measured on this show)
- Dataset: 50 episodes ≈ 169k tokens (≈ 3.4k per episode).
- One full run: finder 50 calls (127k in / 84k out) + judge 256 calls (273k in / 33k out) ≈ **517k tokens**.
- Wall time: ~51 min on a self-hosted 27B model (2 judge passes × 128 clips).
- Scales linearly with episodes: finder cost ∝ episodes; judge cost ∝ promos. Cache makes re-runs free.
- For every show: run per show, same config. Finder prompt carries a short "previously" and premise per episode, so no
  per-show tuning is needed. A paid stronger model would mainly improve the finder and judge, not the pipeline.

## Known limits
Text only (no video/audio); depends on the screenplay's timestamps being accurate; the judge is an LLM and lenient
(see [findings.md](findings.md)).
