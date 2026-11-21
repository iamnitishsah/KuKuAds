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
