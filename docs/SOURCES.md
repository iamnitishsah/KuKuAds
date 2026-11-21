# Sources

## Input data
- **Kuku input pack:** the first 50 episodes of *I Married a Broken Soldier. He was a Duke*, as detailed screenplays with
  a timestamp for every scene, line of dialogue and key action (3,727 beats, about 169k tokens).
  Kuku's confidential content, shared only for the assignment; kept in `data/raw/` and gitignored.
- **Assignment brief:** the Kuku AI Generalist Assignment PDF, Problem 1: Find the Promos (kept locally, not in this repository).

## Models used
Current defaults (`configs/config.yaml`; keys `GROQ_API_KEY` and `GEMINI_API_KEY` in `.env`):

| Role | Model | Served by |
|---|---|---|
| Finder | `openai/gpt-oss-120b` | Groq |
| Finder fallback (only if the Groq call fails) | `gemini-3.5-flash` | Gemini |
| Judge (never the finder's model, no fallback) | `qwen/qwen3.8-27b` | Groq |

The archived run (`outputs/full-run`) used the same two models served differently: finder `gpt-oss-120b` (fallback
`command-a`) through a local OpenAI-compatible router, judge `qwen3.8:27b` on self-hosted Ollama. The all-qwen run used
`qwen3.8:27b` for both stages. The blinded second rater (LLM-2) was DeepSeek V4.1 Flash; see `eval/reports/LLM2_EVALUATION.md`.

## References
- ByteDance / USTC, **HIVE**, arXiv 2507.02790: cuts short dramas into ads from video. KuKuAds starts at its highlight
  step, because screenplays already hold the dialogue, speakers and scenes, and adds length control and a
  standalone-clarity check.
- Promo style reference named in the brief: ReelShort and DramaBox ads on TikTok, Instagram and YouTube Shorts.

## Tools
Claude Code for research, code and auditing (see [AI_LOG.md](AI_LOG.md)).
