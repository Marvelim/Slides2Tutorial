"""OpenAI-compatible client wrapper."""

from __future__ import annotations

import sys
import time
from typing import Protocol

from .prompts import build_summary_prompt


class NotesClient(Protocol):
    def generate_page_notes(self, prompt: str, image_data_url: str) -> str:
        """Generate notes for a single page screenshot."""

    def update_context_summary(self, old_summary: str, new_page_response: str) -> str:
        """Update the rolling context summary."""


class OpenAICompatibleNotesClient:
    """Small wrapper around an OpenAI-compatible Chat Completions endpoint."""

    def __init__(self, *, base_url: str, api_key: str, model: str) -> None:
        from openai import OpenAI

        self._client = OpenAI(base_url=base_url, api_key=api_key)
        self._model = model

    def generate_page_notes(self, prompt: str, image_data_url: str) -> str:
        response = self._create_chat_completion(
            model=self._model,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {
                            "type": "image_url",
                            "image_url": {"url": image_data_url},
                        },
                    ],
                }
            ],
        )
        return _extract_text(response)

    def update_context_summary(self, old_summary: str, new_page_response: str) -> str:
        response = self._create_chat_completion(
            model=self._model,
            messages=[
                {
                    "role": "user",
                    "content": build_summary_prompt(old_summary, new_page_response),
                }
            ],
        )
        return _extract_text(response)

    def _create_chat_completion(self, **kwargs: object) -> object:
        congestion_retries = 0
        while True:
            try:
                return self._client.chat.completions.create(**kwargs)
            except Exception as exc:
                if not _is_upstream_congestion_error(exc):
                    raise

                congestion_retries += 1
                print(
                    "Upstream is congested; retrying in 3 seconds "
                    f"(retry {congestion_retries}).",
                    file=sys.stderr,
                    flush=True,
                )
                time.sleep(3)


def _is_upstream_congestion_error(exc: Exception) -> bool:
    """Return True for temporary upstream congestion/rate-limit responses."""

    status_code = getattr(exc, "status_code", None)
    message = str(exc).lower()
    return status_code == 429 or any(
        marker in message
        for marker in (
            "上游负载已饱和",
            "请稍后再试",
            "rate limit",
            "too many requests",
            "overloaded",
            "upstream",
            "429",
        )
    )


def _extract_text(response: object) -> str:
    """Extract text from the common OpenAI response shape."""

    choices = getattr(response, "choices", None)
    if not choices:
        raise ValueError("API response did not include choices")

    message = getattr(choices[0], "message", None)
    content = getattr(message, "content", None)
    if isinstance(content, str) and content.strip():
        return content.strip()

    if isinstance(content, list):
        parts = []
        for part in content:
            if isinstance(part, dict) and part.get("type") == "text":
                parts.append(str(part.get("text", "")))
        text = "".join(parts).strip()
        if text:
            return text

    raise ValueError("API response did not include message content")
