"""App state: settings kept in session memory, the effective config, and run loading. No Streamlit widgets here."""
from __future__ import annotations

import json
import os
from contextlib import contextmanager
from pathlib import Path

import streamlit as st
from dotenv import load_dotenv

from ..llm import apply_overrides, load_config
from ..pipeline.models import Beat, Episode

ROOT = Path(__file__).resolve().parents[3]
DEFAULTS = {"override": False, "provider": "groq", "model": "", "judge_override": False,
            "jprovider": "groq", "jmodel": "", "api_key": "", "judge": True, "baseline": True}


def outputs_dir() -> Path:
    return Path(os.getenv("KUKUADS_OUTPUTS") or ROOT / "outputs")


def base_cfg() -> dict:
    load_dotenv(ROOT / ".env")
    return load_config(ROOT / "configs" / "config.yaml")


def settings() -> dict:
    """Per-session settings. The API key lives only here: never written to disk, forgotten on reload."""
    return st.session_state.setdefault("settings", dict(DEFAULTS))


def effective_cfg() -> dict:
    s = settings()
    return apply_overrides(base_cfg(), s["provider"] if s["override"] else None, s["model"] if s["override"] else None,
                           s["jprovider"] if s["judge_override"] else None, s["jmodel"] if s["judge_override"] else None)


def key_provider(cfg: dict) -> str:
    """The provider the session API key applies to."""
    s = settings()
    return s["provider"] if s["override"] else cfg["stages"]["finder"][0]["provider"]


@contextmanager
def session_key(cfg: dict):
    """Expose the session API key to the provider adapters for the duration of a call, then restore the environment."""
    s = settings()
    env = cfg["providers"].get(key_provider(cfg), {}).get("api_key_env")
    if not (s["api_key"] and env):
        yield
        return
    old = os.environ.get(env)
    os.environ[env] = s["api_key"]
    try:
        yield
    finally:
        if old is None:
            os.environ.pop(env, None)
        else:
            os.environ[env] = old


def model_summary(cfg: dict) -> str:
    f, j = cfg["stages"]["finder"][0], cfg["stages"]["judge"][0]
    return f"Finder `{f['provider']}/{f['model']}` · Judge `{j['provider']}/{j['model']}`"


def list_runs() -> list[Path]:
    out = outputs_dir()
    if not out.exists():
        return []
    runs = [d for d in out.iterdir() if d.is_dir() and (d / "promos_ranked.json").exists()]
    return sorted(runs, key=lambda d: d.stat().st_mtime, reverse=True)


def load_run(run: Path) -> dict:
    """Everything the Results view needs. `episodes` is None when beats.json is not there."""
    rd = lambda n: json.loads((run / n).read_text(encoding="utf-8")) if (run / n).exists() else None
    beats = rd("beats.json")
    episodes = {e["number"]: Episode(e["number"], e["logline"], e["continuity"], e["duration"],
                                     [Beat(**b) for b in e["beats"]], e.get("source_file", "")) for e in beats} if beats else None
    rep = run / "report.md"
    return {"dir": run, "rows": rd("promos_ranked.json") or [], "meta": rd("run_meta.json") or {},
            "candidates": rd("candidates.json") or [], "episodes": episodes,
            "report": rep.read_text(encoding="utf-8") if rep.exists() else "", "calls": _calls(run)}


def _calls(run: Path) -> list[dict]:
    f = run / "llm_calls.jsonl"
    return [json.loads(l) for l in f.read_text(encoding="utf-8").splitlines() if l.strip()] if f.exists() else []
