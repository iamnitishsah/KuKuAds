# CLI and HTTP API

Both interfaces run the same function, `pipeline.runner.run_pipeline`, so they behave identically.

## CLI: `run.py`

```bash
python run.py --scripts "data/raw/<show folder>"                                   # full show
python run.py --scripts DIR --episodes 1-5,12                                      # subset
python run.py --scripts DIR --provider anthropic --model claude-sonnet-5-5         # one model for every stage
python run.py --scripts DIR --judge-provider openai --judge-model <id>             # swap only the judge
python run.py --scripts DIR --out outputs/another-show                             # choose the output folder
```

| Flag | Meaning |
|---|---|
| `--scripts DIR` | folder of episode `.txt` files (required) |
| `--out DIR` | output folder (default `outputs/run-<timestamp>`) |
| `--episodes SPEC` | e.g. `1-5,12` |
| `--config FILE` | default `configs/config.yaml` |
| `--provider P --model M` | pin all stages to one model (must be given together) |
| `--judge-provider P --judge-model M` | pin only the judge |
| `--no-judge` | skip the judge (no ranking scores) |
| `--no-baseline` | skip the rules-only baseline |
| `--no-cache` | ignore cached LLM replies |

Providers defined in `configs/config.yaml`: `freellm`, `openai`, `gemini`, `groq`, `anthropic`, `ollama`. Keys and URLs
come from `.env` (see `.env.example`).

## HTTP API

```bash
PYTHONPATH=src uvicorn promofinder.api.main:app --port 8000      # or: make serve
```

Jobs are kept in memory and there is no authentication: for local use.

| Method and path | Purpose |
|---|---|
| `GET /` | web UI |
| `GET /api/health` | liveness |
| `GET /api/config` | pinned models per stage, provider types, promo rules (never keys) |
| `POST /api/jobs` | start a run (form fields below); returns `{run, status}` |
| `GET /api/jobs/{run}` | status, stage, progress counts, log tail |
| `GET /api/runs` | finished runs under `outputs/` |
| `GET /api/runs/{run}/promos?top_only=true` | ranked promos (JSON) |
| `GET /api/runs/{run}/report` | `report.md` as text |
| `GET /api/runs/{run}/files/{name}` | download any output file |

`POST /api/jobs` form fields: `files` (one or more `.txt`) **or** `scripts_dir`; optional `episodes`, `provider`,
`model` (together), `judge_provider`, `judge_model`, `judge` (bool, default true).

```bash
curl -F "files=@episode-001.txt" -F "episodes=1" http://127.0.0.1:8000/api/jobs
curl http://127.0.0.1:8000/api/jobs/<run>
curl "http://127.0.0.1:8000/api/runs/<run>/promos?top_only=true"
```

## Output schema (`promos_ranked.json`)

One object per valid promo, in posting order.

| Field | Meaning |
|---|---|
| `rank`, `in_top_list` | position; true for the top list (one promo per episode) |
| `promo_id` | e.g. `E31-P2` (`E<episode>-P<n>`; baseline uses `-B<n>`) |
| `segments[]` | `episode`, `start`, `end` (seconds), `start_beat`, `end_beat`, in story order |
| `duration_s`, `episodes` | total length; episodes covered |
| `hook`, `cliffhanger`, `why`, `patterns` | the finder's explanation |
| `hook_beat`, `cliffhanger_beat` | beat IDs the validator enforced |
| `judge` | `hook`, `cliffhanger`, `clarity` (1-5, averaged), `repeats`, `spread`, `summary`, `confusing`, `want_next`, `model`, `served_by`, `fallback` |
| `scores` | `hook`, `cliffhanger`, `clarity`, `intensity` (0-1), `entry_bonus`, `final` |
| `notes` | every automatic fix the validator applied |
| `finder_model` | model that actually answered the finder call |

`promos_ranked.csv` has the same content flattened, one row per promo. Other files per run: `report.md`,
`candidates.json` (includes rejected promos with the reason), `baseline.json`, `beats.json`, `llm_calls.jsonl`,
`run_meta.json`.
