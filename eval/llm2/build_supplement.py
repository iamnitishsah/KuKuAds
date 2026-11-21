"""Build the 4-clip top-5 supplement: E31-P2, E43-P1, E01-P1, E13-P1."""
from __future__ import annotations

import json
import random
import shutil
import sys
from pathlib import Path

ROOT = Path(r"C:\Users\kunal\nitish\promo-finder")
SCRIPTS = Path(r"C:\Users\kunal\nitish\I Married a Broken Soldier. He was a Duke-scripts (2) (1)")
OUT = ROOT / "outputs" / "eval-llm2"
TEMP = Path(r"C:\Users\kunal\AppData\Local\Temp\opencode\llm2")
sys.path.insert(0, str(ROOT))

from promofinder.pipeline.judge import clip_transcript  # noqa: E402
from promofinder.pipeline.models import Promo, Segment  # noqa: E402
from promofinder.pipeline.parse import load_show  # noqa: E402

WANT = ["E31-P2", "E43-P1", "E01-P1", "E13-P1"]


def as_promo(row: dict) -> Promo:
    return Promo(
        promo_id=row["promo_id"],
        source=row.get("source", ""),
        segments=[
            Segment(
                episode=s["episode"], start=float(s["start"]), end=float(s["end"]),
                start_beat=s.get("start_beat", ""), end_beat=s.get("end_beat", ""),
            )
            for s in row["segments"]
        ],
    )


def main() -> None:
    show = load_show(SCRIPTS)
    by_num = {e.number: e for e in show}
    rows = {r["promo_id"]: r for r in json.loads(
        (ROOT / "outputs/full-run/promos_ranked.json").read_text(encoding="utf-8"))}

    chosen = [rows[i] for i in WANT]
    rng = random.Random(7)
    rng.shuffle(chosen)

    packet, key = [], []
    for i, row in enumerate(chosen, 1):
        cid = f"S{i:02d}"
        packet.append({
            "clip_id": cid,
            "duration_s": row["duration_s"],
            "transcript": clip_transcript(as_promo(row), by_num),
        })
        key.append({
            "clip_id": cid,
            "promo_id": row["promo_id"],
            "rank": row.get("rank"),
            "episodes": row.get("episodes"),
            "qwen": {d: row["judge"][d] for d in ("hook", "cliffhanger", "clarity")},
            "qwen_final": (row.get("scores") or {}).get("final"),
        })

    (OUT / "supplement_packet.json").write_text(json.dumps(packet, ensure_ascii=False, indent=1), encoding="utf-8")
    (OUT / "supplement_key.json").write_text(json.dumps(key, ensure_ascii=False, indent=1), encoding="utf-8")

    for name in ("supplement1", "supplement2"):
        d = TEMP / name
        d.mkdir(parents=True, exist_ok=True)
        shutil.copy2(OUT / "supplement_packet.json", d / "packet.json")
        shutil.copy2(OUT / "rubric.md", d / "rubric.md")
    print("supplement clips:", len(packet))
    print("dirs:", TEMP / "supplement1", TEMP / "supplement2")


if __name__ == "__main__":
    main()
