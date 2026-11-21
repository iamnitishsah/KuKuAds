from promofinder.pipeline.models import Promo, Segment
from promofinder.pipeline.rank import rank

CFG = {"weights": {"hook": 0.3, "cliffhanger": 0.3, "clarity": 0.3, "intensity": 0.1},
       "entry_point_bonus": 0.05, "entry_point_episodes": 5, "max_per_episode_in_top": 1, "top_n": 10}


def _p(pid, ep, h, c, cl):
    p = Promo(pid, "llm", [Segment(ep, 0, 30, "a", "b")], status="valid")
    p.judge = {"hook": h, "cliffhanger": c, "clarity": cl}
    return p


def test_rank_orders_by_score_and_applies_diversity_cap():
    rows = rank([_p("A", 20, 4, 4, 4), _p("B", 20, 5, 5, 5), _p("C", 21, 3, 3, 3)], CFG)
    assert [r["promo_id"] for r in rows] == ["B", "C", "A"]     # A held back: same episode as B
    assert rows[0]["in_top_list"] and not rows[2]["in_top_list"]


def test_entry_point_bonus_breaks_ties_for_early_episodes():
    rows = rank([_p("late", 30, 4, 4, 4), _p("early", 2, 4, 4, 4)], CFG)
    assert rows[0]["promo_id"] == "early"
