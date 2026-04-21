from openai import OpenAI
from django.conf import settings
from typing import Iterator


def _client() -> OpenAI:
    return OpenAI(api_key=settings.LLM_API_KEY, base_url=settings.LLM_BASE_URL)


def chat_stream(messages: list[dict], system: str = "") -> Iterator[str]:
    """Yields token strings from Groq streaming chat."""
    stream = _client().chat.completions.create(
        model=settings.LLM_MODEL,
        messages=_build_messages(messages, system),
        stream=True,
        timeout=120,
    )
    for chunk in stream:
        token = chunk.choices[0].delta.content or ""
        if token:
            yield token


def chat_complete(messages: list[dict], system: str = "", json_mode: bool = False) -> str:
    """Returns full response string from Groq (non-streaming)."""
    kwargs = {
        "model": settings.LLM_MODEL,
        "messages": _build_messages(messages, system),
        "timeout": 120,
    }
    if json_mode:
        kwargs["response_format"] = {"type": "json_object"}
    resp = _client().chat.completions.create(**kwargs)
    return resp.choices[0].message.content


def _build_messages(messages: list[dict], system: str) -> list[dict]:
    result = []
    if system:
        result.append({"role": "system", "content": system})
    result.extend(messages)
    return result
