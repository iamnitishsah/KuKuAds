# AI tools used, and where they got it wrong

## Tools
| Tool | Used for |
|---|---|
| Claude (Claude Code) | Research on approaches/papers, architecture discussion, writing the code and tests, auditing results |
| FreeLLM router (local) → `gpt-oss-120b`, `command-a` | The **finder** (picks promo beats) |
| Self-hosted Ollama `qwen3.8:27b` | The **judge** (scores clips as a cold viewer) |

The model in each role is configured, not hard-coded (`configs/config.yaml`).

## Where the AI got it wrong (real examples)
1. **The finder's `context_needed` field was always "low".** The prompt asked the model to say how much backstory a clip
   needs; it answered "low" every time, even for mid-story scenes the judge found confusing. We stopped trusting it and
   rely on the independent judge's clarity score instead.
2. **The judge scored clips as unclear when it could not see the action.** Given only dialogue, Ep 1 got clarity 2.
   The screenplay has camera/action lines; adding them to the judge's transcript fixed it.
3. **Unanchored 1–5 scales clustered at 2–3**, so ranking separated nothing. Anchoring each score with a definition fixed
   that, but the judge then swung the other way and became lenient (79% scores of 4–5): a known, still-open problem.
4. **The finder proposed clips that started before the hook** (start moved to the hook beat in 4 cases) and clips that
   were too short or too long. Code, not the model, enforces the rules, because the model's own timing claims are not
   trustworthy.
5. **The router quietly changed the model.** See `DEV_LOG.md` #1: the finder ended up grading its own clips.

## How I used AI
Decisions (pipeline shape, pinned models, one independent judge, what counts as proof) were made in conversation and
checked against run logs; every claim in the docs traces to a file in `outputs/`.
