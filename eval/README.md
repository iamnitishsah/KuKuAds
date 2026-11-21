# eval/

`reports/` holds the long evidence behind the numbers in [docs/findings.md](../docs/findings.md):

| File | What |
|---|---|
| `reports/DETAILED_WORKING_REPORT.md` | every stage with the real prompts, inputs and outputs from the archived run |
| `reports/LLM2_EVALUATION.md` | the blinded second-LLM check on 24 clips: method, prompt, all scores |

The scripts that built the second-LLM packet were removed: they had hard-coded paths from another machine and could
not run here. They are in git history (commit `e18ca80`).
