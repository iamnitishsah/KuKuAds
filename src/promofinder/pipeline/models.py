"""Plain data structures shared by every pipeline stage."""
from __future__ import annotations

from dataclasses import dataclass, field, asdict


@dataclass
class Beat:
    """One timed line of a screenplay: dialogue, action, camera shot or sound effect."""
    id: str                 # stable ID, e.g. "E01-B012" (the LLM refers to beats only by this)
    episode: int
    index: int              # position within the episode (0-based)
    type: str               # dialogue | action | camera | sfx
    speaker: str            # character name for dialogue, else ""
    tags: list[str]         # parenthetical tone tags, e.g. ["Cold", "Commanding"]
    text: str
    start: float            # seconds from episode start
    end: float
    scene: int
    # Cheap signals computed by code (no LLM)
    intensity: int = 0      # 0..3 emotional heat from tone tags and punctuation
    physical: bool = False  # slap, strike, kneel, fire...
    cliff_cue: bool = False # "cliffhanger peak", "cut to black", "freeze"...

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class Episode:
    number: int
    logline: str
    continuity: str
    duration: float
    beats: list[Beat]
    source_file: str = ""

    def beat(self, beat_id: str) -> Beat | None:
        for b in self.beats:
            if b.id == beat_id:
                return b
        return None

    def to_dict(self) -> dict:
        return {
            "number": self.number, "logline": self.logline, "continuity": self.continuity,
            "duration": self.duration, "source_file": self.source_file,
            "beats": [b.to_dict() for b in self.beats],
        }


@dataclass
class Segment:
    episode: int
    start: float
    end: float
    start_beat: str
    end_beat: str

    @property
    def duration(self) -> float:
        return round(self.end - self.start, 2)


@dataclass
class Promo:
    promo_id: str
    source: str                       # "llm" or "baseline"
    segments: list[Segment]
    hook: str = ""
    cliffhanger: str = ""
    why: str = ""
    patterns: list[str] = field(default_factory=list)
    context_needed: str = ""
    hook_beat: str = ""
    cliffhanger_beat: str = ""
    status: str = "candidate"         # candidate | valid | rejected
    notes: list[str] = field(default_factory=list)   # validator fixes / rejection reasons
    intensity: float = 0.0
    judge: dict = field(default_factory=dict)
    scores: dict = field(default_factory=dict)
    finder_model: str = ""

    @property
    def duration(self) -> float:
        return round(sum(s.duration for s in self.segments), 2)

    @property
    def episodes(self) -> list[int]:
        return sorted({s.episode for s in self.segments})

    def to_dict(self) -> dict:
        d = asdict(self)
        d["duration_s"] = self.duration
        d["episodes"] = self.episodes
        return d


def fmt_ts(seconds: float) -> str:
    """83.5 -> '01:23.50' (same format as the screenplays)."""
    m, s = divmod(max(seconds, 0.0), 60)
    return f"{int(m):02d}:{s:05.2f}"
