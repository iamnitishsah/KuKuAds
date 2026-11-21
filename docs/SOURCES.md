# Sources

## Input data
- **Kuku input pack:** the first 50 episodes of *I Married a Broken Soldier. He was a Duke*, as detailed screenplays with
  a timestamp for every scene, line of dialogue and key action (3,727 beats, about 169k tokens).
  Kuku's confidential content, shared only for the assignment; kept in `data/raw/` and gitignored.
- **Assignment brief:** `submission/Kuku-AI Generalist Assignment.pdf` (Problem 1: Find the Promos).

## Models used
| Role | Model | How it was served |
|---|---|---|
| Finder | `gpt-oss-120b` (fallback `command-a`) | local OpenAI-compatible router (`freellm`) |
| Judge | `qwen3.8:27b` | self-hosted Ollama |
| Finder in the all-qwen run | `qwen3.8:27b` | self-hosted Ollama |
| Blinded second rater (LLM-2) | DeepSeek V4.1 Flash | see `eval/reports/LLM2_EVALUATION.md` |

## References
- ByteDance / USTC, **HIVE**, arXiv 2507.02790: cuts short dramas into ads from video. KuKuAds starts at its highlight
  step, because screenplays already hold the dialogue, speakers and scenes, and adds length control and a
  standalone-clarity check.
- Promo style reference named in the brief: ReelShort and DramaBox ads on TikTok, Instagram and YouTube Shorts.

## Tools
Claude Code for research, code and auditing (see [AI_LOG.md](AI_LOG.md)).
