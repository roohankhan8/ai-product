from collections.abc import Sequence
from dataclasses import dataclass

import httpx

from core.config import get_settings
from core.errors import APIError


@dataclass(frozen=True)
class ChatMessage:
    role: str
    content: str


class ChatProvider:
    async def complete(self, messages: Sequence[ChatMessage]) -> str:
        raise NotImplementedError


class MockChatProvider(ChatProvider):
    async def complete(self, messages: Sequence[ChatMessage]) -> str:
        latest = next(
            (message.content for message in reversed(messages) if message.role == "user"),
            "",
        )
        return f"Mock response: {latest}"


class OpenAICompatibleProvider(ChatProvider):
    async def complete(self, messages: Sequence[ChatMessage]) -> str:
        settings = get_settings()
        if not settings.llm_api_key:
            raise APIError(503, "llm_not_configured", "LLM provider is not configured")
        payload = {
            "model": settings.llm_model,
            "messages": [{"role": item.role, "content": item.content} for item in messages],
        }
        headers = {"Authorization": f"Bearer {settings.llm_api_key}"}
        try:
            async with httpx.AsyncClient(timeout=settings.llm_timeout_seconds) as client:
                response = await client.post(settings.llm_base_url, json=payload, headers=headers)
                response.raise_for_status()
                data = response.json()
                content = data["choices"][0]["message"]["content"]
        except (httpx.HTTPError, KeyError, IndexError, TypeError, ValueError) as exc:
            raise APIError(502, "llm_provider_error", "LLM provider request failed") from exc
        if not isinstance(content, str) or not content.strip():
            raise APIError(502, "llm_invalid_response", "LLM provider returned an invalid response")
        return content.strip()


class GeminiProvider(ChatProvider):
    async def complete(self, messages: Sequence[ChatMessage]) -> str:
        settings = get_settings()
        if not settings.llm_api_key:
            raise APIError(503, "llm_not_configured", "LLM provider is not configured")
        contents = [
            {
                "role": "model" if item.role == "assistant" else "user",
                "parts": [{"text": item.content}],
            }
            for item in messages
            if item.role in {"user", "assistant"}
        ]
        url = f"{settings.llm_base_url.rstrip('/')}/{settings.llm_model}:generateContent"
        try:
            async with httpx.AsyncClient(timeout=settings.llm_timeout_seconds) as client:
                response = await client.post(
                    url,
                    params={"key": settings.llm_api_key},
                    json={"contents": contents},
                )
                response.raise_for_status()
                data = response.json()
                content = data["candidates"][0]["content"]["parts"][0]["text"]
        except (httpx.HTTPError, KeyError, IndexError, TypeError, ValueError) as exc:
            raise APIError(502, "llm_provider_error", "LLM provider request failed") from exc
        if not isinstance(content, str) or not content.strip():
            raise APIError(502, "llm_invalid_response", "LLM provider returned an invalid response")
        return content.strip()


def get_chat_provider() -> ChatProvider:
    provider = get_settings().llm_provider
    if provider == "mock":
        return MockChatProvider()
    if provider == "openai_compatible":
        return OpenAICompatibleProvider()
    if provider == "gemini":
        return GeminiProvider()
    raise APIError(500, "invalid_llm_provider", "Configured LLM provider is unsupported")
