"""Stage 3 - Validate and fix promos (pure code).

Turns beat IDs into timestamps and enforces the brief's rules:
  * 20-60 s total
  * the hook beat starts within the first 3 s
  * the clip ends on (or right after) the cliffhanger beat
  * cuts never land in the middle of a spoken line, and snap to camera-shot edges
Every fix or rejection is recorded in promo.notes, so bad picks can be explained.
"""
from __future__ import annotations

from .models import Beat, Episode, Promo, Segment

SNAP_START_S = 1.0   # max seconds a start may move back to the beginning of the camera shot
SNAP_END_S = 1.5     # max seconds an end may move forward to the end of the camera shot
END_SLACK_S = 3.0    # the clip may run this long past the cliffhanger beat


def is_strong(b: Beat) -> bool:
    if b.type == "dialogue":
        return b.intensity >= 1 or "!" in b.text or "?" in b.text
    return b.physical


def clip_beats(ep: Episode, promo: Promo, include_camera: bool = False) -> list[Beat]:
    out = []
    for seg in promo.segments:
        for b in ep.beats:
            if seg.start - 0.01 <= b.start < seg.end and (include_camera or b.type != "camera" or b.physical):
                out.append(b)
    return out


def promo_intensity(beats: list[Beat]) -> float:
    spoken = [b.intensity for b in beats if b.type == "dialogue"]
    avg = sum(spoken) / len(spoken) if spoken else 0.0
    phys = sum(1 for b in beats if b.physical)
    return round(min(1.0, avg / 2 + 0.1 * phys), 3)


def _snap(ep: Episode, start: float, end: float) -> tuple[float, float]:
    for b in ep.beats:   # never cut a spoken line in half
        if b.type == "dialogue" and b.start < end < b.end:
            end = b.end
    for b in ep.beats:
        if b.type == "camera" and b.start <= start < b.end and start - b.start <= SNAP_START_S:
            start = b.start
        if b.type == "camera" and b.start < end < b.end and b.end - end <= SNAP_END_S:
            end = b.end
    return round(max(start, 0.0), 2), round(min(end, ep.duration), 2)


def _get(ep: Episode, beat_id) -> Beat | None:
    return ep.beat(str(beat_id).strip()) if beat_id else None


def _overlap(a: Promo, b: Promo) -> float:
    """Temporal IoU between two promos (same-episode segments only)."""
    inter = 0.0
    for sa in a.segments:
        for sb in b.segments:
            if sa.episode == sb.episode:
                inter += max(0.0, min(sa.end, sb.end) - max(sa.start, sb.start))
    union = a.duration + b.duration - inter
    return inter / union if union > 0 else 0.0


def validate(raw: dict, ep: Episode, promo_id: str, cfg: dict, source: str = "llm") -> Promo:
    min_s, max_s = cfg.get("min_s", 20), cfg.get("max_s", 60)
    hook_window = cfg.get("hook_window_s", 3)
    p = Promo(promo_id=promo_id, source=source, segments=[],
              hook=str(raw.get("hook", "")), cliffhanger=str(raw.get("cliffhanger", "")),
              why=str(raw.get("why", "")), patterns=list(raw.get("patterns") or []),
              context_needed=str(raw.get("context_needed", "")))

    def reject(reason: str) -> Promo:
        p.status = "rejected"
        p.notes.append(reason)
        return p

    # 1. Beat IDs -> beat ranges (must exist, be in order, not overlap)
    ranges: list[tuple[Beat, Beat]] = []
    for s in (raw.get("segments") or [])[:2]:
        a, b = _get(ep, s.get("start_beat")), _get(ep, s.get("end_beat"))
        if not a or not b:
            return reject(f"unknown beat id in segment {s}")
        if b.index < a.index:
            a, b = b, a
            p.notes.append("segment start/end were swapped")
        ranges.append((a, b))
    if not ranges:
        return reject("no segments")
    ranges.sort(key=lambda r: r[0].index)
    for (a1, b1), (a2, b2) in zip(ranges, ranges[1:]):
        if a2.index <= b1.index:
            return reject("segments overlap")

    hook = _get(ep, raw.get("hook_beat")) or next(
        (b for b in ep.beats[ranges[0][0].index:ranges[0][1].index + 1] if is_strong(b)), ranges[0][0])
    cliff = _get(ep, raw.get("cliffhanger_beat")) or ranges[-1][1]
    p.hook_beat, p.cliffhanger_beat = hook.id, cliff.id

    # 2. Hook must open the clip: move the start to the hook beat if it comes late
    a, b = ranges[0]
    if hook.start - a.start > hook_window or hook.index < a.index:
        if hook.index <= b.index:
            p.notes.append(f"start moved to hook beat ({a.id} -> {hook.id})")
            ranges[0] = (hook, b)
        else:
            return reject("hook beat is outside the first segment")

    # 3. Clip must end on the cliffhanger: trim trailing resolution / extend to the cliffhanger
    a, b = ranges[-1]
    if a.index <= cliff.index and cliff.end < b.end - END_SLACK_S:
        p.notes.append(f"end trimmed to cliffhanger beat ({b.id} -> {cliff.id})")
        ranges[-1] = (a, cliff)
    elif cliff.index > b.index:
        p.notes.append(f"end extended to cliffhanger beat ({b.id} -> {cliff.id})")
        ranges[-1] = (a, cliff)

    def build(rs) -> list[Segment]:
        segs = []
        for x, y in rs:
            st, en = _snap(ep, x.start, max(y.end, x.end))
            segs.append(Segment(ep.number, st, en, x.id, y.id))
        return segs

    p.segments = build(ranges)

    # 4. Length: too long -> start at a later strong beat; too short -> start at an earlier strong beat
    if p.duration > max_s:
        a, b = ranges[0]
        other = p.duration - p.segments[0].duration
        for nb in ep.beats[a.index + 1:b.index + 1]:
            if nb.type != "camera" and is_strong(nb) and min_s <= (b.end - nb.start) + other <= max_s:
                p.notes.append(f"too long ({p.duration:.1f}s): start moved to later hook {nb.id}")
                ranges[0] = (nb, b)
                p.hook_beat, p.hook = nb.id, nb.text[:120]
                p.segments = build(ranges)
                break
        if p.duration > max_s:
            return reject(f"too long ({p.duration:.1f}s > {max_s}s)")
    if p.duration < min_s:
        a, b = ranges[0]
        other = p.duration - p.segments[0].duration
        for nb in reversed(ep.beats[:a.index]):
            need = (b.end - nb.start) + other
            if need > max_s:
                break
            if nb.type != "camera" and is_strong(nb) and need >= min_s:
                p.notes.append(f"too short ({p.duration:.1f}s): start moved back to strong beat {nb.id}")
                ranges[0] = (nb, b)
                p.hook_beat, p.hook = nb.id, nb.text[:120]
                p.segments = build(ranges)
                break
        if p.duration < min_s:
            return reject(f"too short ({p.duration:.1f}s < {min_s}s)")

    p.intensity = promo_intensity(clip_beats(ep, p))
    p.status = "valid"
    return p


def validate_episode(raws: list[dict], ep: Episode, cfg: dict, finder_model: str = "") -> list[Promo]:
    promos: list[Promo] = []
    for i, raw in enumerate(raws, 1):
        pr = validate(raw, ep, f"E{ep.number:02d}-P{i}", cfg)
        pr.finder_model = finder_model
        if pr.status == "valid":
            for other in promos:
                if other.status == "valid" and _overlap(pr, other) > 0.6:
                    pr.status = "rejected"
                    pr.notes.append(f"duplicate of {other.promo_id} (overlap > 60%)")
                    break
        promos.append(pr)
    return promos
