from kukuads.pipeline.parse import parse_screenplay

SAMPLE = """EPISODE NUMBER: Episode 7
EPISODE LOGLINE: A test logline.
CONTINUITY NOTES: Notes.

--- SCRIPT START ---

SCENE 01
SCENE HEADING: INT. HALL – DAY
SCENE START: 00:00.00
SCENE END: 00:10.00

**CAMERA:**
Start: (00:00.00) | End: (00:02.50)
Wide shot of the hall.

**MATRIARCH (O.S.) (Cold, Furious):**
Start: (00:01.30) | End: (00:03.10)
"Get out of my house!"

SCENE 02

**ACTION:**
Start: (00:03.20) | End: (00:05.00)
She slaps him across the face.

**SOUND FX:**
Start: (00:05.00) | End: (01:02.50)
Strings swell to an ominous cliffhanger peak.
"""


def test_parses_blocks_and_header():
    ep = parse_screenplay(SAMPLE)
    assert ep.number == 7
    assert ep.logline == "A test logline."
    assert [b.type for b in ep.beats] == ["camera", "dialogue", "action", "sfx"]
    assert ep.beats[0].id == "E07-B001"
    assert ep.duration == 62.5


def test_dialogue_speaker_tags_and_signals():
    ep = parse_screenplay(SAMPLE)
    d = ep.beats[1]
    assert d.speaker == "MATRIARCH"
    assert d.tags == ["Cold", "Furious"]          # O.S. is dropped
    assert d.start == 1.3 and d.end == 3.1
    assert d.intensity == 3                        # two strong tones + "!"
    assert ep.beats[2].physical                    # slap
    assert ep.beats[2].scene == 2
    assert ep.beats[3].cliff_cue
