# Dataset

The input data and what the pipeline derives from it: the screenplay format, the beat unit, the cheap signals code
computes, and the promo knowledge written into the prompts. Where the data comes from: [SOURCES.md](SOURCES.md).

## Screenplay format (input)

One `.txt` per episode. Header lines, then scenes made of timed blocks:

```
EPISODE NUMBER: Episode 1
EPISODE LOGLINE: ...
CONTINUITY NOTES: ...
SCENE 01
**MATRIARCH (Cold, Commanding):**
Start: (00:11.30) | End: (00:13.10)
"You should turn around, Juliana."
```

Block labels: `CAMERA`, `ACTION`, `SOUND`/`SFX`/`MUSIC`, or a speaker with optional `(O.S.)`/`(V.O.)` and tone tags.
Parsed by `pipeline/parse.py`; the parser is tolerant of case, spacing and missing headers.

## Beat (the unit everything else uses)

`id` (`E01-B008`), `episode`, `index`, `type` (dialogue / action / camera / sfx), `speaker`, `tags`, `text`,
`start`, `end`, `scene`, plus three signals computed by code, no LLM:

| Signal | How it is computed |
|---|---|
| `intensity` 0-3 | tone tags matched against a list of strong tones (furious, menacing, begging, ...) + 1 for `!` in dialogue |
| `physical` | action/camera text matches slap, strike, kneel, blade, fire, iron, poison, ... |
| `cliff_cue` | sound/camera/action text matches "cliffhanger", "cut to black", "sting", "freeze", ... |

The word lists are `STRONG_TONES`, `PHYSICAL_RE` and `CLIFF_RE` in `pipeline/parse.py`.

## Promo knowledge (in the prompts, `pipeline/prompts.py`)

**A good promo** (finder prompt): a hook in the first 3 s; ends on a cliffhanger before the answer; understandable to a
stranger; 20-60 s (25-45 ideal); one stretch preferred, up to two joined from the same episode.

**Patterns and their weights** the finder is told about: betrayal or shocking reveal (3), identity reveal / power
reversal (3), humiliation of the heroine (2), violence / slap / physical threat (2), rescue / protective hero (2),
ultimatum or impossible choice (2), forbidden romance / intimacy (1), cliffhanger ending (2).

**Judge rubric**: hook, cliffhanger and clarity each scored 1-5 with an anchor for 1, 3 and 5. The judge sees only the
clip transcript (dialogue, on-screen action and shots, sounds, seconds from clip start).

## Rules enforced by code (`pipeline/validate.py`, values in `configs/config.yaml`)

20-60 s total; hook beat within 3 s of the start; end at the cliffhanger beat (up to 3 s slack); cuts never inside a
spoken line; start snaps back up to 1 s and end forward up to 1.5 s to shot edges; duplicates (overlap above 60%)
rejected.
