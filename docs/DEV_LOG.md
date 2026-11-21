# Dev log: mistakes made and how they were solved

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
| 11 | **Validator rejected a good episode instead of repairing it** (Ep 42: 17.4 s after the start moved to the hook) | Audit found one episode with no promo although the best scene was in the funnel | Open. Plan: extend the end to the next strong beat, then re-ask the finder once with the reason |
| 12 | **I almost trusted the first ranking** before measuring whether the judge was stable | Repeated each judgement twice and computed rank correlation (0.90) and top-15 overlap (11/15) | Judge stability is now part of the report |

## What I'd tell an interviewer
The most important lesson: a fallback that works *silently* is worse than a failure, because it quietly breaks the
experiment. So the client logs which model really answered, and the report surfaces it.
