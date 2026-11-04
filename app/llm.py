"""Thin LLM client: OpenAI-compatible or Anthropic via env keys."""

from __future__ import annotations

import httpx

from app.config import Settings


class LLMError(RuntimeError):
    pass


async def complete(settings: Settings, system: str, user: str) -> str:
    provider = settings.provider()
    if provider == "openai":
        return await _openai_compatible(settings, system, user)
    if provider == "anthropic":
        return await _anthropic(settings, system, user)
    raise LLMError(
        "No API key configured. Set OPENAI_API_KEY or ANTHROPIC_API_KEY in .env "
        "(see .env.example)."
    )


async def _openai_compatible(settings: Settings, system: str, user: str) -> str:
    url = settings.openai_base_url.rstrip("/") + "/chat/completions"
    headers = {
        "Authorization": f"Bearer {settings.openai_api_key}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": settings.openai_model,
        "temperature": 0.3,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
    }
    async with httpx.AsyncClient(timeout=120.0) as client:
        resp = await client.post(url, headers=headers, json=payload)
        if resp.status_code >= 400:
            raise LLMError(f"OpenAI-compatible API error {resp.status_code}: {resp.text[:500]}")
        data = resp.json()
    try:
        return data["choices"][0]["message"]["content"].strip()
    except (KeyError, IndexError, TypeError) as exc:
        raise LLMError(f"Unexpected OpenAI response shape: {data!r}") from exc


async def _anthropic(settings: Settings, system: str, user: str) -> str:
    url = "https://api.anthropic.com/v1/messages"
    headers = {
        "x-api-key": settings.anthropic_api_key or "",
        "anthropic-version": "2023-06-01",
        "Content-Type": "application/json",
    }
    payload = {
        "model": settings.anthropic_model,
        "max_tokens": 4096,
        "temperature": 0.3,
        "system": system,
        "messages": [{"role": "user", "content": user}],
    }
    async with httpx.AsyncClient(timeout=120.0) as client:
        resp = await client.post(url, headers=headers, json=payload)
        if resp.status_code >= 400:
            raise LLMError(f"Anthropic API error {resp.status_code}: {resp.text[:500]}")
        data = resp.json()
    try:
        parts = data["content"]
        text = "".join(block.get("text", "") for block in parts if block.get("type") == "text")
        return text.strip()
    except (KeyError, TypeError) as exc:
        raise LLMError(f"Unexpected Anthropic response shape: {data!r}") from exc
