"""Backend status: which configured models can be reached, and is the key set. Used by the Streamlit app."""
from __future__ import annotations

import os
import urllib.error
import urllib.request


def _base_url(pcfg: dict) -> str | None:
    if "base_url_env" in pcfg:
        url = os.getenv(pcfg["base_url_env"], "").rstrip("/")
        return (url + ("" if url.endswith("/v1") else "/v1")) if url else None
    return pcfg.get("base_url")


def check_backends(cfg: dict, timeout: float = 4.0) -> list[dict]:
    """One row per (stage, model): key present? endpoint answering? Never raises."""
    rows = []
    for stage, chain in cfg["stages"].items():
        for i, entry in enumerate(chain):
            pcfg = cfg["providers"].get(entry["provider"], {})
            key_env = pcfg.get("api_key_env", "")
            key_set = bool(os.getenv(key_env)) if key_env else False
            row = {"stage": stage + ("" if i == 0 else " (fallback)"), "provider": entry["provider"],
                   "model": entry["model"], "key_set": key_set, "reachable": None, "detail": ""}
            if not key_set:
                row["detail"] = f"{key_env} is not set"
            elif pcfg.get("type") == "anthropic":
                row["detail"] = "key set (endpoint not probed)"
            else:
                url = _base_url(pcfg)
                if not url:
                    row["detail"] = f"{pcfg.get('base_url_env')} is not set"
                else:
                    try:
                        req = urllib.request.Request(url + "/models", headers={"Authorization": f"Bearer {os.getenv(key_env)}", "User-Agent": "kukuads-health"})
                        urllib.request.urlopen(req, timeout=timeout).close()
                        row["reachable"], row["detail"] = True, "answering"
                    except urllib.error.HTTPError as e:   # the server answered, e.g. 401 or 404
                        row["reachable"], row["detail"] = True, f"answering (HTTP {e.code})"
                    except Exception as e:
                        row["reachable"], row["detail"] = False, f"not reachable ({type(e).__name__})"
            rows.append(row)
    return rows
