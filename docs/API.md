# Interfaces

The Streamlit app runs one function, `pipeline.runner.run_pipeline`; the same call works from Python:

```python
from kukuads.pipeline.runner import run_pipeline
run_pipeline(scripts_dir, out_dir, cfg, episodes="1-5,12", do_judge=True, do_baseline=True)
```

`cfg` comes from `configs/config.yaml` (`kukuads.llm.load_config`); `apply_overrides` pins one model for every stage or only the
judge. Providers defined there: `freellm`, `openai`, `gemini`, `groq`, `anthropic`, `ollama`. Keys and URLs come from `.env`
(see `.env.example`). Screenplays go in `data/raw/` (gitignored). Each run writes to `outputs/run-<timestamp>/`.

## Streamlit app

Deployed on Streamlit Community Cloud: https://kukuads.streamlit.app/ (the **Try the demo** button needs no key and no data; a real run needs a key in **Settings** and your own screenplays, which are not on the server).

Run it locally:

```bash
streamlit run app.py        # or: make app
```

Four tabs, plus a **Settings** dialog (button at the top right).

| Tab | What it shows |
|---|---|
| **Overview** | what it helps with, the headline results of the archived run, what to post first, what it will not do |
| **Live demo** | a strip with **Run self-test** (offline, stub model) and **Check models** (is each configured model reachable); then choose screenplays (upload or folder) and episodes and press **Run**, or **Try the demo**. Each promo is a card: a timeline of where the clip sits in its episode, "checked by code" chips (length, hook timing recomputed from the data), hook / cliffhanger / why, judge score bars and final score, the clip transcript the judge saw, and **Why this pick?** (what the cold viewer saw, judge model). Below: run summary (funnel, errors, tokens) and downloads |
| **How it works** | the five stages (code vs AI), how the final score is built, the guardrails, where data and keys live |
| **Evaluation** | measured results as bars: AI vs the rules-only baseline, the re-run with the fixed validator, the second-model check, where it is weak; the full `docs/findings.md` is in an expander |

**Settings:** use the models in `configs/config.yaml` or one model for every stage, a different judge model, your own API
key (kept in this session's memory only, never written to disk), judge and baseline on/off, and **Test connection** (a
real one-token call to the finder and the judge).

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
