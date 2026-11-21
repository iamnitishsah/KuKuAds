"""FastAPI wrapper around the same pipeline the CLI runs.

  uvicorn promofinder.api.main:app --reload        then open http://127.0.0.1:8000

Endpoints
  GET  /api/health
  GET  /api/config                     pinned models per stage + available providers (never keys)
  POST /api/jobs                       upload screenplays (.txt) or give a server folder; runs in background
  GET  /api/jobs/{run}                 status + progress log
  GET  /api/runs                       finished/ongoing run folders under outputs/
  GET  /api/runs/{run}/promos          ranked promos (JSON)
  GET  /api/runs/{run}/report          report.md (text)
  GET  /api/runs/{run}/files/{name}    download any output file (csv, json, md)
"""
from __future__ import annotations

import json
import re
import threading
import time
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse, PlainTextResponse

from promofinder.llm import apply_overrides, load_config
from promofinder.pipeline.runner import run_pipeline

ROOT = Path(__file__).resolve().parents[3]
OUTPUTS = ROOT / "outputs"
STATIC = Path(__file__).resolve().parent / "static"
load_dotenv(ROOT / ".env")

app = FastAPI(title="Promo Finder", version="1.0")
JOBS: dict[str, dict] = {}
_lock = threading.Lock()
SAFE = re.compile(r"^[A-Za-z0-9._-]+$")


def _run_dir(run: str) -> Path:
    if not SAFE.match(run):
        raise HTTPException(400, "bad run name")
    d = OUTPUTS / run
    if not d.is_dir():
        raise HTTPException(404, f"run '{run}' not found")
    return d


@app.get("/")
def index():
    return FileResponse(STATIC / "index.html")


@app.get("/api/health")
def health():
    return {"ok": True}


@app.get("/api/config")
def config():
    cfg = load_config(ROOT / "configs" / "config.yaml")
    return {"stages": cfg["stages"], "providers": {k: v.get("type") for k, v in cfg["providers"].items()},
            "promo": cfg.get("promo", {})}


def _worker(run: str, scripts_dir: Path, cfg: dict, episodes: str | None, do_judge: bool) -> None:
    job = JOBS[run]

    def progress(stage: str, i: int, n: int, msg: str) -> None:
        with _lock:
            job["stage"], job["done"], job["total"] = stage, i, n
            job["log"].append(f"[{stage} {i}/{n}] {msg}")
            job["log"] = job["log"][-300:]

    try:
        res = run_pipeline(scripts_dir, OUTPUTS / run, cfg, episodes=episodes, do_judge=do_judge,
                           progress=progress, cache_dir=ROOT / ".cache" / "llm")
        job.update(status="done", errors=res["meta"]["errors"])
    except Exception as e:  # surface any failure to the UI instead of dying silently
        job.update(status="failed", error=f"{type(e).__name__}: {e}")
    job["finished_at"] = time.strftime("%H:%M:%S")


@app.post("/api/jobs")
async def create_job(files: list[UploadFile] | None = File(None), scripts_dir: str | None = Form(None),
                     episodes: str | None = Form(None), provider: str | None = Form(None),
                     model: str | None = Form(None), judge_provider: str | None = Form(None),
                     judge_model: str | None = Form(None), judge: bool = Form(True)):
    run = f"api-{time.strftime('%Y%m%d-%H%M%S')}"
    out = OUTPUTS / run
    if files and any(f.filename for f in files):
        src = out / "input"
        src.mkdir(parents=True, exist_ok=True)
        for f in files:
            name = Path(f.filename or "").name
            if name.lower().endswith(".txt"):
                (src / name).write_bytes(await f.read())
        if not any(src.glob("*.txt")):
            raise HTTPException(400, "upload at least one .txt screenplay")
    elif scripts_dir:
        src = Path(scripts_dir)
        if not src.is_dir():
            raise HTTPException(400, f"folder not found: {scripts_dir}")
    else:
        raise HTTPException(400, "send screenplay files or a scripts_dir")

    if bool(provider) != bool(model):
        raise HTTPException(400, "provider and model go together")
    cfg = apply_overrides(load_config(ROOT / "configs" / "config.yaml"), provider or None, model or None,
                          judge_provider or None, judge_model or None)
    JOBS[run] = {"run": run, "status": "running", "stage": "starting", "done": 0, "total": 0, "log": [],
                 "started_at": time.strftime("%H:%M:%S")}
    threading.Thread(target=_worker, args=(run, src, cfg, episodes or None, judge), daemon=True).start()
    return {"run": run, "status": "running"}


@app.get("/api/jobs/{run}")
def job_status(run: str):
    if run in JOBS:
        return JOBS[run]
    d = _run_dir(run)
    return {"run": run, "status": "done" if (d / "promos_ranked.json").exists() else "unknown", "log": []}


@app.get("/api/runs")
def runs():
    if not OUTPUTS.exists():
        return []
    items = []
    for d in sorted(OUTPUTS.iterdir(), key=lambda p: p.stat().st_mtime, reverse=True):
        if d.is_dir() and (d / "promos_ranked.json").exists():
            meta = json.loads((d / "run_meta.json").read_text(encoding="utf-8")) if (d / "run_meta.json").exists() else {}
            items.append({"run": d.name, "episodes": len(meta.get("episodes", [])),
                          "finished_at": meta.get("finished_at"),
                          "finder": (meta.get("finder_chain") or [{}])[0].get("model"),
                          "judge": (meta.get("judge_chain") or [{}])[0].get("model")})
    return items


@app.get("/api/runs/{run}/promos")
def promos(run: str, top_only: bool = False):
    rows = json.loads((_run_dir(run) / "promos_ranked.json").read_text(encoding="utf-8"))
    return [r for r in rows if r.get("in_top_list")] if top_only else rows


@app.get("/api/runs/{run}/report", response_class=PlainTextResponse)
def report(run: str):
    f = _run_dir(run) / "report.md"
    if not f.exists():
        raise HTTPException(404, "report not ready")
    return f.read_text(encoding="utf-8")


@app.get("/api/runs/{run}/files/{name}")
def download(run: str, name: str):
    if not SAFE.match(name):
        raise HTTPException(400, "bad file name")
    f = _run_dir(run) / name
    if not f.is_file():
        raise HTTPException(404, "file not found")
    return FileResponse(f, filename=name)
