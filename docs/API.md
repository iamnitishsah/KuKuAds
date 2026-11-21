# Interfaces

The command line and the Streamlit app run the same function, `pipeline.runner.run_pipeline`, so they behave identically.

## CLI: `run.py`

```bash
python run.py --scripts "data/raw/<show folder>"                                   # full show
python run.py --scripts DIR --episodes 1-5,12                                      # subset
python run.py --scripts DIR --provider anthropic --model claude-sonnet-5-5         # one model for every stage (needs ANTHROPIC_API_KEY)
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
| `--selftest` | offline check, no LLM or key; `--scripts` not needed |
| `--no-judge` | skip the judge (no ranking scores) |
| `--no-baseline` | skip the rules-only baseline |
| `--no-cache` | ignore cached LLM replies |

Providers defined in `configs/config.yaml`: `freellm`, `openai`, `gemini`, `groq`, `anthropic`, `ollama`. Keys and URLs
come from `.env` (see `.env.example`).

## Streamlit app

```bash
streamlit run app.py        # or: make app
```

Five tabs, plus a **Settings** dialog (button at the top right).

| Tab | What it shows |
|---|---|
| **Overview** | what it helps with, how, and what it will not do |
| **Find promos** | choose screenplays (upload or folder) and episodes, **Run**, or **Try the demo**. Each promo is a card: segments, "checked by code" badges (length, hook timing recomputed from the data), hook / cliffhanger / why, judge scores, and **Why this pick?** (automatic fixes, what the cold viewer saw, judge model). Side panel: **Run** (funnel, errors, tokens), **Clip** (the exact transcript the judge saw), **Export** (CSV, JSON, report). **Open an earlier run** browses `outputs/`. |
| **How it works** | the five steps (code vs AI), how invented timestamps are stopped, where data and keys live |
| **Evaluation** | `docs/findings.md`: measured results and failures from the archived run |
| **Status** | **Run self-test** (offline, stub model, no key or data) and a table of which configured models are reachable |

**Settings:** use the models in `configs/config.yaml` or one model for every stage, a different judge model, your own API
key (kept in this session's memory only, never written to disk), judge and baseline on/off, and **Test connection** (a
real one-token call to the finder and the judge).

The same self-test is available without the app: `python run.py --selftest` (exit code 0 means it passed).

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
