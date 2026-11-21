"""LLMClient: the only thing the pipeline talks to.

  * Pinned model per stage, with an explicit fallback list (used only when a call fails).
  * Returns parsed JSON; tolerates code fences / chatter around the JSON.
  * Disk cache keyed on (model, prompts, settings) so re-runs are free and demos are fast.
  * Logs every call (model that actually answered, tokens, latency, fallback) to a JSONL file.
"""
from __future__ import annotations

import hashlib
import json
import re
import time
from pathlib import Path

from .providers import LLMError, LLMResponse, build_provider


def extract_json(text: str) -> dict:
    """Pull the first JSON object out of a model reply."""
    text = text.strip()
    text = re.sub(r"^```(?:json)?\s*|\s*```$", "", text)
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    start = text.find("{")
    while start != -1:
        try:
            obj, _ = json.JSONDecoder().raw_decode(text[start:])
            if isinstance(obj, dict):
                return obj
        except json.JSONDecodeError:
            pass
        start = text.find("{", start + 1)
    raise ValueError(f"No JSON object in model reply: {text[:200]!r}")


def rate_limit_wait(err: Exception) -> float | None:
    """Seconds to wait if `err` is a rate limit (HTTP 429), else None.

    Reads, in order: the router's retryAtMs, a 'reset ~Ns' hint, a Retry-After header; default 30 s.
    """
    status = getattr(err, "status_code", None) or getattr(getattr(err, "response", None), "status_code", None)
    text = str(err)
    if status != 429 and "rate" not in text.lower():
        return None
    m = re.search(r"retryAtMs['\"]?\s*:\s*(\d{12,})", text)
    if m:
        return max(1.0, int(m.group(1)) / 1000 - time.time())
    m = re.search(r"reset\s*~\s*(\d+(?:\.\d+)?)\s*s", text)
    if m:
        return max(1.0, float(m.group(1)))
    headers = getattr(getattr(err, "response", None), "headers", None) or {}
    try:
        return max(1.0, float(headers.get("retry-after")))
    except (TypeError, ValueError):
        return 30.0


class LLMClient:
    def __init__(self, stage: str, chain: list[dict], providers_cfg: dict, llm_cfg: dict,
                 cache_dir: str | Path = ".cache/llm", log_path: str | Path | None = None):
        if not chain:
            raise LLMError(f"No models configured for stage '{stage}'")
        self.stage, self.chain, self.providers_cfg, self.llm_cfg = stage, chain, providers_cfg, llm_cfg
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.log_path = Path(log_path) if log_path else None
        self._built: dict[int, object] = {}
        self._sleep = time.sleep   # swappable in tests

    @property
    def primary(self) -> str:
        return f"{self.chain[0]['provider']}/{self.chain[0]['model']}"

    def _provider(self, i: int):
        if i not in self._built:
            entry = self.chain[i]
            pcfg = self.providers_cfg.get(entry["provider"])
            if pcfg is None:
                raise LLMError(f"Provider '{entry['provider']}' is not defined in config.yaml")
            self._built[i] = build_provider(entry["provider"], entry["model"], pcfg, self.llm_cfg)
        return self._built[i]

    def _cache_key(self, entry: dict, system: str, user: str, variant: int = 0) -> Path:
        key = [entry["provider"], entry["model"], system, user,
               self.llm_cfg.get("temperature"), self.llm_cfg.get("max_tokens")]
        # Only add these when set, so existing cache entries stay valid.
        extra = (self.providers_cfg.get(entry["provider"]) or {}).get("extra_body")
        if extra:
            key.append({"extra_body": extra})
        if variant:
            key.append({"variant": variant})
        raw = json.dumps(key)
        return self.cache_dir / (hashlib.sha256(raw.encode()).hexdigest()[:32] + ".json")

    def _log(self, record: dict) -> None:
        if self.log_path:
            self.log_path.parent.mkdir(parents=True, exist_ok=True)
            with self.log_path.open("a", encoding="utf-8") as f:
                f.write(json.dumps(record, ensure_ascii=False) + "\n")

    def complete_json(self, system: str, user: str, tag: str = "", variant: int = 0) -> tuple[dict, dict]:
        """Returns (parsed_json, meta). Tries the pinned model, then the fallbacks in order.

        `variant` > 0 asks for an independent repeat of the same prompt (cached separately),
        used to judge a clip several times and average.
        """
        errors = []
        for i, entry in enumerate(self.chain):
            label = f"{entry['provider']}/{entry['model']}"
            cache_file = self._cache_key(entry, system, user, variant)
            if cache_file.exists():
                cached = json.loads(cache_file.read_text(encoding="utf-8"))
                meta = {**cached["meta"], "cached": True}
                self._log({"stage": self.stage, "tag": tag, **meta})
                return cached["data"], meta
            bad_json, rl_waits, attempt = 0, 0, 0
            while True:
                attempt += 1
                try:
                    resp: LLMResponse = self._provider(i).complete(
                        system, user,
                        temperature=self.llm_cfg.get("temperature", 0.2),
                        max_tokens=self.llm_cfg.get("max_tokens", 4000))
                    if resp.finish_reason == "length" and not resp.text:
                        raise ValueError("reply truncated by max_tokens before any output")
                    data = extract_json(resp.text)
                    meta = {"model": label, "served_by": resp.model, "fallback": i > 0,
                            "input_tokens": resp.input_tokens, "output_tokens": resp.output_tokens,
                            "latency_s": resp.latency_s, "attempt": attempt, "cached": False,
                            "ts": time.strftime("%Y-%m-%dT%H:%M:%S")}
                    cache_file.write_text(json.dumps({"meta": meta, "data": data}, ensure_ascii=False),
                                          encoding="utf-8")
                    self._log({"stage": self.stage, "tag": tag, **meta})
                    return data, meta
                except ValueError as e:          # bad JSON: retry same model once
                    errors.append(f"{label} attempt {attempt}: {e}")
                    bad_json += 1
                    if bad_json >= 2:
                        break
                    continue
                except Exception as e:
                    # Rate limited: wait for the reset and keep the PINNED model, rather than
                    # silently switching models. Fall back only if the wait would be too long.
                    wait = rate_limit_wait(e)
                    max_wait = self.llm_cfg.get("rate_limit_max_wait_s", 180)
                    if wait is not None and wait <= max_wait and rl_waits < self.llm_cfg.get("rate_limit_retries", 4):
                        rl_waits += 1
                        self._log({"stage": self.stage, "tag": tag, "model": label,
                                   "rate_limited": True, "wait_s": round(wait, 1)})
                        self._sleep(wait + 1)
                        continue
                    errors.append(f"{label}: {type(e).__name__}: {str(e)[:160]}")
                    break
            self._log({"stage": self.stage, "tag": tag, "model": label, "error": errors[-1]})
        raise LLMError(f"All models failed for stage '{self.stage}' ({tag}): " + " | ".join(errors))


def load_config(path: str | Path = "configs/config.yaml") -> dict:
    import yaml
    return yaml.safe_load(Path(path).read_text(encoding="utf-8"))


def apply_overrides(cfg: dict, provider: str | None = None, model: str | None = None,
                    judge_provider: str | None = None, judge_model: str | None = None) -> dict:
    """CLI/API override: '--provider anthropic --model X' pins every stage to that one model."""
    cfg = json.loads(json.dumps(cfg))
    if provider and model:
        for stage in cfg["stages"]:
            cfg["stages"][stage] = [{"provider": provider, "model": model}]
    if judge_provider and judge_model:
        cfg["stages"]["judge"] = [{"provider": judge_provider, "model": judge_model}]
    return cfg


def make_clients(cfg: dict, out_dir: str | Path, cache_dir: str | Path = ".cache/llm") -> dict[str, LLMClient]:
    log = Path(out_dir) / "llm_calls.jsonl"
    return {stage: LLMClient(stage, chain, cfg["providers"], cfg.get("llm", {}), cache_dir, log)
            for stage, chain in cfg["stages"].items()}
