# eval/

`llm2/` holds the one-off scripts that built the blinded LLM-2 comparison (packet, key, tables, report rendering).
Results are in `outputs/eval-llm2/`; the write-up is `eval/reports/LLM2_EVALUATION.md`.

These scripts were written on another machine: `ROOT`, `SCRIPTS` and temp paths are hard-coded Windows paths
(`C:\\Users\\kunal\\...`). Edit those constants before re-running them. They are not part of the pipeline.
