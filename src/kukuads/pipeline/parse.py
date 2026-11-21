"""Stage 1 - Parse screenplays into timed beats (pure code, no LLM).

Input format (one block per beat):

    **MATRIARCH (Cold, Commanding):**
    Start: (00:11.30) | End: (00:13.10)
    "You should turn around, Juliana."

The parser is deliberately forgiving (case, spacing, missing headers) so it can run
on a new show without changes.
"""
from __future__ import annotations

import re
from pathlib import Path

from .models import Beat, Episode

TIME = r"(\d{1,2}):(\d{1,2}(?:\.\d+)?)"
BLOCK_RE = re.compile(
    r"^\*\*(?P<label>[^*\n]+?):?\*\*:?\s*\n\s*Start:\s*\(\s*" + TIME +
    r"\s*\)\s*\|\s*End:\s*\(\s*" + TIME + r"\s*\)\s*\n(?P<body>.*?)(?=\n\s*\n|\n\*\*|\Z)",
    re.MULTILINE | re.DOTALL | re.IGNORECASE,
)
SCENE_RE = re.compile(r"^SCENE\s+(\d+)\s*$", re.MULTILINE | re.IGNORECASE)
HEADER_RE = {
    "number": re.compile(r"^EPISODE NUMBER:\s*(?:Episode\s*)?(\d+)", re.MULTILINE | re.IGNORECASE),
    "logline": re.compile(r"^EPISODE LOGLINE:\s*(.+)$", re.MULTILINE | re.IGNORECASE),
    "continuity": re.compile(r"^CONTINUITY NOTES:\s*(.+)$", re.MULTILINE | re.IGNORECASE),
}

# Tone words that signal a heated moment (from the screenplays' own parentheticals).
STRONG_TONES = {
    "furious", "fury", "enraged", "rage", "outraged", "betrayed", "devastated", "horrified",
    "gloating", "smug", "cruel", "vicious", "venomous", "mocking", "taunting", "sneering",
    "menacing", "threatening", "murderous", "desperate", "begging", "pleading", "sobbing",
    "screaming", "shouting", "crying", "shocked", "stunned", "terrified", "panicked",
    "defiant", "triumphant", "cold", "icy", "lethal", "deadly", "seething", "accusing",
    "contemptuous", "disdainful", "humiliated", "anguished", "broken", "heartbroken",
    "hysterical", "commanding", "ruthless", "sadistic", "dangerous", "piercing", "raw",
}
PHYSICAL_RE = re.compile(
    r"\b(slap\w*|strik\w*|struck|punch\w*|hit[s]?|grab\w*|seiz\w*|shov\w*|kneel\w*|knee|"
    r"collaps\w*|blood\w*|bleed\w*|stab\w*|sword|blade|dagger|knife|fire|flames?|blaze|"
    r"chain\w*|shackle\w*|explo\w*|burst\w*|kiss\w*|whip\w*|crop|chok\w*|throw\w*|throws|"
    r"hurl\w*|drag\w*|slam\w*|shatter\w*|attack\w*|tackl\w*|gun|pistol|noose|hang\w*|"
    r"iron|brand\w*|poison\w*|tears? (?:off|open)|rips?)\b",
    re.IGNORECASE,
)
CLIFF_RE = re.compile(
    r"cliffhanger|cut to black|smash cut|freeze[s]?|frozen frame|swells?|peak|sting|"
    r"ominous|hangs in the air|to be continued|abrupt(?:ly)? cut",
    re.IGNORECASE,
)


def _secs(m: str, s: str) -> float:
    return round(int(m) * 60 + float(s), 3)


def _classify(label: str) -> tuple[str, str, list[str]]:
    """'MATRIARCH (O.S.) (Firm)' -> ('dialogue', 'MATRIARCH', ['Firm'])."""
    label = label.strip().rstrip(":").strip()
    upper = label.upper()
    if upper.startswith("CAMERA"):
        return "camera", "", []
    if upper.startswith("ACTION"):
        return "action", "", []
    if upper.startswith("SOUND") or upper.startswith("SFX") or upper.startswith("MUSIC"):
        return "sfx", "", []
    groups = re.findall(r"\(([^)]*)\)", label)
    speaker = re.sub(r"\(.*", "", label).strip()
    tags: list[str] = []
    for g in groups:
        if g.strip().upper().replace(".", "") in {"OS", "VO", "CONTD", "CONT'D", "OC"}:
            continue
        tags += [t.strip() for t in g.split(",") if t.strip()]
    return "dialogue", speaker, tags


def _intensity(tags: list[str], text: str, kind: str) -> int:
    words = {w.lower() for t in tags for w in re.findall(r"[A-Za-z]+", t)}
    score = min(2, len(words & STRONG_TONES))
    if kind == "dialogue" and "!" in text:
        score += 1
    return min(score, 3)


def parse_screenplay(text: str, source_file: str = "", fallback_number: int = 0) -> Episode:
    num_m = HEADER_RE["number"].search(text)
    number = int(num_m.group(1)) if num_m else fallback_number
    logline_m = HEADER_RE["logline"].search(text)
    cont_m = HEADER_RE["continuity"].search(text)

    scene_starts = [(m.start(), int(m.group(1))) for m in SCENE_RE.finditer(text)]

    def scene_at(pos: int) -> int:
        current = 1
        for p, n in scene_starts:
            if p <= pos:
                current = n
        return current

    beats: list[Beat] = []
    for i, m in enumerate(BLOCK_RE.finditer(text)):
        kind, speaker, tags = _classify(m.group("label"))
        body = " ".join(m.group("body").split()).strip()
        start, end = _secs(m.group(2), m.group(3)), _secs(m.group(4), m.group(5))
        if end < start:
            end = start
        beats.append(Beat(
            id=f"E{number:02d}-B{i + 1:03d}", episode=number, index=i, type=kind,
            speaker=speaker, tags=tags, text=body, start=start, end=end, scene=scene_at(m.start()),
            intensity=_intensity(tags, body, kind),
            physical=bool(kind in ("action", "camera") and PHYSICAL_RE.search(body)),
            cliff_cue=bool(kind in ("sfx", "camera", "action") and CLIFF_RE.search(body)),
        ))

    duration = max((b.end for b in beats), default=0.0)
    return Episode(
        number=number,
        logline=logline_m.group(1).strip() if logline_m else "",
        continuity=cont_m.group(1).strip() if cont_m else "",
        duration=duration, beats=beats, source_file=source_file,
    )


def parse_file(path: str | Path, fallback_number: int = 0) -> Episode:
    path = Path(path)
    return parse_screenplay(path.read_text(encoding="utf-8", errors="replace"), path.name, fallback_number)


def load_show(scripts_dir: str | Path) -> list[Episode]:
    """Parse every .txt screenplay in a folder, ordered by episode number."""
    files = sorted(Path(scripts_dir).glob("*.txt"))
    if not files:
        raise FileNotFoundError(f"No .txt screenplays found in {scripts_dir}")
    episodes = [parse_file(f, fallback_number=i + 1) for i, f in enumerate(files)]
    episodes.sort(key=lambda e: e.number)
    return episodes
