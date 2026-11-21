# Outputs

One folder per run; each holds `report.md`, `promos_ranked.csv/json`, `candidates.json`, `baseline.json`,
`run_meta.json`, `llm_calls.jsonl` (and `beats.json`, which embeds screenplay text and is gitignored).

| Folder | What it is |
|---|---|
| `full-run/` | **The archived run cited in the solution doc**: `gpt-oss-120b` finder + `qwen3.8:27b` judge, 50 episodes |
| `full-run-qwen-both/` | All-qwen run (finder and judge are the same model; a coverage check, not independent quality) |
| `full-run-v1-judge-fallback/` | Evidence: router silently fell back, finder graded its own clips |
| `full-run-v2-quota-hit/`, `full-run-v3-mixed-judges/` | Evidence: judge quota hit, then 20 different judges (scores not comparable) |
| `full-run-v3-interrupted/` | Interrupted run (partial) |
| `dev/`, `qwen-both-test/` | Small development and smoke runs |
| `eval-llm2/` | Results of the blinded second-LLM check (scripts are in `eval/llm2/`) |

New CLI runs default to `outputs/run-<timestamp>/`; API runs go to `outputs/api-<timestamp>/`.
