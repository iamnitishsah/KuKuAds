from kukuads.selftest import run_selftest


def test_selftest_passes_offline():
    steps = run_selftest()
    assert len(steps) == 4 and all(s["ok"] for s in steps), steps
