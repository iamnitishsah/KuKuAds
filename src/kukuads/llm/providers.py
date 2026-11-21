"""Provider adapters. Every adapter exposes the same `complete()` method, so the
pipeline never knows (or cares) which API is behind it.

Two adapter types cover practically every provider:
  * openai_compatible - OpenAI, Gemini (OpenAI endpoint), Groq, local routers, Ollama, LM Studio...
  * anthropic         - Claude via the Anthropic SDK
"""
from __future__ import annotations

import os
import time
from dataclasses import dataclass


@dataclass
class LLMResponse:
    text: str
    model: str
    provider: str
    input_tokens: int = 0
    output_tokens: int = 0
    latency_s: float = 0.0
    finish_reason: str = "stop"


class LLMError(RuntimeError):
    pass


def _require_key(env_name: str) -> str:
    key = os.getenv(env_name)
    if not key:
        raise LLMError(f"{env_name} is not set (add it to .env)")
    return key


class OpenAICompatibleLLM:
    """Any provider with an OpenAI-style /chat/completions endpoint."""

    def __init__(self, name: str, model: str, base_url: str, api_key_env: str,
                 max_retries: int = 2, timeout: float = 120.0, extra_body: dict | None = None):
        from openai import OpenAI
        self.name, self.model, self.extra_body = name, model, extra_body or None
        # The SDK retries 429 (rate limit) and 5xx errors itself, with exponential backoff.
        self.client = OpenAI(api_key=_require_key(api_key_env), base_url=base_url,
                             max_retries=max_retries, timeout=timeout)

    def complete(self, system: str, user: str, temperature: float = 0.2,
                 max_tokens: int = 4000, json_mode: bool = True) -> LLMResponse:
        t0 = time.monotonic()
        kwargs = {}
        if json_mode:
            kwargs["response_format"] = {"type": "json_object"}
        if self.extra_body:
            kwargs["extra_body"] = self.extra_body
        resp = self.client.chat.completions.create(
            model=self.model,
            messages=[{"role": "system", "content": system}, {"role": "user", "content": user}],
            temperature=temperature, max_tokens=max_tokens, **kwargs,
        )
        usage = resp.usage
        choice = resp.choices[0]
        return LLMResponse(
            text=(choice.message.content or "").strip(),
            model=resp.model or self.model, provider=self.name,
            input_tokens=getattr(usage, "prompt_tokens", 0) or 0,
            output_tokens=getattr(usage, "completion_tokens", 0) or 0,
            latency_s=round(time.monotonic() - t0, 2),
            finish_reason=choice.finish_reason or "stop",
        )


class AnthropicLLM:
    """Claude via the Anthropic Messages API."""

    def __init__(self, name: str, model: str, api_key_env: str = "ANTHROPIC_API_KEY",
                 max_retries: int = 2, timeout: float = 120.0, **_ignored):
        import anthropic
        self.name, self.model = name, model
        self.client = anthropic.Anthropic(api_key=_require_key(api_key_env),
                                          max_retries=max_retries, timeout=timeout)

    def complete(self, system: str, user: str, temperature: float = 0.2,
                 max_tokens: int = 4000, json_mode: bool = True) -> LLMResponse:
        t0 = time.monotonic()
        if json_mode:
            system = system + "\n\nRespond with a single valid JSON object and nothing else."
        resp = self.client.messages.create(
            model=self.model, system=system, max_tokens=max_tokens, temperature=temperature,
            messages=[{"role": "user", "content": user}],
        )
        text = "".join(getattr(b, "text", "") for b in resp.content).strip()
        return LLMResponse(
            text=text, model=resp.model or self.model, provider=self.name,
            input_tokens=resp.usage.input_tokens, output_tokens=resp.usage.output_tokens,
            latency_s=round(time.monotonic() - t0, 2),
            finish_reason="length" if resp.stop_reason == "max_tokens" else "stop",
        )


ADAPTERS = {"openai_compatible": OpenAICompatibleLLM, "anthropic": AnthropicLLM}


def build_provider(provider_name: str, model: str, provider_cfg: dict, llm_cfg: dict):
    kind = provider_cfg.get("type", "openai_compatible")
    if kind not in ADAPTERS:
        raise LLMError(f"Unknown provider type '{kind}' for '{provider_name}'")
    kwargs = {k: v for k, v in provider_cfg.items() if k not in ("type", "base_url_env")}
    if "base_url_env" in provider_cfg:      # URL kept in .env (e.g. a tunnel URL that changes per session)
        url = os.getenv(provider_cfg["base_url_env"])
        if not url:
            raise LLMError(f"{provider_cfg['base_url_env']} is not set (add it to .env)")
        kwargs["base_url"] = url.rstrip("/") + ("" if url.rstrip("/").endswith("/v1") else "/v1")
    return ADAPTERS[kind](name=provider_name, model=model,
                          max_retries=llm_cfg.get("max_retries", 2),
                          timeout=llm_cfg.get("timeout_s", 120), **kwargs)
