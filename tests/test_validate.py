from kukuads.pipeline.models import Beat, Episode
from kukuads.pipeline.validate import validate

CFG = {"min_s": 20, "max_s": 60, "hook_window_s": 3}


def _ep() -> Episode:
    """A synthetic 90 s episode: a calm opening, a hook at 10 s, dialogue every 5 s."""
    beats = [Beat("E01-B001", 1, 0, "camera", "", [], "Wide shot of doors.", 0, 10, 1),
             Beat("E01-B002", 1, 1, "action", "", [], "She walks in calmly.", 1, 9, 1)]
    for i in range(16):
        t = 10 + i * 5
        beats.append(Beat(f"E01-B{i + 3:03d}", 1, i + 2, "dialogue", "SISTER", ["Cruel"],
                          f"Line {i}!", t, t + 4, 1, intensity=2))
    return Episode(1, "logline", "", 90, beats)


def test_ids_become_timestamps():
    p = validate({"segments": [{"start_beat": "E01-B003", "end_beat": "E01-B008"}],
                  "hook_beat": "E01-B003", "cliffhanger_beat": "E01-B008"}, _ep(), "P1", CFG)
    assert p.status == "valid"
    assert (p.segments[0].start, p.segments[0].end) == (10, 39)


def test_late_hook_moves_start():
    p = validate({"segments": [{"start_beat": "E01-B002", "end_beat": "E01-B009"}],
                  "hook_beat": "E01-B003", "cliffhanger_beat": "E01-B009"}, _ep(), "P1", CFG)
    assert p.status == "valid"
    assert p.segments[0].start == 10
    assert any("hook" in n for n in p.notes)


def test_too_long_is_trimmed_to_fit():
    p = validate({"segments": [{"start_beat": "E01-B003", "end_beat": "E01-B018"}],
                  "hook_beat": "E01-B003", "cliffhanger_beat": "E01-B018"}, _ep(), "P1", CFG)
    assert p.status == "valid" and p.duration <= 60


def test_unknown_beat_is_rejected():
    p = validate({"segments": [{"start_beat": "E01-B999", "end_beat": "E01-B008"}]}, _ep(), "P1", CFG)
    assert p.status == "rejected"


def test_too_short_extends_back_or_rejects():
    p = validate({"segments": [{"start_beat": "E01-B010", "end_beat": "E01-B011"}],
                  "hook_beat": "E01-B010", "cliffhanger_beat": "E01-B011"}, _ep(), "P1", CFG)
    assert p.status == "valid" and p.duration >= 20


# ---- edge cases: shot snapping, cuts inside spoken lines, hook window, length repair ----
def _mk(spec) -> Episode:
    """spec: (type, start, end, strong) per beat; strong dialogue gets a tone tag and a '!'."""
    beats = []
    for i, (kind, start, end, strong) in enumerate(spec):
        text = "Strong line!" if strong else "Plain line."
        beats.append(Beat(f"E01-B{i + 1:03d}", 1, i, kind, "X" if kind == "dialogue" else "",
                          ["Cruel"] if strong else [], text, start, end, 1, intensity=2 if strong else 0))
    return Episode(1, "", "", max(b.end for b in beats), beats)


def _raw(start, end, hook=None):
    return {"segments": [{"start_beat": start, "end_beat": end}], "hook_beat": hook or start, "cliffhanger_beat": end}


def _inside_a_line(ep, t):
    return any(b.type == "dialogue" and b.start < t < b.end for b in ep.beats)


def test_end_snapped_to_a_shot_never_lands_inside_a_line():
    ep = _mk([("dialogue", 0, 4, True), ("dialogue", 5, 25, False), ("camera", 24, 26.2, False), ("dialogue", 25.5, 30, False)])
    p = validate(_raw("E01-B001", "E01-B002"), ep, "P", CFG)
    assert p.status == "valid" and not _inside_a_line(ep, p.segments[0].end)
    assert p.segments[0].end == 30


def test_start_inside_a_line_moves_to_a_line_boundary():
    ep = _mk([("dialogue", 0, 10, False), ("camera", 9.8, 14, False), ("dialogue", 10.3, 14, True),
              ("dialogue", 15, 25, False), ("dialogue", 26, 35, False)])
    p = validate(_raw("E01-B003", "E01-B005"), ep, "P", CFG)
    assert p.status == "valid" and not _inside_a_line(ep, p.segments[0].start)


def test_shot_snap_does_not_push_a_clip_over_the_cap():
    ep = _mk([("camera", 19, 21, False), ("dialogue", 20, 24, True), ("dialogue", 30, 40, False), ("dialogue", 70, 79.7, True)])
    p = validate(_raw("E01-B002", "E01-B004"), ep, "P", CFG)       # raw 59.7 s; snapping back 1 s would make 60.7
    assert p.status == "valid" and p.duration <= 60 and p.segments[0].start == 20


def test_shot_snap_does_not_move_the_hook_outside_the_window():
    ep = _mk([("camera", 9.2, 13, False), ("dialogue", 10, 12.5, False), ("dialogue", 12.8, 16, True),
              ("dialogue", 17, 27, False), ("dialogue", 28, 38, False)])
    p = validate(_raw("E01-B002", "E01-B005", hook="E01-B003"), ep, "P", CFG)
    assert p.status == "valid" and ep.beat(p.hook_beat).start - p.segments[0].start <= 3


def test_too_short_is_repaired_by_running_past_the_cliffhanger():
    ep = _mk([("dialogue", 0, 4, True), ("dialogue", 5, 15, False), ("dialogue", 16, 19, False), ("dialogue", 20, 24, False)])
    p = validate(_raw("E01-B001", "E01-B002"), ep, "P", CFG)
    assert p.status == "valid" and p.duration == 24 and p.cliffhanger_beat == "E01-B004"
    assert any("extended past the cliffhanger" in n for n in p.notes)


def test_too_short_with_nothing_to_extend_is_rejected():
    ep = _mk([("dialogue", 0, 4, True), ("dialogue", 5, 15, False)])
    assert validate(_raw("E01-B001", "E01-B002"), ep, "P", CFG).status == "rejected"


def test_too_long_with_no_strong_later_beat_falls_back_to_a_weaker_hook():
    ep = _mk([("dialogue", 0, 4, True), ("dialogue", 5, 15, False), ("dialogue", 16, 30, False),
              ("dialogue", 31, 50, False), ("dialogue", 51, 70, False)])
    p = validate(_raw("E01-B001", "E01-B005"), ep, "P", CFG)
    assert p.status == "valid" and p.duration <= 60 and any("weaker hook" in n for n in p.notes)
