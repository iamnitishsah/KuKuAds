# KuKuAds: Solution (Problem 1, Find the Promos)

**Prototype:** https://github.com/iamnitishsah/KuKuAds  ·  **Raw outputs:** `outputs/full-run/` (shared by Drive link; not in the repo because the input pack is confidential)

## Why this problem
An editor watches every episode to pick promos, and new shows arrive every week. It is the problem where the answer
can be checked (a time range, a hook, a cliffhanger) and where code and AI each have an obvious job. I scoped it to
*finding* promos only: no editing, music or overlays.

## Assumptions
- Screenplay timestamps match the final video. A promo is 20–60 s, with the hook in the first 3 s and the cut on an unresolved moment.
- I judge from text (dialogue plus shot descriptions). I cannot see video or hear audio.
- The "post first" list has at most one promo per episode, so it is not one storyline.
- Episodes 1–5 get a small bonus (0.05), because a new viewer can start there.

## How it works
| Step | Done by | What it does |
|---|---|---|
| Parse | code | Splits each screenplay into timed beats with IDs (3,727 beats, 0 parse errors) |
| Find | AI, one call per episode | Proposes promos as beat IDs only, so it cannot invent a timestamp |
| Validate | code | Turns IDs into times; enforces 20–60 s, hook within 3 s, cut on the cliffhanger, never mid-line; logs every fix or rejection |
| Judge | a *different* AI | Reads only the clip, like a stranger, and scores hook, cliffhanger and clarity from 1 to 5 |
| Rank | code | 0.3 hook + 0.3 cliffhanger + 0.3 clarity + 0.1 intensity, one promo per episode in the top 15 |
| Baseline | code | A rules-only version of the task, scored by the same judge, as the control |

**Human in the loop:** the tool proposes and explains; an editor decides what to post.
**Swappable model:** one model per step in `configs/config.yaml`, or `python run.py --scripts <folder> --provider anthropic --model <id>`.
OpenAI, Gemini, Groq, Anthropic, Ollama and any OpenAI-compatible router work. A new show is the same command with a different folder.
**Check it runs:** `python run.py --selftest` (offline) or `streamlit run app.py`, whose Status tab also shows which models are reachable.

## Scale and cost
50 episodes is about 169k tokens. A full run was about 517k tokens (50 finder calls, 256 judge calls) and took about 51 minutes on a free self-hosted 27B model. Cost grows linearly with episodes, and re-runs are free from the cache. With a paid API I would use a stronger model for finding and judging and run shows in parallel; the pipeline would not change.

## How I know it is good
| Check | Result |
|---|---|
| Rules, checked in code | 78 of 78 promos are 20–60 s with the hook inside 3 s; 77 of 78 end on the cliffhanger |
| Invented quotes | 0 |
| Coverage | 84 proposed, 78 valid; 49 of 50 episodes have a promo |
| Against the rules-only baseline | The AI's best promo wins in 31 of 49 episodes (not statistically proven). Its edge is the cliffhanger (better in 20, worse in 7). Hook and clarity are not clearly better |
| Is the judge steady? | Judging twice gives the same score 79% of the time and within 1 point 99%; the two rankings correlate at 0.90 |
| Did the AI grade its own picks? | No: 0 of 78 |
| Different finder model | Only 2 of the top 5 survive. E31-P2 is #1 in both runs and in a blinded second-AI check |

So the AI's real value is **choosing where to cut**; on hook and clarity a simple baseline is close.
**Not done:** a human-labelled check (about 20 blind clips) of the judge. Until then, "good" means "an AI judge agrees", which is a proxy. The real measure is the 3-second hold rate and click-through of A/B-tested ads.

## Where it fails
- **Coverage depends on the model.** The archived run misses Ep 42 (a 17.4 s clip was rejected); another run covers it but misses Ep 33 (60.3 s, 0.3 s over the cap). The real problem is the hard 60 s limit.
- **Cut edges.** E04-P2 ends 0.1 s inside a line and E32-P1 starts 0.2 s inside one.
- **Lenient judge.** 72% of scores are 4 or 5, so small gaps at the top are weak evidence.
- **Self-grading.** In the second run the same model found and judged every promo, so those scores may be generous.
- **Brand safety.** The #1 and #3 picks (Ep 31, 32) show a red-hot iron inches from an eye. There is no safety check yet.
- **Low clarity.** Mid-story scenes with unexplained names or relationships (for example E49-P1, E06-P2, E17-P1).

Next I would: repair clips instead of rejecting them, add edge checks, rank the top clips head to head, add a safety flag, then build the human-labelled set.

## AI tools used, and one place they got it wrong
Claude Code for research, code and checking results; `gpt-oss-120b` and `command-a` (through a local router) as the finder; a self-hosted `qwen3.8:27b` as the judge.
**Where it went wrong:** my router silently switched to the finder model when the judge was rate-limited, so the finder graded 108 of 128 clips itself. The call log showed the real model. I made the client wait out the limit and keep the pinned model, and the report now counts self-graded clips. Twelve such problems are in `docs/DEVELOPMENT.md`.
