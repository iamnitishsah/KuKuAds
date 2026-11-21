# Detailed Working Report — Promo Finder (Problem 1)

**What this document is.** A layer-by-layer account of the pipeline that produced `outputs/full-run/`: what goes in, what comes out, the exact prompt used, and the real numbers from the 50-episode run. Every example below is copied from the archived artifacts, not reconstructed from memory. Where a claim in the summary does not survive checking, it is flagged in [§12](#12-verified-corrections-and-limits).

**Archived run.** `outputs/full-run/` — 50 episodes, finder `gpt-oss-120b` (local router), judge `qwen3.8:27b` (self-hosted Ollama), finished 2026-11-21 03:34:02, wall time 3,076.2 s (51.3 min), 0 errors.

**Second run.** A second full 50-episode run used `qwen3.8:27b` for **both** stages (`outputs/full-run-qwen-both/`). It is compared in [Appendix C](#appendix-c--second-run-all-qwen). Because the finder and judge are the same model, all 83 LLM promos are **self-graded**; treat that run as coverage/finder evidence, not independent quality evidence.

**Input pack (confidential, not in the repo).**
`C:\Users\kunal\nitish\I Married a Broken Soldier. He was a Duke-scripts (2) (1)` — 50 `.txt` screenplays, 100 scenes, 6,162.62 s (102.71 min).

---

## 0. At a glance

| # | Layer | Owner | Input | Output | Real number |
|---|---|---|---|---|---|
| 1 | Parse | code | 50 screenplays | `beats.json` | **3,727 beats**, 100 scenes |
| 2 | Find | LLM | one episode's beats | `candidates.json` | **84 proposals**, 50 logical calls |
| 3 | Validate / fix | code | beat-ID proposals | fixed promos | **16 fix events** on 13 promos |
| 4 | Validate / reject | code | fixed promos | rejected set | **6 rejected** (4 short, 2 duplicate) |
| 5 | Valid set | code | fixed promos | 78 valid | **78 valid**, 49/50 episodes |
| 6 | Baseline | code | same beats | `baseline.json` | **98 generated, 50 judged** |
| 7 | Judge | LLM | clip transcript | judge scores | **128 promos × 2 = 256 calls** |
| 8 | Rank | code | judge + intensity | ranked rows | **78 ranked** |
| 9 | Top list | code | ranked rows | top 15 | **15**, one per episode |
| 10 | Coverage | — | — | — | **49/50 LLM**, 50/50 with baseline |

---

## 1. Parse — 3,727 beats

### What it does

`pipeline/parse.py` reads each episode and turns every timed screenplay block into a **beat**. A beat is one cue: dialogue, camera shot, action, or sound effect. It carries a stable ID, episode, scene, start/end seconds, track type, speaker, tone tags, and text. Code also attaches three cheap signals (`intensity`, `physical`, `cliff_cue`) that later stages use without calling a model.

The key design choice: **the LLM never sees or writes a timestamp.** It sees beat IDs and returns beat IDs. All timing is computed from the parsed beats.

### Input — real Episode 1 excerpt

```
EPISODE LOGLINE: Lady Juliana arrives at the cathedral in her late mother's bridal gown,
only to suffer the ultimate betrayal when her fiancé Gerald abandons her at the altar
for her cruel sister Clarissa with her family's full blessing.

**CAMERA:**
Start: (00:00.00) | End: (00:04.80)
Symmetrical framing on the heavy church doors as they slowly part...

**MATRIARCH (Cold, Commanding):**
Start: (00:11.30) | End: (00:13.10)
"You should turn around, Juliana."
```

### Output — the same moment as a beat (E01-B008)

```json
{
  "id": "E01-B008",
  "episode": 1,
  "index": 7,
  "type": "dialogue",
  "speaker": "MATRIARCH",
  "tags": ["Cold", "Commanding"],
  "text": "\"You should turn around, Juliana.\"",
  "start": 11.3,
  "end": 13.1,
  "scene": 1,
  "intensity": 2,
  "physical": false,
  "cliff_cue": false
}
```

A camera beat at the same moment is separate, because camera/action/dialogue run on parallel tracks:

```json
{
  "id": "E01-B007",
  "type": "camera",
  "text": "Medium shot as Juliana stops midway down the aisle, confronted by a haughty matriarch in black velvet stepping into the foreground.",
  "start": 11.0, "end": 13.2, "scene": 1, "intensity": 0
}
```

### Signals attached by code

| Signal | Meaning | Example |
|---|---|---|
| `intensity` | 0–3 heat from tone tags and punctuation | `["Cold", "Commanding"]` → 2 |
| `physical` | slap, strike, kneel, seize, fire… | E01-B090 (hand clenches) |
| `cliff_cue` | "cliffhanger peak", "cut to black", "freeze" | E01-B094 |

### Numbers

| Metric | Value |
|---|---|
| Episodes | 50 |
| Scenes | 100 |
| Beats / timestamped cues | **3,727** |
| Dialogue / camera / action / SFX | 1,487 / 1,754 / 372 / 114 |
| Runtime | 6,162.62 s = 102.71 min |
| Beats per episode | min 37 (Ep 42), max 121 (Ep 36), mean 74.5 |
| Timestamp format | all `mm:ss.xx`; no scene-clock resets |
| Parser anomalies | 8 local timestamp reversals ≤1.0 s (overlapping tracks), one 0.3 s scene-boundary overrun (E22-B023) |

**Verified:** a fresh parse of all 50 files is deep-equal to `beats.json`, and every raw cue is consumed exactly once. “0 parse mismatches” is not a defined metric; the defensible version is “3,727/3,727 cues parsed once, artifact reproducible.”

---

## 2. Finder — 84 proposals

### What it does

`pipeline/find.py` builds one prompt per episode and makes one LLM call. The model returns **beat IDs only** plus hook, cliffhanger, why-it-works, patterns, and `context_needed`. Code later converts IDs to timestamps. The model may return up to 3 promos and is told to return fewer if the episode has few strong moments.

Camera lines are filtered out of the prompt unless they carry a key visual (`physical` or `cliff_cue`), so Episode 1 sends 47 of its 95 beats.

### The exact system prompt (`FINDER_SYSTEM`)

```
You are a senior promo editor for vertical microdrama apps (like the 20-60 second ads ReelShort and DramaBox run on TikTok, Instagram and YouTube Shorts). From one episode's screenplay you pick the clips that make a scrolling stranger stop, and then crave the next episode.

A GOOD PROMO:
1. HOOK - its first 3 seconds contain a striking line or action: a slap, a reveal, a cruel or shocking line, a threat. Never start on a calm establishing moment, someone walking, or small talk.
2. CLIFFHANGER - it ends on an unresolved moment: cut right after the question / threat / reveal, BEFORE the answer, the rescue or the reaction resolves it.
3. STANDALONE - a stranger who has never seen the show understands who wants what. Prefer moments where relationships are stated in the dialogue (sister, father, husband, duke). Avoid clips that only make sense with plot knowledge from earlier episodes.
4. LENGTH - 20 to 60 seconds in total (use the timestamps); 25-45 seconds is ideal.
5. One continuous stretch is preferred. You may join up to 2 stretches from this episode when that makes a clearly stronger promo (e.g. hook from one moment, cliffhanger from a later one), in story order.

PROMO PATTERNS that perform well (weight): betrayal or shocking reveal (3), identity reveal / power reversal (3), humiliation of the heroine (2), violence, slap or physical threat (2), rescue / protective hero (2), ultimatum or impossible choice (2), forbidden romance / intimacy (1), cliffhanger ending (2).

Return between 1 and 3 promos, best first. Return fewer if the episode has few strong moments: quality over quantity. Promos must not overlap much with each other.

Answer ONLY with JSON in exactly this shape:
{"promos": [{
  "segments": [{"start_beat": "E01-B008", "end_beat": "E01-B031"}],
  "hook_beat": "E01-B008",
  "cliffhanger_beat": "E01-B031",
  "hook": "<the hook in a few words, quoting the key line>",
  "cliffhanger": "<the unresolved moment it cuts on>",
  "why": "<one line: why a cold viewer would stop and want more>",
  "patterns": ["betrayal or shocking reveal"],
  "context_needed": "none | low | high"
}]}
Use ONLY beat IDs from the list. Never write timestamps yourself.
```

### The exact user prompt template (`FINDER_USER`)

```
SERIES PREMISE (episode 1): {premise}
PREVIOUSLY (episode {prev_num}): {previously}
THIS EPISODE ({num}, length {length}): {logline}

BEATS - format: ID [start-end] SPEAKER (tone): line   |   [ACTION] / [SOUND] lines describe what is seen/heard
{beats}
```

### Real user prompt for Episode 1 (excerpt)

Full prompt: **5,204 characters, 47 beats**. Reproduce it exactly with `pipeline.find.build_finder_prompt(show[0], show, 3)`; a representative slice follows.

```
SERIES PREMISE (episode 1): (this is episode 1)
PREVIOUSLY (episode -): (none - first episode)
THIS EPISODE (1, length 02:18.00): Lady Juliana arrives at the cathedral in her late mother's bridal gown, only to suffer the ultimate betrayal when her fiancé Gerald abandons her at the altar for her cruel sister Clarissa with her family's full blessing.

BEATS - format: ID [start-end] SPEAKER (tone): line   |   [ACTION] / [SOUND] lines describe what is seen/heard
E01-B002 [00:01.00-00:04.80] [ACTION] Juliana pauses at the threshold, her expression bright with joyful anticipation, wearing her mother's vintage gown and an oval pendant necklace.
E01-B005 [00:07.20-00:09.80] [ACTION] Juliana's eyes widen slightly in bewilderment as she notices something amiss at the altar.
E01-B008 [00:11.30-00:13.10] MATRIARCH (Cold, Commanding): "You should turn around, Juliana."
E01-B009 [00:13.50-00:14.30] LADY JULIANA (Confused, Breathless): "Why?"
E01-B011 [00:15.50-00:17.50] LADY JULIANA (Desperate, Unbelieving): "Gerald is waiting for me."
E01-B013 [00:18.00-00:19.40] MATRIARCH (Blunt, Unforgiving): "Not anymore."
E01-B015 [00:21.80-00:23.50] LADY JULIANA (Trembling, Pleading): "What do you mean?"
E01-B017 [00:23.80-00:25.50] MATRIARCH (Dismissive): "Look for yourself."
E01-B018 [00:25.60-00:29.80] [ACTION] Juliana walks forward past the Matriarch, her breath hitching as she approaches the altar steps, looking up in shock.
E01-B023 [00:33.80-00:35.00] LADY JULIANA (Shaken, Whispering): "Gerald?"
E01-B024 [00:35.40-00:37.70] LADY JULIANA (Heartbroken): "Why are you holding her hand?"
E01-B027 [00:39.10-00:41.20] LADY IN GOLD GOWN (Gloating, Smug): "Because he is marrying me."
...
E01-B090 [02:11.30-02:13.80] [ACTION] Juliana's hand clenches fiercely into the folds of her mother's silk bridal gown, knuckles whitening with suppressed fury.
E01-B094 [02:15.00-02:17.50] [SOUND] Solemn low-pitched string drone swells to an ominous cliffhanger peak.
E01-B095 [02:17.00-02:18.00] [SHOT] Cut to black.
```

### Real output — Episode 1 returned two promos

`candidates.json` preserves the proposal fields; validator metadata is added later. The raw model answer was beat IDs + text, not timestamps.

```json
{
  "promo_id": "E01-P1",
  "segments": [{"episode": 1, "start_beat": "E01-B008", "end_beat": "E01-B041"}],
  "hook_beat": "E01-B008",
  "cliffhanger_beat": "E01-B041",
  "hook": "\"You should turn around, Juliana.\"",
  "cliffhanger": "The former groom coldly declares, \"I changed my mind,\" leaving Juliana's fate hanging.",
  "why": "A sudden betrayal at the altar shocks viewers and begs to know what happens next.",
  "patterns": ["betrayal or shocking reveal"],
  "context_needed": "low"
}
```

```json
{
  "promo_id": "E01-P2",
  "segments": [{"episode": 1, "start_beat": "E01-B075", "end_beat": "E01-B090"}],
  "hook_beat": "E01-B075",
  "cliffhanger_beat": "E01-B090",
  "hook": "\"You are the daughter people tolerate because they have to.\"",
  "cliffhanger": "Clarissa boasts that she's the true jewel, hinting at a power shift as the episode cuts to a tense silence.",
  "why": "The cruel truth about family loyalty and a looming power play compel viewers to watch the fallout.",
  "patterns": ["betrayal or shocking reveal"],
  "context_needed": "low"
}
```

### Why the timestamps differ from the beat IDs

E01-P1’s start beat is **B008 at 11.3 s** and its cliff beat is **B041 at 61.8 s**, but the validated segment is **11.0–63.0 s**. The validator snaps the start back to camera **B007** (11.0 s, within `SNAP_START_S = 1.0`) and the end forward to the end of camera **B040** (63.0 s, the shot that contains Gerald’s line, within `SNAP_END_S = 1.5`). That is how the model’s beat-ID answer becomes a clean shot boundary — and why the clip runs 1.2 s past Gerald’s line. The snap is not logged as a “fix,” which is why E01-P1 has no notes.

### Numbers

| Metric | Value |
|---|---|
| Logical finder calls | 50 (one per episode) |
| Cached responses in this archived run | **50 / 50** (the live calls happened when the cache was populated) |
| Fallbacks used | 0 (`command-a` never used) |
| Proposals | **84** |
| Proposals per episode | 1.68 average (max 3) |
| Served by | `openai/gpt-oss-120b` ×25, `@cf/openai/gpt-oss-120b` ×24, `gpt-oss-120b` ×1 |
| Finder tokens | 127,126 in / 83,879 out |

The three “served by” labels are the same logical model behind different router upstreams; the per-call log records which one answered.

---

## 3. Validator — 16 recorded fixes (not 22)

### What it does

`pipeline/validate.py` converts beat IDs to timestamps and enforces the brief. Every fix or rejection is written to `notes`, so a bad pick can be explained.

Rules, in order:

1. Beat IDs must exist, be in order, and not overlap.
2. Hook must open the clip: if the hook beat starts more than **3.0 s** after the segment start, move the start to the hook beat.
3. End on the cliffhanger: trim a trailing resolution, or extend to the cliffhanger.
4. Snap the start back to a camera-shot edge (≤1.0 s) and the end forward (≤1.5 s).
5. Enforce 20–60 s. Too long → move the start to a later strong beat. Too short → move the start back to an earlier strong beat.
6. Deduplicate later proposals with temporal IoU > 0.6.

### The 16 fix events (all kept in the valid set)

| Fix type | Events | Promos |
|---|---|---|
| Too short → start moved back to a strong beat | 8 | E04-P2, E05-P2, E05-P3, E19-P3, E27-P1, E33-P1, E33-P2, E33-P3 |
| Too long → start moved to a later strong beat | 4 | E14-P1, E29-P1, E32-P1, E48-P1 |
| Start moved to hook beat | 4 | E25-P1, E33-P1, E33-P2, E33-P3 |
| **Total** | **16** | **13 distinct promos** (E33-P1/P2/P3 each carry two fixes) |

The report line “too short ×8, too long ×4, start moved ×4 = 16” counts **fix events**, not promos. Across all 84 proposals there are **23 notes**: 16 on the 13 valid promos above, and 7 on the 6 rejected promos (E42-P1 carries two: the hook move and the 17.4 s rejection; the other four short promos and two duplicates carry one each). “22” does not match any count.

### Worked fix + rejection: E42-P1

This is the one that leaves Episode 42 uncovered.

```json
{
  "promo_id": "E42-P1",
  "segments": [
    {"episode": 42, "start": 12.8, "end": 16.6, "start_beat": "E42-B004", "end_beat": "E42-B006"},
    {"episode": 42, "start": 64.2, "end": 77.8, "start_beat": "E42-B034", "end_beat": "E42-B037"}
  ],
  "hook_beat": "E42-B004",
  "cliffhanger_beat": "E42-B037",
  "status": "rejected",
  "notes": [
    "start moved to hook beat (E42-B002 -> E42-B004)",
    "too short (17.4s < 20s)"
  ],
  "duration_s": 17.4
}
```

Why repair failed:

- The model originally started at B002; the hook was B004 at 12.8 s, so the start moved forward to B004.
- That shrank the first segment to 3.8 s. With the second segment (13.6 s), the total became **17.4 s**.
- The validator tries an earlier strong beat. B003 gives 18.8 s (still short); B002 would give 29.0 s but it is an `action` beat with `physical = false`, so `is_strong()` is false; B001 is a camera beat. There is no eligible earlier beat, so it rejects instead of repairing.

This is the exact mechanism behind “Ep 42 has no promo.” The episode itself is fine (77.8 s, 37 beats). Its reveal is major: the guards refuse Rupert’s arrest order, Alexander is publicly proclaimed “Alexander Ashburn. The rightful Duke of Ashburn!” — but the candidate was rejected before judging. Note that E43-P1 partly replays the same cathedral confrontation, so the unique mother’s-proclamation beat is what is missing.

---

## 4. Validator — 6 rejections

| Promo | Reason | Detail |
|---|---|---|
| E04-P1 | too short | 14.2 s < 20 s |
| E19-P1 | too short | 9.0 s < 20 s |
| E19-P2 | too short | 11.8 s < 20 s |
| E42-P1 | too short | 17.4 s < 20 s (after the hook move above) |
| E43-P2 | duplicate | overlap with E43-P1; recomputed IoU **0.675** > 0.6 |
| E46-P2 | duplicate | overlap with E46-P1; recomputed IoU **0.793** > 0.6 |

Funnel: **84 proposed → 78 valid, 6 rejected**.

---

## 5. Valid set — 78 promos, 49/50 episodes

| Check | Result | How it was measured |
|---|---|---|
| Duration 20–60 s | **78/78** | recomputed from segment timestamps; min 20.0 s (E22-P1), max 59.2 s (E45-P1) |
| Hook within 3 s | **78/78** | hook beat start − first segment start; max 2.5 s (E11-P1) |
| Ends on the cliffhanger *beat* | **77/78** | `end_beat == cliffhanger_beat`; only E04-P2 fails |
| Ends within 3 s of the cliffhanger *end* | **76/78** | timestamp test; E04-P2 is 4.0 s past, E06-P2 is 3.2 s past but its `end_beat` is the cliff beat, so the label-based count hides it |
| Episodes covered | **49/50** | Ep 42 has no valid LLM promo; the baseline does cover Ep 42 (E42-B1, 30.1 s) |
| Invented quotes | **0** | 103/105 quoted spans match a single dialogue line exactly; E36-P2 merges two real lines, E10-P1 truncates a real SOUND FX line |

**Correction to “never cut mid-line.”** It is not literally true. The validator snaps and trims, but two clips still intersect a line:

- **E04-P2** ends at 69.5 s, 0.1 s before B050 ends (68.0–69.6 s).
- **E32-P1** starts at 107.0 s, 0.2 s before B079 ends (103.8–107.2 s), so the viewer hears only the tail of the setup line.

`END_SLACK_S = 3.0` allows the end to run past the cliff beat, and `_snap()` runs after the trim; that is why a “safe” label does not guarantee a clean line boundary.

**Known cut-edge cases** (verified against the scripts):

- E01-P1 ends at 63.0 s. It **does** include Gerald’s “I changed my mind.” (60.1–61.8 s); Clarissa’s “People change their minds, sister.” starts 3.5 s after the cut. So “3 s before the sting” is true for Clarissa, not for Gerald.
- E47-P1 does **not** end mid-sentence. B067 (“I offer you bread and honest labor. Take the apron, or leave the county.”) is complete; the next line is omitted whole. The real mid-sentence cut is **E04-P2**, above.
- E32-P1 starts 0.2 s before a reply; the setup line is a statement, not a question. The missing context is real, but the “reply to an unheard question” wording is imprecise.

---

## 6. Baseline — 98 generated, 50 judged

### What it does

`pipeline/baseline.py` is the no-LLM control. For every possible clip starting on a strong non-camera beat and lasting 25–45 s, it computes:

```
rule score = hook heat in the first 3 s
           + ending (cliff cue or episode end within 3 s, plus last-line intensity)
           + mean dialogue heat
```

It sorts by rule score and keeps the top non-overlapping clips. It generates **up to 2 per episode**: **98 in total** — 48 episodes produce 2, while Episodes 19 and 50 produce only 1. Only the first/best one per episode (`B1`) is sent to the judge — **50 judged** — to bound comparison cost.

### Real example: E01-B1

```json
{
  "promo_id": "E01-B1",
  "source": "baseline",
  "segments": [{"episode": 1, "start": 39.0, "end": 66.0,
                "start_beat": "E01-B027", "end_beat": "E01-B043"}],
  "hook": "\"Because he is marrying me.\"",
  "cliffhanger": "\"You swore you loved me!\"",
  "why": "rule score 6.50",
  "intensity": 0.75,
  "judge": {"hook": 5, "cliffhanger": 4, "clarity": 5,
            "repeats": [{"hook": 5, "cliffhanger": 4, "clarity": 5},
                        {"hook": 5, "cliffhanger": 4, "clarity": 5}],
            "spread": 0},
  "scores": {"hook": 1.0, "cliffhanger": 0.75, "clarity": 1.0,
             "intensity": 0.75, "entry_bonus": 0.05, "final": 0.95}
}
```

E01-B1 scores **0.95**, above LLM E01-P1’s **0.9217**, because its intensity is 0.75 vs 0.467. The judge scores are identical (5/4/5). This is a clean illustration of why the comparison must be per-episode and paired: on Episode 1 the simple baseline wins.

---

## 7. Judge — 128 promos, 256 calls

### What it does

`pipeline/judge.py` gives the judge **only the clip transcript**: dialogue, visible action, camera descriptions, sound, with seconds from clip start. No logline, no premise, no character list, no episode number. Each clip is judged twice; scores are averaged and the spread is kept.

### Exact judge system prompt (`JUDGE_SYSTEM`)

```
You are a typical US viewer scrolling TikTok. You have NEVER seen this show and know nothing about it. You will read the transcript of one short video clip: dialogue and visible action, in order, with seconds from the clip start. Speaker labels are how the characters would look on screen to you.

Judge it honestly and use the whole scale.
- hook (1-5): do the first 3 seconds make you stop scrolling?
  5 = shocking line/action instantly; 3 = mildly intriguing; 1 = nothing happens, you scroll on.
- cliffhanger (1-5): does it cut at a moment that leaves you needing to know what happens next?
  5 = cut mid-crisis, you must know what happens; 3 = some open question; 1 = resolved or just fizzles out.
- clarity (1-5): with zero background, can you follow it? You do NOT need names or full backstory - promos
  rarely give that. Judge whether the core situation and stakes are clear.
  5 = instantly obvious who is the victim, who is the villain and what is at stake (e.g. "a bride is jilted
  at the altar for her sister"); 3 = you get the gist of the conflict but key relationships or stakes are
  fuzzy; 1 = you cannot tell what is going on or why it matters.

Answer ONLY with JSON:
{"summary": "<one sentence: what is happening>",
 "confusing": "<what is unclear to you, or 'nothing'>",
 "want_next": "<the question you are left with, or 'nothing'>",
 "hook": 1, "cliffhanger": 1, "clarity": 1,
 "would_watch_next_episode": true}
```

### Exact judge user prompt template (`JUDGE_USER`)

```
CLIP ({duration:.0f} seconds):
{clip}
```

### Real input — E01-P1 transcript (52 s)

```
CLIP (52 seconds):
[ 0.0s] (on screen) Medium shot as Juliana stops midway down the aisle, confronted by a haughty matriarch in black velvet stepping into the foreground.
[ 0.3s] MATRIARCH (Cold, Commanding): "You should turn around, Juliana."
[ 2.5s] LADY JULIANA (Confused, Breathless): "Why?"
[ 3.3s] (on screen) Over-the-shoulder medium close-up past the Matriarch to Juliana, looking past her toward the altar.
[ 4.5s] LADY JULIANA (Desperate, Unbelieving): "Gerald is waiting for me."
[ 6.8s] (on screen) Close-up on the Matriarch wearing an ornate tiara and sapphire jewelry, gazing down with merciless disdain.
[ 7.0s] MATRIARCH (Blunt, Unforgiving): "Not anymore."
[ 9.5s] (on screen) Close-up on Juliana's stricken face as the weight of the words sinks in.
[10.8s] LADY JULIANA (Trembling, Pleading): "What do you mean?"
[12.6s] (on screen) Medium shot of the Matriarch gesturing dismissively toward the altar.
[12.8s] MATRIARCH (Dismissive): "Look for yourself."
[14.6s] (on screen) Juliana walks forward past the Matriarch, her breath hitching as she approaches the altar steps, looking up in shock.
[14.8s] (on screen) Medium front tracking shot moving backward ahead of Juliana as she advances down the center aisle.
[18.8s] (on screen) Panning shot across the seated wedding guests whispering and casting judging glances from the wooden pews.
[21.8s] (on screen) Low-angle shot from behind Juliana looking up at Gerald and the Lady in Gold Gown standing proudly before the altar.
[22.7s] (on screen) Close-up on Juliana's trembling lips and shocked, tearful blue eyes.
[22.8s] LADY JULIANA (Shaken, Whispering): "Gerald?"
[24.4s] LADY JULIANA (Heartbroken): "Why are you holding her hand?"
[25.5s] (on screen) Close-up insert of Gerald's fingers firmly interlocked with the white-gloved hand of the Lady in Gold Gown.
[28.0s] (on screen) Close-up on the Lady in Gold Gown beaming with cruel triumph.
[28.1s] LADY IN GOLD GOWN (Gloating, Smug): "Because he is marrying me."
[30.5s] (on screen) Close-up on Juliana as tears spill over her eyelashes.
[30.7s] LADY JULIANA (Gasping, Devastated): "No..."
[32.9s] (on screen) Wide profile shot showing Juliana standing below the altar platform, looking up at Gerald and her sister.
[35.8s] (on screen) Close-up on Juliana clutching her chest, her sorrow turning into burning outrage.
[35.8s] LADY JULIANA (Outraged, Accusing): "You knew this before I walked through those doors!"
[39.4s] (on screen) Medium shot of Gerald standing stoic and impassive next to the smug Lady in Gold Gown.
[41.0s] (on screen) Close-up on Juliana's hands desperately clenching fistfuls of her white dress fabric.
[41.8s] LADY JULIANA (Choking on Tears): "You let me come here..."
[43.6s] (on screen) Close-up on Juliana's tear-streaked face as she shakes with grief.
[43.7s] LADY JULIANA (Crushed, Shaking): "You let me dress in my mother's gown..."
[46.0s] LADY JULIANA (Crying Out): "You let me believe I was walking toward my husband!"
[46.6s] (on screen) Medium shot on Gerald stepping forward, cold and indifferent, with the Lady in Gold Gown lingering in soft focus behind him.
[49.1s] (on screen) Tight close-up on Gerald's hardened profile as he glances down.
[49.1s] THE FORMER GROOM (Cold, Callous): "I changed my mind."
```

### Real output — E01-P1 judge JSON

```json
{
  "summary": "A bride is stopped in the aisle by a matriarch and discovers her fiancé is about to marry her sister instead.",
  "confusing": "The specific relationship between the matriarch and the other woman is not explicitly stated, though it is implied they are aligned against the bride.",
  "want_next": "Will the bride fight back, or will she just walk away in humiliation?",
  "hook": 5,
  "cliffhanger": 4,
  "clarity": 5,
  "would_watch_next_episode": true
}
```

Stored with repeats and provenance:

```json
{
  "hook": 5, "cliffhanger": 4, "clarity": 5,
  "repeats": [{"hook": 5, "cliffhanger": 4, "clarity": 5},
              {"hook": 5, "cliffhanger": 4, "clarity": 5}],
  "spread": 0,
  "model": "ollama/qwen3.8:27b",
  "served_by": "qwen3.8:27b",
  "fallback": false
}
```

### Numbers

| Metric | Value |
|---|---|
| Promos judged | **128** = 78 LLM + 50 baseline B1 |
| Calls | **256** = 128 × 2 repeats |
| Live / cached calls | 246 live / 10 cached |
| Judge model | `qwen3.8:27b` ×256, 0 fallback |
| Self-grading | **0 of 78** LLM promos graded by `gpt-oss-120b` |
| Judge tokens | 273,330 in / 32,618 out |
| Live latency | 12.49 s average |
| Repeat agreement | 79% per-dimension exact (302/384), 99% within 1 point |
| Per-clip all-three exact | **51.6%** (66/128) — the 79% is per dimension, not per clip |
| Rank correlation between passes | 0.90 (LLM 78, final-score formula, capped top list) |
| Top-15 overlap / top-5 overlap | 11/15 / 4/5 |
| Leniency | **72.2%** of the 234 averaged LLM dimension scores are ≥4; 79% only reproduces by pooling raw repeats across all 128 promos including baseline |

---

## 8. Rank — 78 promos

### What it does

`pipeline/rank.py` normalizes each judge score from 1–5 to 0–1, adds screenplay intensity and an early-episode bonus, then sorts. A diversity pass keeps at most one promo per episode in the top list.

```
judge_norm(x) = (x - 1) / 4
final = 0.30*hook + 0.30*cliffhanger + 0.30*clarity + 0.10*intensity + 0.05*entry_bonus
entry_bonus = 0.05 if min(episode) <= 5 else 0
```

There is **no clipping**. The theoretical maximum is 1.05; the observed maximum is 1.0 (E31-P2).

### Worked example — E01-P1

| Component | Raw | Normalized | Weight | Contribution |
|---|---|---|---|---|
| Hook | 5 | 1.000 | 0.30 | 0.3000 |
| Cliffhanger | 4 | 0.750 | 0.30 | 0.2250 |
| Clarity | 5 | 1.000 | 0.30 | 0.3000 |
| Screenplay intensity | 0.467 | 0.467 | 0.10 | 0.0467 |
| Early-episode bonus (Ep 1 ≤ 5) | — | 0.05 | — | 0.0500 |
| **Final** | | | | **0.9217** |

### Baseline comparison on the same formula

E01-B1: hook 5, cliffhanger 4, clarity 5, intensity 0.75, bonus 0.05 → **0.95**. The baseline wins Episode 1 on intensity. This is why the report’s honest reading is “the LLM is better at choosing *where to cut*, not uniformly better.”

---

## 9. Top 15 “post first”

| # | Promo | Window | Len | H/C/Cl | Score |
|---|---|---|---|---|---|
| 1 | E31-P2 | Ep 31 02:14.50–02:40.00 | 25.5 s | 5/5/5 | 1.0000 |
| 2 | E43-P1 | Ep 43 00:03.80–01:00.00 | 56.2 s | 5/5/4.5 | 0.9356 |
| 3 | E32-P1 | Ep 32 01:47.00–02:34.38 | 47.4 s | 5/5/4 | 0.9250 |
| 4 | E01-P1 | Ep 1 00:11.00–01:03.00 | 52.0 s | 5/4/5 | 0.9217 |
| 5 | E13-P1 | Ep 13 00:41.60–01:11.20 | 29.6 s | 5/5/4 | 0.9179 |
| 6 | E02-P1 | Ep 2 00:00.00–00:47.60 | 47.6 s | 5/4/5 | 0.9000 |
| 7 | E33-P1 | Ep 33 00:59.00–01:19.50 | 20.5 s | 5/5/4 | 0.9000 |
| 8 | E45-P1 | Ep 45 00:54.00–01:53.20 | 59.2 s | 5/5/4 | 0.8935 |
| 9 | E16-P1 | Ep 16 00:14.30–00:55.20 | 40.9 s | 5/4/4.5 | 0.8875 |
| 10 | E18-P1 | Ep 18 00:20.10–00:59.20 | 39.1 s | 4.5/5/4 | 0.8750 |
| 11 | E23-P1 | Ep 23 01:26.00–02:11.50 | 45.5 s | 5/5/4 | 0.8750 |
| 12 | E44-P1 | Ep 44 00:11.40–01:10.50 | 59.1 s | 4/5/4.5 | 0.8703 |
| 13 | E29-P2 | Ep 29 00:24.80–00:46.90 | 22.1 s | 4/4.5/5 | 0.8687 |
| 14 | E07-P1 | Ep 7 00:24.50–01:09.50 | 45.0 s | 4/5/5 | 0.8625 |
| 15 | E11-P1 | Ep 11 00:14.30–00:58.00 | 43.7 s | 4/5/4.5 | 0.8558 |

### Why a high-scoring promo can be missing

The cap is one promo per episode. **E31-P1** scores **0.925** (would be #2 or #3 overall) but sits at **#16** because E31-P2 already represents Episode 31. This is the only descending inversion in the list: E11-P1 at #15 (0.8558) is ahead of E31-P1 at #16 (0.925). That is the cap working as designed, not a scoring bug.

**Second run.** An all-qwen run produced a different list: only **2 of these top 5** and **8 of these 15** survive. **E31-P2 is #1 in both runs**, and also #1 in the LLM-2 check. See Appendix C.

---

## 10. Coverage — 49/50

- In the archived run, valid LLM promos cover **49 of 50 episodes**. Episode 42 is the only gap.
- The rules-only baseline covers **50/50**, including E42-B1 (30.1 s). So “49/50” is the LLM pipeline’s coverage, not the whole system’s.
- Cause: E42-P1 was rejected at 17.4 s after the hook move, not repaired. See §3.
- **The gap is model-dependent.** A second all-qwen run covers Ep 42 (E42-P1, 59.9 s, #5) but misses **Ep 33**: E33-P1 started at 100.3 s, the start moved to B064, leaving 60.3 s — 0.3 s over the cap — and was rejected. The stable issue is the hard 60 s boundary, not one episode. See Appendix C.

---

### 10.1 Where it picks badly (verified against the scripts)

**Lowest cold-viewer clarity.** These are all low-ranked valid promos, not top-15 picks:

| Promo | Clarity | Overall rank | What confused the judge |
|---|---|---|---|
| E49-P1 | 2.5 | 76 | Who the “disgraced bride” is, who “her” refers to, why a priest is conspiring |
| E06-P2 | 3.0 | 78 | Who the bearded man is, why he takes the woman to a secluded cottage |
| E17-P1 | 3.0 | 77 | The relationship context and why the man is protective |
| E19-P3 | 3.0 | 74 | Who “Ashburg” is, what “the proof” refers to |
| E07-P2 | 3.0 | 72 | The relationship between the scarred man and Gerald |
| E20-P1 | 3.0 | 69 | Catherine’s relationship to Rupert, the estate politics |
| E09-P1 | 3.0 | 68 | The former groom’s relationship to the nobleman |
| E14-P1 | 3.0 | 67 | What caused the hand injury, who the villain is |
| E33-P3 | 3.0 | 64 | Who Lady Juliana is, why the maid feels guilty |
| E37-P3 | 3.0 | 56 | Who “she” is; the victim is never shown |

**`context_needed` is dead weight.** All **84/84** proposals returned `"low"`. With zero variance it carries no signal, and `rank.py` never reads it.

**Brand safety is only partly a top-list issue.** Ep 31/32 are real: E31-P2 is **#1** and E32-P1 is **#3**, and both use a red-hot iron inches from Juliana’s eye. The script says the iron stops “inches from her eyes” and “mere millimeters from her right eye” — graphic threat, but no contact or injury. Ep 39 is **#47**: the guard is put in a sleeper hold and is explicitly “unconscious,” not killed. Ep 50 is **#63**: the intimate scene is real, but the promo is near the bottom. So “some high-ranking clips” is true for 31/32, false for 39/50.

**The judge is lenient.** 72.2% of the averaged LLM dimension scores are ≥4; 29.1% are ≥4.5. Small gaps near the top are weak evidence.

**Cut edges, precisely.** E04-P2 ends 0.1 s inside B050; E32-P1 starts 0.2 s inside B079. E01-P1 does include Gerald’s “I changed my mind.”; Clarissa’s sting starts 3.5 s after the cut. E47-P1 does not end mid-sentence — the real mid-sentence cut is E04-P2.

**Top-five pattern.** “A cruel or shocking line, then a threat or accusation left hanging” is exact for E31-P2 and E43-P1, partial for E32-P1 (opens on a reply), E01-P1 (ends on a rejection), and E13-P1 (ends on an injury). A looser “cruel/shocking line → unresolved danger or betrayal” fits all five.

---

## 11. Cross-layer numbers

| Metric | Value |
|---|---|
| Screenplays / scenes / beats | 50 / 100 / 3,727 |
| Runtime | 6,162.62 s = 102.71 min |
| Finder logical calls | 50 (50 cached in this archived run) |
| Finder proposals | 84 (1.68 per episode) |
| Validator fix events | 16 on 13 valid promos |
| Rejections | 6 (4 short, 2 duplicate) |
| Valid LLM promos | 78 |
| Baseline generated / judged | 98 / 50 (B1 only) |
| Judge promos / calls | 128 / 256 (246 live, 10 cached) |
| Self-graded LLM promos | 0 / 78 |
| Ranked LLM promos | 78 |
| Top list | 15 (one per episode) |
| LLM coverage | 49 / 50 episodes |
| Tokens | 400,456 in / 116,497 out ≈ **517k total** |
| Wall time | 3,076.2 s = 51.3 min |
| API cost | $0 (self-hosted / local router) |

---

## 12. Verified corrections and limits

These are the places where the short summary or earlier docs overstate what the run supports. The detailed report uses the corrected version.

1. **Fix count is 16 events, not 22.** 8 short + 4 long + 4 hook-moves = 16, on 13 distinct valid promos. All 84 proposals carry 23 notes (16 valid + 7 rejected); “22” matches neither count.
2. **“77/78 end on the cliffhanger” is label-based.** By timestamps it is **76/78**: E04-P2 is 4.0 s past, E06-P2 is 3.2 s past (its `end_beat` is the cliff beat, so the label test hides it).
3. **“Never cuts mid-line” is false.** E04-P2 ends 0.1 s inside B050; E32-P1 starts 0.2 s inside B079. The `END_SLACK_S=3.0` allowance and the snap order let this through.
4. **E47-P1 does not end mid-sentence.** The complete line is B067; the next line is omitted whole. The real mid-sentence cut is E04-P2. The JSON cliffhanger text adds an ellipsis, which is formatting, not a video cut.
5. **E01-P1’s “3 s before the sting” is about Clarissa, not Gerald.** Gerald’s “I changed my mind.” is inside the clip; Clarissa’s line starts 3.5 s after the cut.
6. **The finder’s 50 calls were all cache hits in this archived run.** The live calls happened when the cache was populated. The design is one call per episode; the final run replayed cached responses.
7. **The judge count is 128 promos / 256 calls.** Both are right: 128 promos × 2 repeats. Report prose “×128” counts promos; the usage table counts calls.
8. **Leniency is 72.2%, not 79%**, on the scores actually used (78 LLM promos × 3 averaged dimensions). 79% only reproduces by pooling raw repeats across all 128 clips including baseline.
9. **Repeat agreement 79% is per dimension, not per clip.** Only 51.6% of clips had all three dimensions identical across repeats.
10. **The baseline comparison is asymmetric.** The LLM’s best is chosen from 1–3 judged promos by the same judge; the baseline is B1-only and never judge-selected. Per-episode averages cut the cliffhanger margin from +0.27 to +0.07 and flip hook from +0.11 to −0.04.
11. **The cliffhanger p=0.019 is unadjusted.** With four tests, Holm/Bonferroni threshold is 0.0125; it does not survive correction. Treat it as suggestive.
12. **“Late-episode skew” is not supported by the delivered top 15.** Mean episode 23.2 vs 23.97 for all promos — slightly earlier. Only the top 3 are late. The 0.05 bonus changes no top-15 membership.
13. **Brand safety was overstated.** Ep 31/32 eye imagery is real and high-ranked (#1, #3), but it is graphic threat, not injury. Ep 39’s guard is knocked unconscious, not killed, and that promo ranks **#47**. Ep 50’s intimate scene is real but ranks **#63**.
14. **There is no human gold set.** “Good” currently means “agrees with an LLM judge.” The LLM-2 check in Appendix B is cross-model agreement, not human validation.
15. **The baseline generated 98, not 100.** 48 episodes produce two clips and Episodes 19 and 50 produce one each; only the 50 `B1` clips are judged. The “100” figure would require every episode to produce two.
16. **The missing episode is model-dependent.** The archived `gpt-oss` run misses Ep 42; the all-qwen run covers Ep 42 but misses Ep 33 (60.3 s after repair). The all-qwen run is **self-graded 83/83**, so it is a coverage/finder check, not independent quality evidence. See Appendix C.

---

## Appendix A — Reproducing this run

```bash
# 1. Install dependencies (project uses Anaconda Python 3.12.7 locally)
C:\Users\kunal\anaconda3\python.exe -m pip install -r requirements.txt

# 2. Set provider keys in .env (see .env.example)
#    OLLAMA_BASE_URL + OLLAMA_API_KEY for the judge; FREELLM_API_KEY for the router

# 3. Full 50-episode run (single line in PowerShell)
C:\Users\kunal\anaconda3\python.exe run.py --scripts "C:\Users\kunal\nitish\I Married a Broken Soldier. He was a Duke-scripts (2) (1)" --out outputs/full-run

# 4. A few episodes
C:\Users\kunal\anaconda3\python.exe run.py --scripts "<folder>" --episodes 1-5

# 5. Swap models
C:\Users\kunal\anaconda3\python.exe run.py --scripts "<folder>" --provider ollama --model qwen3.8:27b
C:\Users\kunal\anaconda3\python.exe run.py --scripts "<folder>" --judge-provider openai --judge-model <id>
```

Artifacts per run: `beats.json`, `candidates.json`, `baseline.json`, `promos_ranked.json` / `.csv`, `llm_calls.jsonl`, `run_meta.json`, `report.md`.

---

## Appendix B — LLM-2 robustness check (DeepSeek V4.1 Flash)

This is **not** human validation. It is a second, differently-trained LLM judge used to test whether the Qwen ranking survives a change of model family. The 24-clip packet was stratified 8 top / 6 mid / 6 bottom / 4 baseline, one clip per episode, with ranks, scores, source and episode numbers stripped. Two independent DeepSeek V4.1 Flash passes scored it in fresh contexts; each rater could read only the packet and the rubric, with no repo access and no conversation history. A 4-clip supplement covered the rest of the actual top 5.

### 24-clip packet

| Metric | Qwen | LLM-2 | Delta |
|---|---|---|---|
| Hook mean | 4.08 | 3.48 | −0.60 |
| Cliffhanger mean | 4.08 | 3.23 | −0.85 |
| Clarity mean | 3.96 | 3.75 | −0.21 |
| Composite mean | 4.04 | 3.49 | −0.56 |
| Composite Spearman | — | **0.73** | — |
| Top-10 overlap | — | **6/10** | — |

Stratum separation (LLM-2 composite / would-post):

| Stratum | n | Qwen | LLM-2 | LLM-2 would-post |
|---|---|---|---|---|
| Top | 8 | 4.60 | 3.83 | 94% |
| Mid | 6 | 4.19 | 3.54 | 75% |
| Bottom | 6 | 3.33 | 2.96 | **25%** |
| Baseline | 4 | 3.75 | 3.50 | 75% |

### Top-5 supplement

| Promo | Qwen H/C/Cl | LLM-2 H/C/Cl | Qwen comp | LLM-2 comp |
|---|---|---|---|---|
| E31-P2 | 5/5/5 | 4.5/5/5 | 5.00 | 4.83 |
| E43-P1 | 5/5/4.5 | 4/4/4 | 4.83 | 4.00 |
| E01-P1 | 5/4/5 | 2.75/2.75/4.75 | 4.67 | 3.42 |
| E13-P1 | 5/5/4 | 3.25/3.5/4.25 | 4.67 | 3.67 |

Qwen’s order on these four, using its actual final ranks, is **E31-P2 > E43-P1 > E01-P1 > E13-P1**; LLM-2’s is **E31-P2 > E43-P1 > E13-P1 > E01-P1**. The top two match; E13 and E01 swap. Adding E32-P1, Qwen’s top five is **E31-P2 > E43-P1 > E32-P1 > E01-P1 > E13-P1**, while LLM-2’s is **E31-P2 > E32-P1 > E43-P1 > E13-P1 > E01-P1** (E32-P1 4.33, E01-P1 3.42). Only #1 is stable; the rest reorder, and E01-P1 falls from #4 to #5.

### What this means

- The **rank signal is real**: LLM-2 independently recovers top > mid > bottom, and its would-post rate collapses to 25% on the bottom stratum.
- **Qwen is lenient**, by about +0.56 composite and +0.85 on cliffhanger, confirming the known leniency with a second model family.
- **The exact top order is not fully robust**: top-10 overlap 6/10; E07-P1, E29-P2 and E11-P1 are rated ~1.2 lower by LLM-2. Without humans, it is unresolved whether Qwen overrates them or LLM-2 misses their appeal.
- **Cliffhanger is fragile**: Qwen overrates it most, and LLM-2’s own two passes agree on it only weakly (ρ=0.53; 7/24 exact) while Qwen’s repeats on the same clips are much more stable (ρ=0.91). That weakens any strong claim resting on small cliffhanger gaps.

Files: `outputs/eval-llm2/packet.json`, `key.json`, `comparison.md`, `per_clip.csv`, `supplement_packet.json`, `supplement_key.json`.

---

## Appendix C — Second run: all-qwen (finder + judge)

### C.1 Why this run

The archived run used two different models: `gpt-oss-120b` to find, `qwen3.8:27b` to judge. This second run uses **`qwen3.8:27b` for both stages**. It answers two questions:

1. Does the pipeline still work end-to-end with one model?
2. How much of the top list is the finder’s choice rather than the judge’s?

It is **not** an independent quality evaluation: all 83 LLM promos were judged by the same model that found them. The report itself flags “83 of 83 — these may be scored generously.”

### C.2 Run summary

| Metric | Archived (`gpt-oss` finder) | All-qwen |
|---|---|---|
| Finder / judge | `gpt-oss-120b` / `qwen3.8:27b` | `qwen3.8:27b` / `qwen3.8:27b` |
| Proposed → valid → rejected | 84 → 78 → 6 | **89 → 83 → 6** |
| Valid-promo fix events | 16 | **32** (17 too long, 12 too short, 3 hook moves) |
| Coverage | 49/50, missing **Ep 42** | 49/50, missing **Ep 33** |
| Self-graded LLM promos | 0/78 | **83/83** |
| Judge calls | 256 (10 cached) | 266 (126 cached) |
| Judge repeats identical / within 1 | 79% / 99% | 80% / 99% |
| Dimension scores ≥4 | 72.2% | 75.1% |
| Wall time | 3,076.2 s (51.3 min) | 3,446.2 s (57.4 min) |
| Top-5 / top-10 / top-15 overlap | — | **2/5 / 6/10 / 8/15** |

### C.3 Top 15

| # | Promo | Window | Len | H/C/Cl | Score |
|---|---|---|---|---|---|
| 1 | E31-P2 | Ep 31 02:14.50–02:40.00 | 25.5 s | 5/5/5 | 1.0000 |
| 2 | E01-P1 | Ep 1 00:11.00–00:41.50 | 30.5 s | 5/5/5 | 0.9889 |
| 3 | E15-P1 | Ep 15 00:26.80–01:26.00 | 59.2 s | 4/5/5 | 0.9250 |
| 4 | E02-P1 | Ep 2 00:00.00–00:44.80 | 44.8 s | 5/4/5 | 0.9019 |
| 5 | E42-P1 | Ep 42 00:17.90–01:17.80 | 59.9 s | 4.5/5/4.5 | 0.8983 |
| 6 | E10-P1 | Ep 10 00:02.10–00:39.20 | 37.1 s | 5/4/5 | 0.8900 |
| 7 | E05-P2 | Ep 5 00:06.60–00:29.00 | 22.4 s | 4.5/5/4.5 | 0.8893 |
| 8 | E16-P1 | Ep 16 00:25.80–00:55.20 | 29.4 s | 4/4.5/5 | 0.8875 |
| 9 | E18-P1 | Ep 18 00:00.00–00:28.90 | 28.9 s | 5/4/4.5 | 0.8875 |
| 10 | E32-P1 | Ep 32 00:07.50–00:23.00 + 02:28.00–02:34.38 | 21.9 s | 4.5/5/4 | 0.8875 |
| 11 | E23-P1 | Ep 23 01:18.50–02:11.50 | 53.0 s | 5/5/4 | 0.8850 |
| 12 | E43-P3 | Ep 43 01:08.80–01:52.80 | 44.0 s | 5/5/4 | 0.8767 |
| 13 | E12-P2 | Ep 12 00:43.70–01:27.21 | 43.5 s | 5/4/5 | 0.8700 |
| 14 | E47-P1 | Ep 47 01:14.80–02:11.50 | 56.7 s | 5/3.5/5 | 0.8628 |
| 15 | E11-P1 | Ep 11 00:58.00–01:52.75 | 54.8 s | 4/5/4 | 0.8500 |

### C.4 What changed

- **E31-P2 is #1 in both runs**, and also #1 in the LLM-2 check. It is the only pick that survives every configuration.
- **E01-P1 rises #4 → #2**, with a tighter 30.5 s cut instead of 52.0 s, and a 5/5/5 judge score instead of 5/4/5.
- **E43-P1 (#2 archived) becomes E43-P3 (#12)** — the qwen finder chose a different segment in the same episode.
- **E32-P1 falls #3 → #10** and becomes a 2-segment stitch (7.5–23.0 s + 148.0–154.38 s).
- **E13-P1 (#5 archived) falls out of the top 15.**
- New entrants: **E15-P1 (#3), E42-P1 (#5), E10-P1 (#6), E05-P2 (#7), E12-P2 (#13), E47-P1 (#14).**

Overlap: **2/5 top five, 6/10 top ten, 8/15 top fifteen**. Seven of the fifteen entries change when only the finder model changes.

### C.5 Coverage flips: Ep 42 fixed, Ep 33 broken

- **Ep 42 is covered.** E42-P1 runs 17.9–77.8 s (59.9 s), judged 4.5/5/4.5, and ranks #5. The qwen finder found a candidate that survived validation; the archived gpt-oss candidate was rejected at 17.4 s.
- **Ep 33 is the new gap.** E33-P1 started at 100.3 s; the validator moved the start to B064, leaving 60.3 s — **0.3 s over the 60 s cap** — and rejected it. There was no other Ep33 candidate.
- So “Ep 42 is missing” is **finder-specific**, not a fixed pipeline bug. The stable issue is the hard 60 s boundary.

### C.6 Quality and the self-grading problem

- **83/83 LLM promos were judged by `qwen3.8:27b`**, the same model that found them. The report says: “these may be scored generously.” This is the main reason the all-qwen scores are not independent evidence.
- Judge repeats were identical 80% of the time (per dimension) and within 1 point 99% of the time.
- 75.1% of the averaged LLM dimension scores are ≥4, slightly more lenient than the archived 72.2%.
- Baseline comparison: LLM wins **30 of 49** episodes (p = 0.079). Hook +0.13 (p = 0.185), cliffhanger +0.20 (p = 0.099), clarity **+0.27 (p = 0.002)**. Clarity is the only dimension that survives correction (three tests, Holm threshold 0.0167), but it is also the dimension most exposed to self-grading. Treat it as suggestive.

### C.7 Usage

| Stage | Calls | Live | Cached | Avg live latency | Tokens in / out |
|---|---|---|---|---|---|
| Finder | 50 | 47 | 3 | 35.80 s | 148,187 / 19,127 |
| Judge | 266 | 140 | 126 | 12.55 s | 289,582 / 33,838 |

Total: 437,769 input / 52,965 output tokens; 3,446.2 s (57.4 min); **$0** on local/self-hosted hardware.

### C.8 Verdict

- **E31-P2 is robust** across two finders and the blinded LLM-2 judge.
- The rest of the top list is **finder-dependent**: change the finder model and 7 of 15 entries change.
- The all-qwen run is a **coverage and finder-sensitivity experiment**, not a clean quality evaluation. To isolate judge bias, run the qwen finder with a **different** judge on the same 83 candidates.

---

*Report generated from the archived full run. All timestamps are seconds from episode start; all scores are on the run’s 1–5 judge scale unless normalized to 0–1.*
