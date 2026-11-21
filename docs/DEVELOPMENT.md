# Development

How to set up, change and test KuKuAds. For what each stage does see [ARCHITECTURE.md](ARCHITECTURE.md); for the
CLI and HTTP interface see [API.md](API.md).

## Setup

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env          # only the keys for the providers you use
python run.py --selftest      # offline pipeline check
python -m pytest -q           # 33 tests; no network or API key needed
```

`run.py` adds `src/` to the path, so nothing needs installing. `pyproject.toml` also sets `pythonpath = ["src"]` for pytest.
`make test`, `make selftest`, `make run SCRIPTS=...` and `make app` wrap the same commands.

## Layout

| Path | What |
|---|---|
| `src/kukuads/pipeline/` | `parse`, `find`, `prompts`, `validate`, `judge`, `rank`, `baseline`, `report`, `runner`, `models` |
| `src/kukuads/llm/` | `LLMClient` (pin, fallback, cache, log) and the two provider adapters |
| `src/kukuads/ui/` | Streamlit app: `state.py` (settings, runs), `settings.py` (dialog), `components.py` (promo card, side panel), `pages/` (one module per tab) |
| `src/kukuads/health.py`, `selftest.py` | backend check and ping; offline self-test and demo-run writer |
| `configs/config.yaml` | providers, pinned models, promo rules, ranking weights |
| `tests/` | parser, validator, ranker, LLM client, self-test, backend check |
| `eval/reports/` | the long evidence reports |

## Common changes

- **Swap a model:** edit `stages` in `configs/config.yaml`, or pass `--provider/--model` (see [API.md](API.md)).
- **Add a provider:** add an entry under `providers`; `openai_compatible` and `anthropic` are the only adapter types.
- **Tune a prompt:** all prompts are in `pipeline/prompts.py`. Re-run with `--no-cache`, or the cache returns old replies.
- **Change promo rules or ranking weights:** `promo` and `ranking` in `configs/config.yaml`; no code change needed.
- **New show:** `python run.py --scripts <folder>` (or upload in the app); the parser is forgiving about case, spacing and missing headers.

## Rules that matter

- **Never change the cache key casually** (`LLMClient._cache_key`). Add new fields only when set, so existing cache
  entries stay valid (mistake #6 below).
- **Never let a stage fall back silently.** Every call logs `served_by`; the report counts self-graded clips.
- **Code owns timestamps.** The LLM returns beat IDs only; do not let a prompt change ask it for times.

## Tests

```bash
python -m pytest -q
python -m pytest tests/test_validate.py -q
```

Covered: parser, validator (edge cases and length repair), ranker, LLM client, judge failure handling and the runner, self-test, backend check, the app (tabs, demo run, session key). Not covered directly: `find`, `baseline`, `report` (the app test exercises `report`).

## Mistakes log: what went wrong and how it was solved

All real; evidence is in the git history and `outputs/` runs (kept as `full-run-v1…v3`).

| # | What went wrong | How I found it | Fix |
|---|---|---|---|
| 1 | **The finder graded its own clips.** The judge model was rate-limited after 11 calls and the router silently fell back to the finder model, which served 108 of 128 judge calls | `llm_calls.jsonl` records the model that actually answered (`served_by`), and it showed the finder's name on judge calls | On rate limit, wait for the reset (`retryAtMs` / "reset ~Ns" / Retry-After) and keep the pinned model; removed the finder from the judge chain; report now prints how many promos were self-graded |
| 2 | **Daily quota hit on both judges**, so I let the router pick any model. 20 different judges scored the clips: weak agreement (hook correlation 0.19, top-15 overlap 6/15), average score jumped 2.95 → 4.47 | Compared the same clips across runs | Moved to one self-hosted judge (Ollama) for all clips. Old runs kept as evidence of why |
| 3 | **Judge couldn't see the action**, so a strong opening scored clarity 2 | Read the judge's "confusing" text for Ep 1 | Include camera/action lines in the judge's clip transcript |
| 4 | **Scores clustered at 2–3** with a free-form 1–5 scale | Score histogram | Anchored definitions per score. Side effect: leniency (79% 4–5), still open |
| 5 | **Self-hosted model took ~90 s per call** (it is a "thinking" model) | Latency column in the report | `reasoning_effort: none` via `extra_body` → ~12 s per call with the same quality; full run 51 min |
| 6 | **Changed the cache key and invalidated every cached finder result.** The finder then hit a 429 and the smoke run failed | Smoke run failed right after the change | Made the key backward-compatible: new fields are added only when set. Lesson: never change a cache key casually |
| 7 | **Report counted rate-limit wait records as LLM calls**, inflating call counts | Counts didn't match the run | Separate columns for calls, waits and failed attempts |
| 8 | **Report said "mixed judges" even with one judge** | Reading the regenerated report | Wording is now conditional on the number of judge models |
| 9 | **CLI crashed with `UnicodeEncodeError`** on a Windows cp1252 console | First full-run print | Reconfigure stdout/stderr to UTF-8 |
| 10 | **`git push` / `curl` fail on this Windows machine** (schannel certificate-revocation check) | Error `CRYPT_E_REVOCATION_OFFLINE` | Python's httpx/openai clients are unaffected; push needs the user's terminal (`http.schannelCheckRevoke` setting). Unresolved on my side |
| 11 | **Validator rejected a good episode instead of repairing it** (Ep 42: 17.4 s after the start moved to the hook) | Audit found one episode with no promo although the best scene was in the funnel | Fixed: a too-short clip is repaired (start back to a strong beat, else end extended past the cliffhanger, else start back to a weaker hook) before it is rejected; a too-long clip falls back to a weaker later hook. Replay of all 10 archived length rejections: all now valid |
| 12 | **I almost trusted the first ranking** before measuring whether the judge was stable | Repeated each judgement twice and computed rank correlation (0.90) and top-15 overlap (11/15) | Judge stability is now part of the report |

| 13 | **Groq free tier ran out mid-run**: about 200,000 tokens per day per key and model, so a 50-episode run needs more than one key (finder stopped at episode 26; the judge hit it on the baseline clips) | `429 ... tokens per day` in `llm_calls.jsonl`; the report showed 22 promos as failed | Swap to a key with quota and run the same command again: finished calls come from the cache, only the missing ones are sent. The pipeline marks unjudged promos instead of scoring them 0 |

## What I'd tell an interviewer
The most important lesson: a fallback that works *silently* is worse than a failure, because it quietly breaks the
experiment. So the client logs which model really answered, and the report surfaces it.
