"""Configurable LLM provider.

The LLM is OPTIONAL. When LLM_PROVIDER is "none" the system uses deterministic
heuristic reasoning (no fabricated AI text). When a provider + key are set, the
agents route their reasoning prompts through the real model.

This module NEVER fabricates metrics: it only produces natural-language
reasoning/explanations. All numeric predictions come from the trained ML model
(see services/ml_pipeline.py) or deterministic rules.
"""
from __future__ import annotations

import json
import logging
import os
from typing import Any

from app.config import settings

logger = logging.getLogger("resurge.llm")


class LLMService:
    def __init__(self) -> None:
        self.provider = settings.LLM_PROVIDER
        self.api_key = settings.LLM_API_KEY
        self.model = settings.LLM_MODEL
        self._client = None

    @property
    def enabled(self) -> bool:
        return self.provider != "none" and bool(self.api_key)

    def _get_client(self):
        if self._client is not None:
            return self._client
        if self.provider == "openai":
            try:
                from openai import OpenAI
            except ImportError as exc:  # pragma: no cover
                raise RuntimeError("openai package not installed") from exc
            base = settings.LLM_BASE_URL or None
            self._client = OpenAI(api_key=self.api_key, base_url=base)
        elif self.provider == "anthropic":
            try:
                import anthropic
            except ImportError as exc:  # pragma: no cover
                raise RuntimeError("anthropic package not installed") from exc
            self._client = anthropic.Anthropic(api_key=self.api_key)
        else:
            raise RuntimeError("LLM provider disabled")
        return self._client

    def complete(self, system: str, user: str, max_tokens: int = 600) -> str:
        if not self.enabled:
            raise RuntimeError("LLM disabled; use heuristic reasoning")
        client = self._get_client()
        if self.provider == "openai":
            resp = client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system},
                    {"role": "user", "content": user},
                ],
                max_tokens=max_tokens,
                temperature=0.2,
            )
            return resp.choices[0].message.content or ""
        if self.provider == "anthropic":
            resp = client.messages.create(
                model=self.model,
                system=system,
                messages=[{"role": "user", "content": user}],
                max_tokens=max_tokens,
            )
            return "".join(block.text for block in resp.content if block.type == "text")
        raise RuntimeError("unknown provider")

    def structured(self, system: str, user: str, max_tokens: int = 800) -> Any:
        text = self.complete(system, user, max_tokens)
        # Extract the first JSON object from the response.
        start = text.find("{")
        end = text.rfind("}")
        if start == -1 or end == -1:
            return {}
        try:
            return json.loads(text[start : end + 1])
        except json.JSONDecodeError:
            return {}


_llm_instance: LLMService | None = None


def get_llm() -> LLMService:
    global _llm_instance
    if _llm_instance is None:
        _llm_instance = LLMService()
    return _llm_instance
