# LLM-2 Evaluation — DeepSeek V4.1 Flash

**A second, blinded LLM judge used to test whether the Qwen ranking survives a change of model family.**

> **What this is:** a robustness check. A different model family scored the same clips, blind, on the same 1–5 rubric.
>
> **What this is not:** human validation. LLM-2 is an LLM, not a viewer. Agreement between two LLMs is evidence about the ranking, not proof that either matches an audience.

**At a glance**

| Item | Value |
|---|---|
| Rater | DeepSeek V4.1 Flash (two independent passes) |
| Clips | 24 in the main packet + 4 in the top-5 supplement |
| Blinding | No ranks, scores, source, promo IDs, or episode numbers |
| Main result | Composite **Spearman 0.73**, top-10 overlap **6/10** |
| Leniency | LLM-2 is **0.56 points harsher** on the 5-point composite |
| Rank signal | LLM-2 recovers top > mid > bottom; bottom would-post rate **25%** |
| Weak spot | Cliffhanger: Qwen overrates it, and LLM-2 agrees with itself only weakly (ρ=0.53) |
| Human gold set | **Still missing** — this document does not replace it |

---

## 1. Why run this at all?

The main run uses one judge, `qwen3.8:27b`, for every clip. That is good for comparability: one model, one rubric, two repeats. But it leaves two questions open:

1. **Is the ranking Qwen-specific?** If another model family ranks the same clips similarly, the signal is less likely to be an artifact of one model.
2. **Is Qwen too generous?** Qwen gives 4 or 5 to 72% of the averaged LLM dimension scores. A second model with no knowledge of Qwen’s scores can test whether that leniency is shared.

LLM-2 answers those two questions. It does **not** answer “is this a good promo for a real viewer?” — only humans (or real ad performance) can answer that.

---

## 2. The design

### 2.1 Main packet: 24 clips

The packet was built from the archived full run (`outputs/full-run/`):

| Stratum | How many | Where they come from |
|---|---|---|
| Top | 8 | Qwen overall ranks 1–15 |
| Mid | 6 | ranks 16–50 |
| Bottom | 6 | ranks 51–78 |
| Baseline | 4 | rules-only `B1` promos |

- **One clip per episode** (24 distinct episodes), so a rater cannot learn the story across clips.
- **Fixed random seed 42**, so the sample is reproducible.
- **Why stratified, not random?** A random sample of 24 would be dominated by mid-ranked clips. Stratifying forces the packet to span the full quality range, which is what a rank-correlation test needs.
- **Why the supplement?** The random top stratum included only one of the actual top five (E32-P1). A separate 4-clip supplement covered E31-P2, E43-P1, E01-P1, and E13-P1 so the head of the list could be checked.

### 2.2 What the rater saw

Each packet entry contained only:

```json
{
  "clip_id": "C04",
  "duration_s": 45.0,
  "transcript": "[ 0.0s] (on screen) Medium shot of Gerald...\n[ 0.5s] GERALD ..."
}
```

Removed: overall rank, Qwen score, source (LLM vs baseline), promo ID, episode number, hook, cliffhanger, why-it-works, finder model, judge metadata.

The transcript was built with the **same** `pipeline.judge.clip_transcript()` function the Qwen judge used, so both models saw the same text.

### 2.3 What stayed private

`outputs/eval-llm2/key.json` maps each `Cxx` back to its promo ID, stratum, rank, and Qwen scores. It was **not** placed in the rater’s directory. The raters could read only `packet.json` and `rubric.md`.

### 2.4 Two passes

Two independent DeepSeek V4.1 Flash sessions scored the same packet in separate temp directories. Neither saw the other’s scores, the repo, or this conversation. The two passes are averaged, matching Qwen’s two-repeat design.

**Meta-instructions given to each rater (exact rules):**

```text
Read ONLY packet.json and rubric.md.
Do NOT read, list, search, or inspect any other file or directory.
Do not open the promo-finder repo. Do not use prior knowledge about this task,
the show, or any evaluation. Judge only the transcripts in packet.json.
There are 24 clips, each from a different episode, shuffled. You do not know
their ranks, scores, source, or episode numbers. That is intentional.
Use the whole scale. Do not cluster scores at 4-5; if a clip is ordinary,
score it ordinary. Judge only what a cold US TikTok viewer would perceive.
Write valid JSON to scores.json.
```

---

## 3. The exact LLM-2 prompt

This is `outputs/eval-llm2/rubric.md`, used verbatim:

```text
You are a typical US viewer scrolling TikTok. You have NEVER seen this show and know nothing
about it. You will read the transcript of one short video clip: dialogue and visible action, in order, with
seconds from the clip start. Speaker labels are how the characters would look on screen to you.

Judge each clip honestly and use the whole scale (1-5; half points allowed).
- hook (1-5): do the first 3 seconds make you stop scrolling?
  5 = shocking line/action instantly; 3 = mildly intriguing; 1 = nothing happens, you scroll on.
- cliffhanger (1-5): does it cut at a moment that leaves you needing to know what happens next?
  5 = cut mid-crisis, you must know what happens; 3 = some open question; 1 = resolved or just fizzles out.
- clarity (1-5): with zero background, can you follow it? You do NOT need names or full backstory - promos
  rarely give that. Judge whether the core situation and stakes are clear.
  5 = instantly obvious who is the victim, who is the villain and what is at stake;
  3 = you get the gist of the conflict but key relationships or stakes are fuzzy;
  1 = you cannot tell what is going on or why it matters.
- would_post (true/false): if you ran the show's account, would you post this clip as an ad?
- safety (safe | caution | unsafe): would Instagram/TikTok likely restrict it for violence, gore,
  sexual content or other brand-safety reasons?

Do not use outside knowledge. Judge ONLY the transcript in front of you. Do not reward a clip for being
from a later episode; you do not know the episode number.

Return ONLY valid JSON:
{"scores": [
  {"clip_id": "C01",
   "hook": 1, "cliffhanger": 1, "clarity": 1,
   "would_post": true,
   "safety": "safe",
   "summary": "<one sentence: what is happening>",
   "confusing": "<what is unclear, or 'nothing'>",
   "want_next": "<the question you are left with, or 'nothing'>",
   "would_watch_next_episode": true}
]}
```

**What is comparable:** `hook`, `cliffhanger`, `clarity` are the same 1–5 dimensions Qwen scored. `would_post` and `safety` are extra flags; Qwen only had `would_watch_next_episode`.

**Output shape:** one JSON object per clip, keyed by `clip_id`, written to `scores.json`. Half points are allowed; the model used them.

---

## 4. The Qwen prompt, for comparison

Qwen saw the same transcript, with no episode number, but with the main run’s system prompt:

```text
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

Qwen’s user message was:

```text
CLIP ({duration} seconds):
{clip}
```

Qwen judged each clip **twice** and averaged. For E32-P1 (`C01`), both repeats were identical: hook 5, cliffhanger 5, clarity 4. For E07-P1 (`C04`), both repeats were also identical: 4/5/5. Qwen’s repeat stability is much higher than LLM-2’s; see §8.6.

---

## 5. Worked example 1 — consensus: `C01` = E32-P1

**Why this clip:** both models rate it high, so it shows what agreement looks like.

### What the rater saw

```text
[ 0.0s] (on screen) Close-up of Catherine throwing her hands up in explosive defensiveness.
[ 0.2s] CATHERINE (Shouting, Outraged): "And what is wrong with that?!"
[ 1.8s] (on screen) Close-up of Catherine's face twisting in absolute venom.
[ 2.4s] (on screen) Close-up of Juliana looking serene.
[ 2.5s] JULIANA (Gentle, Penetrating): "Nothing. Until you have nothing left beneath it."
[ 5.5s] (on screen) Medium shot of Catherine standing motionless, holding the iron rod, struck to the core by the insult.
[ 5.8s] JULIANA (Unrelenting): "You have spent your whole life collecting things that make people bow..."
[ 9.0s] (on screen) Low-angle shot of Juliana's chained hands folded peacefully in her lap.
[ 9.8s] (on screen) Medium close-up of Juliana looking up with quiet pity.
[ 9.9s] JULIANA (Piercing): "...but you have never learned how to make anyone love you."
[12.5s] (on screen) Medium shot of Catherine snapping entirely, raising the branding poker like a weapon and screaming.
[12.6s] CATHERINE (Hysterical, Screaming): "Silence! Silence!"
[14.8s] (on screen) Close-up of Catherine's crazed, gasping face.
[14.8s] CATHERINE (Shrieking): "Why?!"
[15.8s] (on screen) Close-up of Juliana crying out her defiance.
[16.0s] JULIANA (Forceful): "Because I am right!"
[18.0s] (on screen) Low-angle tracking shot of the red-hot branding tip trailing across the wet dungeon floor, steaming.
[18.4s] JULIANA (Scathing, Direct): "You want everyone to believe you are powerful."
[21.5s] (on screen) Medium shot of Juliana sitting under the cold skylight bars, her posture majestic despite her imprisonment.
[22.0s] JULIANA (Continuing): "You want everyone to fear you."
[24.8s] (on screen) Medium shot of Juliana looking directly at Catherine, gestures restrained by the heavy iron chains.
[25.0s] JULIANA (Mocking, Direct): "But look at you."
[27.8s] (on screen) Close-up of Juliana, her eyes burning with fiery contempt.
[28.0s] JULIANA (Stripping Her Bare): "You have to threaten a chained woman to feel powerful!"
[31.5s] (on screen) Close-up of Catherine trembling with uncontrollable rage, teeth bared.
[31.6s] CATHERINE (Choking with Rage): "You insolent—!"
[33.4s] (on screen) Medium shot of Catherine gripping the glowing tongs as Juliana continues speaking over her.
[33.4s] JULIANA (Steely, Triumphant): "You may have the title you have always wanted..."
[35.4s] (on screen) Close-up of Juliana delivering the final emotional blow.
[35.4s] JULIANA (Final, Condemning): "...but you will never have the courage to earn what you demand from everyone else."
[39.5s] (on screen) Close-up of Catherine's face twitching with sheer murderous madness.
[39.6s] CATHERINE (Enraged, Shouting): "You think you can lecture me?!"
[41.0s] (on screen) Medium shot of Catherine raising the branding iron high above her head with both hands.
[41.0s] (on screen) Catherine hoists the searing branding rod over Juliana with frantic fury.
[41.1s] CATHERINE (Screaming, Maniacal): "Then let's see how brave you are when it touches your skin!"
[43.8s] (on screen) Medium shot of Catherine plunging the glowing orange poker straight toward Juliana's face.
[44.2s] (on screen) Juliana gasps, freezing as the glowing tip of the iron thrusts forward, stopping mere millimeters from her right eye.
[45.0s] (on screen) Extreme close-up of Juliana's wide, unblinking blue eye. The intense, fiery orange glow of the iron poker radiates inches from her cornea, holding on the heart-stopping cliffhanger as the frame cuts to black.
```

### The scores

| Source | Hook | Cliffhanger | Clarity | Composite | Would post | Safety |
|---|---|---|---|---|---|---|
| Qwen (avg of 2) | 5 | 5 | 4 | 4.67 | — | — |
| LLM-2 pass 1 | 3.5 | 5 | 4.5 | 4.33 | yes | caution |
| LLM-2 pass 2 | 4.5 | 4 | 4.5 | 4.33 | yes | caution |
| **LLM-2 average** | **4.0** | **4.5** | **4.5** | **4.33** | **yes** | **caution** |
| Delta (LLM-2 − Qwen) | −1.0 | −0.5 | +0.5 | **−0.33** | | |

### What each model “said”

**LLM-2 pass 1** (score 3.5/5/4.5):

> “A chained Juliana calmly tears apart Catherine’s self-worth, driving Catherine into a frenzy until she thrusts a red-hot branding iron at Juliana’s eye.”
>
> Confusing: “Why Juliana is chained and what Catherine is trying to get from her; the clip starts mid-argument.”
>
> Want next: “Does Catherine burn her, and can Juliana survive?”

**LLM-2 pass 2** (score 4.5/4/4.5):

> “A chained woman calmly dismantles her wealthy captor’s self-worth until the captor snaps and raises a red-hot branding iron at her.”
>
> Confusing: “Why Juliana is chained and exactly who Catherine is to her.”
>
> Want next: “Does Catherine brand her, and can Juliana break her captor’s nerve first?”

**Why both agree:** the first line is a shouted confrontation, the power reversal is legible (chained prisoner verbally destroying her captor), and the clip ends on a hot iron inches from an eye. Even with the missing backstory, the victim, villain, and stakes are clear.

**Why LLM-2 is harsher on hook:** it read the opening as “mid-argument” rather than a self-contained shock; Qwen gave the shouted “And what is wrong with that?!” a 5. That is a real judgment difference, not a data error.

---

## 6. Worked example 2 — disagreement: `C04` = E07-P1

**Why this clip:** it has the largest gap in the packet (−1.25 composite). It shows exactly where a second model family disagrees.

### What the rater saw

```text
[ 0.0s] (on screen) Medium shot of Gerald standing beside Aristocratic Woman, sneering disdainfully.
[ 0.5s] GERALD (Arrogant, Scornful): "A fitting home for a woman who threw away everything for a penniless soldier."
[ 5.3s] (on screen) Medium close-up of Juliana, defiant and unflinching despite her soiled dress and damp hair.
[ 5.5s] JULIANA (Sharp, Unintimidated): "You came all this way just to insult my home?"
[ 8.3s] (on screen) Close-up of Aristocratic Woman erupting into high-pitched, malicious laughter beneath her parasol.
[ 8.7s] ARISTOCRATIC WOMAN (Gloating, Mocking): "Home? Look at your hands, Juliana."
[13.3s] (on screen) Close-up of Juliana's mud-stained palms held open against her apron.
[13.7s] ARISTOCRATIC WOMAN (Cruel): "You look like a servant."
[15.3s] (on screen) Close-up of Gerald's smug expression watching Juliana.
[16.5s] (on screen) Medium close-up of Juliana lifting her chin with unwavering dignity.
[16.7s] JULIANA (Proud, Resolute): "I work with my hands. There is no shame in that."
[20.5s] (on screen) Close-up on Gerald's tightening jaw.
[20.7s] GERALD (Biting, Condescending): "You were born a lady."
[22.5s] (on screen) Close-up on Juliana's clear blue eyes, shining with unbroken pride.
[24.3s] JULIANA (Firm, Unapologetic): "And I remain one."
[26.3s] (on screen) Wide shot framing Juliana facing off against Gerald and Aristocratic Woman in the bleak courtyard.
[27.0s] GERALD (Bitter, Sneering): "You chose that scarred beggar over a life of comfort."
[30.3s] (on screen) Two-shot profile of Juliana looking straight into Gerald's eyes without flinching.
[33.3s] JULIANA (Passionate, Defiant): "I chose a man who stood beside me when you walked away."
[37.0s] (on screen) Intense close-up of Juliana dismissing him with utter contempt.
[37.3s] JULIANA (Cold, Commanding): "You have no authority here. Leave."
[40.7s] (on screen) Close-up of Gerald lunging forward, aggressively pointing his finger into Juliana's face.
[41.1s] GERALD (Furious, Threatening): "I have enough influence to make a beggar disappear."
[44.1s] GERALD (Spiteful, Boastful): "And your husband?"
```

### The scores

| Source | Hook | Cliffhanger | Clarity | Composite | Would post | Safety |
|---|---|---|---|---|---|---|
| Qwen (avg of 2) | 4 | 5 | 5 | 4.67 | — | — |
| LLM-2 pass 1 | 3.5 | 4 | 4 | 3.83 | yes | safe |
| LLM-2 pass 2 | 2.5 | 3 | 3.5 | 3.00 | no | safe |
| **LLM-2 average** | **3.0** | **3.5** | **3.75** | **3.42** | **split** | **safe** |
| Delta (LLM-2 − Qwen) | −1.0 | −1.5 | −1.25 | **−1.25** | | |

### What each model “said”

**Qwen** (4/5/5): a cruel public humiliation followed by a threat. It read the final “I have enough influence to make a beggar disappear. And your husband?” as a strong unresolved threat.

**LLM-2 pass 1** (3.5/4/4):

> “Gerald and an aristocratic woman mock Juliana for her poverty and her marriage to a poor soldier, until Gerald threatens to make her husband disappear.”
>
> Confusing: “Why Gerald and the woman care enough to travel there and torment her.”
>
> Want next: “What is Gerald planning to do to Juliana’s husband?”

**LLM-2 pass 2** (2.5/3/3.5):

> “A sneering ex and his new noblewoman mock a woman for her poverty and dirty hands; she stands her ground and orders them out.”
>
> Confusing: “Who Gerald and the aristocratic woman are beyond being former in-laws.”
>
> Want next: “Does Gerald escalate after she tells him to leave?”

**Why the gap:** Qwen weighted the final threat heavily; LLM-2 pass 1 saw it too, but pass 2 summarized the clip as a dismissal (“orders them out”) and gave the cliffhanger a 3. That is a **reading difference on the same text**, and it is exactly why one LLM judge cannot be treated as ground truth. A human labeling pass would decide whether the last line lands as a threat or as a weak tail.

---

## 7. All 24 clips — exact values

`Rank*`: for LLM promos, the overall rank in the 78-promo list; for baseline promos, the rank within the 50 B1 promos. `H/C/Cl` = hook / cliffhanger / clarity. `Composite` = mean of the three.

### 7.1 Qwen vs LLM-2 averages

| Clip | Promo | Stratum | Rank* | Qwen H/C/Cl | Qwen comp | LLM-2 avg H/C/Cl | LLM-2 comp | Delta |
|---|---|---|---|---|---|---|---|---|
| C01 | E32-P1 | top | 3 | 5/5/4 | 4.67 | 4/4.5/4.5 | 4.33 | −0.33 |
| C02 | E29-P2 | top | 13 | 4/4.5/5 | 4.50 | 2.75/3.25/4 | 3.33 | −1.17 |
| C03 | E16-P1 | top | 9 | 5/4/4.5 | 4.50 | 4.5/3/4 | 3.83 | −0.67 |
| C04 | E07-P1 | top | 14 | 4/5/5 | 4.67 | 3/3.5/3.75 | 3.42 | −1.25 |
| C05 | E20-P2 | bottom | 57 | 3.5/3.5/4 | 3.67 | 3.25/3.25/3.75 | 3.42 | −0.25 |
| C06 | E35-P1 | mid | 34 | 4/5/4 | 4.33 | 3/4.25/3.25 | 3.50 | −0.83 |
| C07 | E01-P2 | mid | 20 | 4.5/4/5 | 4.50 | 3.75/3.25/4.25 | 3.75 | −0.75 |
| C08 | E23-B1 | baseline | 19 | 4/5/4 | 4.33 | 3.25/4.5/4 | 3.92 | −0.42 |
| C09 | E28-P2 | mid | 44 | 4/3/4.5 | 3.83 | 3.25/2.5/4 | 3.25 | −0.58 |
| C10 | E09-P1 | bottom | 68 | 3/4/3 | 3.33 | 2.5/3.5/2.5 | 2.83 | −0.50 |
| C11 | E15-B1 | baseline | 27 | 4/4/4 | 4.00 | 3/3.5/4.5 | 3.67 | −0.33 |
| C12 | E33-P1 | top | 7 | 5/5/4 | 4.67 | 3.75/3.75/3.75 | 3.75 | −0.92 |
| C13 | E14-P1 | bottom | 67 | 3/4/3 | 3.33 | 1.75/2.25/3.5 | 2.50 | −0.83 |
| C14 | E11-P1 | top | 15 | 4/5/4.5 | 4.50 | 2.75/3.25/4 | 3.33 | −1.17 |
| C15 | E25-B1 | baseline | 45 | 4/3/3 | 3.33 | 3.5/2.5/3.75 | 3.25 | −0.08 |
| C16 | E37-P1 | bottom | 65 | 3.5/2.5/4 | 3.33 | 2.75/1.75/3 | 2.50 | −0.83 |
| C17 | E46-P1 | mid | 45 | 4/4/4 | 4.00 | 3.5/2.75/3 | 3.08 | −0.92 |
| C18 | E49-P1 | bottom | 76 | 3.5/2/2.5 | 2.67 | 3.25/2.25/2.5 | 2.67 | 0.00 |
| C19 | E30-B1 | baseline | 46 | 3.5/4/2.5 | 3.33 | 3.75/3/2.75 | 3.17 | −0.17 |
| C20 | E24-P1 | mid | 27 | 4.5/4/4 | 4.17 | 5/2.5/4 | 3.83 | −0.33 |
| C21 | E26-P2 | bottom | 58 | 4/3.5/3.5 | 3.67 | 4/3.25/4.25 | 3.83 | +0.17 |
| C22 | E02-P1 | top | 6 | 5/4/5 | 4.67 | 4.25/3.25/4.75 | 4.08 | −0.58 |
| C23 | E45-P1 | top | 8 | 5/5/4 | 4.67 | 5/4.5/4.25 | 4.58 | −0.08 |
| C24 | E21-P1 | mid | 26 | 4/5/4 | 4.33 | 4/3.5/4 | 3.83 | −0.50 |

### 7.2 The two passes and the binary labels

| Clip | Promo | Pass 1 H/C/Cl | Pass 2 H/C/Cl | Post P1 | Post P2 | Safety P1 | Safety P2 |
|---|---|---|---|---|---|---|---|
| C01 | E32-P1 | 3.5/5/4.5 | 4.5/4/4.5 | yes | yes | caution | caution |
| C02 | E29-P2 | 2.5/3/4 | 3/3.5/4 | yes | yes | safe | safe |
| C03 | E16-P1 | 4.5/3.5/4 | 4.5/2.5/4 | yes | yes | caution | caution |
| C04 | E07-P1 | 3.5/4/4 | 2.5/3/3.5 | yes | no | safe | safe |
| C05 | E20-P2 | 3/2.5/3.5 | 3.5/4/4 | no | yes | safe | safe |
| C06 | E35-P1 | 3/4/3 | 3/4.5/3.5 | no | yes | safe | safe |
| C07 | E01-P2 | 4/3/4.5 | 3.5/3.5/4 | yes | yes | safe | safe |
| C08 | E23-B1 | 3.5/4.5/4 | 3/4.5/4 | yes | yes | safe | safe |
| C09 | E28-P2 | 3.5/2.5/4 | 3/2.5/4 | no | yes | safe | safe |
| C10 | E09-P1 | 2.5/3.5/2.5 | 2.5/3.5/2.5 | no | no | safe | safe |
| C11 | E15-B1 | 3/3.5/4.5 | 3/3.5/4.5 | yes | yes | safe | safe |
| C12 | E33-P1 | 4/4/4 | 3.5/3.5/3.5 | yes | yes | caution | safe |
| C13 | E14-P1 | 2/3/3.5 | 1.5/1.5/3.5 | no | no | caution | safe |
| C14 | E11-P1 | 3/3.5/4 | 2.5/3/4 | yes | yes | safe | safe |
| C15 | E25-B1 | 3.5/2.5/3.5 | 3.5/2.5/4 | no | yes | safe | safe |
| C16 | E37-P1 | 3.5/2/3 | 2/1.5/3 | no | no | safe | safe |
| C17 | E46-P1 | 3.5/3/2.5 | 3.5/2.5/3.5 | no | yes | safe | safe |
| C18 | E49-P1 | 3/2/2.5 | 3.5/2.5/2.5 | no | no | safe | safe |
| C19 | E30-B1 | 4/3/3 | 3.5/3/2.5 | yes | no | caution | safe |
| C20 | E24-P1 | 5/3/4 | 5/2/4 | yes | yes | caution | caution |
| C21 | E26-P2 | 4/2.5/4 | 4/4/4.5 | yes | yes | safe | safe |
| C22 | E02-P1 | 4.5/3/4.5 | 4/3.5/5 | yes | yes | safe | safe |
| C23 | E45-P1 | 5/5/4 | 5/4/4.5 | yes | yes | safe | safe |
| C24 | E21-P1 | 4/3.5/3.5 | 4/3.5/4.5 | yes | yes | safe | safe |

**Reading the tables:** a negative Delta means LLM-2 scored the clip lower than Qwen. The largest gaps are C04 (−1.25), C02 and C14 (−1.17 each). The only positive gaps are C21 (+0.17) and C18 (0.00); every other clip is lower.

---

## 8. Aggregate results

### 8.1 Means and agreement

| Dimension | Qwen mean | LLM-2 mean | Mean delta | Spearman | MAE | Exact | Within 1 |
|---|---|---|---|---|---|---|---|
| Hook | 4.08 | 3.48 | −0.60 | 0.73 | 0.67 | 3/24 | 20/24 |
| Cliffhanger | 4.08 | 3.23 | −0.85 | 0.80 | 0.88 | 0/24 | 16/24 |
| Clarity | 3.96 | 3.75 | −0.21 | 0.54 | 0.50 | 4/24 | 23/24 |
| **Composite** | **4.04** | **3.49** | **−0.56** | **0.73** | **0.57** | — | **21/24** |

### 8.2 What the metrics mean

| Metric | Plain meaning | How to read this result |
|---|---|---|
| **Spearman** | Do the two judges rank the clips in the same order? 1.0 = same order, 0 = no relationship | 0.73 composite is moderate-to-strong. The ordering is related, not identical. |
| **MAE** | Average points the two judges differ by, on the 1–5 scale | 0.57 composite; 0.88 on cliffhanger is the largest. |
| **Exact** | Same score to the decimal | Rare, because both models use half points. 3/24 on hook, 0/24 on cliffhanger. |
| **Within 1** | Scores no more than 1 point apart | 21/24 composite. The disagreement is mostly about level, not direction. |
| **Top-10 overlap** | How many of the two top-10 lists are the same clips | 6/10. Four of ten top clips differ — the exact posting order is not robust. |
| **Delta** | LLM-2 minus Qwen; negative = harsher | −0.56 composite; LLM-2 is systematically stricter. |

### 8.3 The rank signal is still there

| Stratum | n | Qwen composite | LLM-2 composite | LLM-2 would-post | Qwen would-watch-next |
|---|---|---|---|---|---|
| Top | 8 | 4.60 | 3.83 | 94% | 100% |
| Mid | 6 | 4.19 | 3.54 | 75% | 100% |
| Bottom | 6 | 3.33 | 2.96 | **25%** | 83% |
| Baseline | 4 | 3.75 | 3.50 | 75% | 100% |

LLM-2 recovers the ordering **top > mid > bottom** and its would-post rate collapses to 25% on the bottom stratum. That is the strongest evidence that the Qwen ranking contains real signal rather than noise.

### 8.4 Top-10 sets within the 24 clips

**Qwen:** C01, C04, C12, C22, C23, C02, C03, C07, C14, C06

**LLM-2:** C23, C01, C22, C08, C03, C20, C21, C24, C07, C12

**Overlap:** C01, C03, C07, C12, C22, C23 = **6/10**.

Notable: LLM-2 promotes **C23/E45-P1** to #1 and **C08/E23-B1** (a baseline promo) to #4; Qwen keeps **C04/E07-P1** at #2, while LLM-2 drops it to the middle. These are the disagreements a human set would need to settle.

### 8.5 Biggest disagreements

| Clip | Promo | Stratum | Qwen | LLM-2 | Delta |
|---|---|---|---|---|---|
| C04 | E07-P1 | top | 4.67 | 3.42 | −1.25 |
| C02 | E29-P2 | top | 4.50 | 3.33 | −1.17 |
| C14 | E11-P1 | top | 4.50 | 3.33 | −1.17 |
| C12 | E33-P1 | top | 4.67 | 3.75 | −0.92 |
| C17 | E46-P1 | mid | 4.00 | 3.08 | −0.92 |
| C13 | E14-P1 | bottom | 3.33 | 2.50 | −0.83 |
| C16 | E37-P1 | bottom | 3.33 | 2.50 | −0.83 |
| C06 | E35-P1 | mid | 4.33 | 3.50 | −0.83 |

### 8.6 Self-consistency on the same 24 clips

| Dimension | Qwen exact | Qwen within 1 | Qwen ρ | LLM-2 exact | LLM-2 within 1 | LLM-2 ρ |
|---|---|---|---|---|---|---|
| Hook | 18/24 | 24/24 | 0.72 | 10/24 | 23/24 | 0.76 |
| Cliffhanger | 20/24 | 24/24 | **0.91** | 7/24 | 21/24 | **0.53** |
| Clarity | 18/24 | 24/24 | 0.84 | 12/24 | 24/24 | 0.74 |

This is the most important robustness finding:

- Qwen is highly stable on cliffhanger (ρ=0.91), but LLM-2 is not (ρ=0.53). The dimension the headline evaluation depends on most is the one where a second model family is least stable.
- LLM-2 is harsher on cliffhanger than Qwen (−0.85), and its two passes disagree on 17 of 24 clips by any amount (7 exact).
- Hook is the most agreed dimension between the two models (ρ=0.73; within 1 on 20/24).
- Clarity has the smallest mean gap (−0.21) but weak rank agreement (ρ=0.54) because both models cluster around 3.5–4.5; small differences are noise.

---

## 9. Top-5 supplement

The main packet included only **one** of the actual top five (E32-P1). The supplement covered the other four so the head of the list could be checked.

| Promo | Qwen H/C/Cl | Qwen comp | LLM-2 H/C/Cl | LLM-2 comp | Delta |
|---|---|---|---|---|---|
| E31-P2 | 5/5/5 | 5.00 | 4.5/5/5 | 4.83 | −0.17 |
| E43-P1 | 5/5/4.5 | 4.83 | 4/4/4 | 4.00 | −0.83 |
| E01-P1 | 5/4/5 | 4.67 | 2.75/2.75/4.75 | 3.42 | −1.25 |
| E13-P1 | 5/5/4 | 4.67 | 3.25/3.5/4.25 | 3.67 | −1.00 |

### The actual top five, side by side

**Qwen (full run):**

1. E31-P2 — 5.00
2. E43-P1 — 4.83
3. E32-P1 — 4.67
4. E01-P1 — 4.67
5. E13-P1 — 4.67

*The order is the actual final ranking. The composite alone ties at 4.67 for #3–#5 (E32-P1, E01-P1, E13-P1); the final score breaks the tie with screenplay intensity and the Ep≤5 bonus.*

**LLM-2 (composite):**

1. E31-P2 — 4.83
2. E32-P1 — 4.33
3. E43-P1 — 4.00
4. E13-P1 — 3.67
5. E01-P1 — 3.42

**What moves:**

- **E31-P2 stays #1** in both. That is the strongest single result: the top pick is not Qwen-specific.
- **E32-P1 moves #3 → #2**, and **E43-P1 moves #2 → #3**. They swap.
- **E13-P1 moves #5 → #4**, and **E01-P1 moves #4 → #5**. They swap.
- **E01-P1** has the largest drop among the top five (−1.25); LLM-2 still gives it a 4.75 for clarity but only 2.75 for hook and cliffhanger. Qwen gave it 5/4/5.

**Interpretation:** the top-1 is robust; the rest of the top five is not stable across model families. A submission that claims “these are the five best” is overclaiming; “these are five strong candidates, with E31-P2 the most robust” is defensible.

### 9.1 Cross-run check: the all-qwen run

A separate 50-episode run used `qwen3.8:27b` for **both** the finder and the judge. Its top five was:

**E31-P2, E01-P1, E15-P1, E02-P1, E42-P1.**

- Only **2 of 5** overlap with the archived top five (E31-P2, E01-P1).
- **E31-P2 is #1 again** — the same pick as the archived run and LLM-2. That is now three independent rankings agreeing on the top spot.
- The all-qwen run is **self-graded** (83/83), so it is not a clean judge comparison. It is evidence about finder sensitivity and coverage, not about judge quality.
- It also flips the missing episode: Ep 42 is covered (E42-P1 #5), but Ep 33 is missed (E33-P1 60.3 s after repair). See the Detailed Working Report, Appendix C.

---

## 10. What this proves — and what it doesn’t

### It does show

- The Qwen ranking is **not purely Qwen-specific**: a different model family reproduces top > mid > bottom and gives the bottom stratum a 25% would-post rate.
- Qwen is **lenient**, by about **+0.56** composite and **+0.85** on cliffhanger.
- The **top-1** (E31-P2) is stable across models.
- The **top-10 order** is only partly stable (6/10 overlap).
- **Cliffhanger** is the weakest dimension: Qwen overrates it most, and LLM-2’s own repeat agreement is low (ρ=0.53).

### It does not show

- That either model matches a human viewer. **There is still no human gold set.**
- That the absolute scores are correct. Both models could be lenient or harsh in the same direction.
- That the result generalizes to another show, another genre, or video/audio. Everything here is text-only, one show.
- That `would_post` or `safety` are ground truth. They are single-judge flags, not platform policy.
- That 24 clips are enough for a precise estimate. The sample is stratified on purpose and is small; treat it as a directional robustness check.

---

## 11. The human step that would settle it

Pick **24 clips** (the same packet is fine), blind them, and have **two people** score them on the same rubric. Then compute:

| Comparison | What it tells you |
|---|---|
| Human 1 vs Human 2 | Is the rubric clear? (Cohen’s κ / ICC) |
| Human vs Qwen | Is Qwen lenient or wrong? |
| Human vs LLM-2 | Is LLM-2 closer to a viewer? |
| Human vs both | Do the two LLMs share a bias? |

Decision table:

| Pattern | Interpretation |
|---|---|
| Human–Qwen high, Human–LLM-2 low | Qwen is right; LLM-2 is too harsh |
| Human–LLM-2 high, Human–Qwen low | Qwen is lenient; LLM-2 is the better proxy |
| Both high | Both are usable proxies; keep the cheaper one |
| Both low | Neither judge is valid; fix the rubric before scaling |
| Human–Human low | The rubric is ambiguous; rewrite the anchors before judging models |

For the top 10, use **pairwise comparisons** (“which would you post first?”) in both orders, then fit Bradley–Terry. That removes the 1–5 leniency problem and gives a direct ranking.

---

## 12. Reproducibility

### Files

| Path | What it is |
|---|---|
| `outputs/eval-llm2/packet.json` | 24 blinded clips: `clip_id`, `duration_s`, `transcript` |
| `outputs/eval-llm2/key.json` | Private mapping: clip → promo, stratum, rank, Qwen scores |
| `outputs/eval-llm2/rubric.md` | Exact LLM-2 prompt |
| `C:\Users\kunal\AppData\Local\Temp\opencode\llm2\pass1\scores.json` | Pass 1 raw scores |
| `C:\Users\kunal\AppData\Local\Temp\opencode\llm2\pass2\scores.json` | Pass 2 raw scores |
| `outputs/eval-llm2/comparison.md` | Human-readable metrics |
| `outputs/eval-llm2/comparison.json` | Machine-readable metrics |
| `outputs/eval-llm2/per_clip.csv` | Unblinded per-clip table |
| `outputs/eval-llm2/supplement_packet.json` | 4-clip top-5 supplement |
| `outputs/eval-llm2/supplement_key.json` | Supplement mapping + Qwen scores |
| `outputs/eval-llm2/build_packet.py` | Builds the 24-clip packet (seed 42) |
| `outputs/eval-llm2/build_supplement.py` | Builds the 4-clip supplement |
| `outputs/eval-llm2/compare.py` | Computes the 24-clip metrics |
| `outputs/eval-llm2/supplement_compare.py` | Computes the supplement table |
| `outputs/eval-llm2/make_tables.py` | Regenerates the tables in this document |

### Commands

```powershell
C:\Users\kunal\anaconda3\python.exe outputs\eval-llm2\build_packet.py
# two blinded raters score pass1/pass2, then:
C:\Users\kunal\anaconda3\python.exe outputs\eval-llm2\compare.py

C:\Users\kunal\anaconda3\python.exe outputs\eval-llm2\build_supplement.py
# two blinded raters score supplement1/supplement2, then:
C:\Users\kunal\anaconda3\python.exe outputs\eval-llm2\supplement_compare.py
```

The rater step is intentionally manual/LLM-session-based; the scripts build the blind packets and compute the metrics. To re-run with human raters, replace the two `scores.json` files with human sheets in the same schema.

---

## 13. Glossary

| Term | Meaning |
|---|---|
| **Packet** | The set of clips shown to a rater, with metadata stripped |
| **Blinding** | Removing rank, score, source, promo ID, and episode number so the rater cannot infer the expected answer |
| **H/C/Cl** | Hook / cliffhanger / clarity, each 1–5 |
| **Composite** | Mean of H, C, and Cl |
| **Delta** | LLM-2 minus Qwen; negative means LLM-2 is harsher |
| **Spearman ρ** | Rank correlation; 1.0 = identical order, 0 = none |
| **MAE** | Mean absolute error in points |
| **Within 1** | Share of clips where the two scores differ by ≤1 point |
| **Top-10 overlap** | Number of clips common to both top-10 lists |
| **Would-post** | Binary: would you run this as an ad? |
| **Safety** | safe / caution / unsafe, judged from the transcript |

---

*This document is a robustness check, not a validation study. The next step is a small blind human set; without it, “good” still means “agrees with an LLM judge.”*
