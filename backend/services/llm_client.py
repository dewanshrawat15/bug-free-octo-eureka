import json
import httpx
from django.conf import settings
from typing import Iterator


def _url(path: str) -> str:
    return f"{settings.OLLAMA_BASE_URL}{path}"


def chat_stream(messages: list[dict], system: str = "") -> Iterator[str]:
    """Yields token strings from Ollama streaming chat."""
    payload = {
        "model": settings.OLLAMA_MODEL,
        "messages": _build_messages(messages, system),
        "stream": True,
    }
    with httpx.stream("POST", _url("/api/chat"), json=payload, timeout=120) as resp:
        resp.raise_for_status()
        for line in resp.iter_lines():
            if not line:
                continue
            try:
                data = json.loads(line)
                token = data.get("message", {}).get("content", "")
                if token:
                    yield token
                if data.get("done"):
                    break
            except json.JSONDecodeError:
                continue


def chat_complete(messages: list[dict], system: str = "", json_mode: bool = False) -> str:
    """Returns full response string from Ollama (non-streaming)."""
    payload = {
        "model": settings.OLLAMA_MODEL,
        "messages": _build_messages(messages, system),
        "stream": False,
    }
    if json_mode:
        payload["format"] = "json"

    resp = httpx.post(_url("/api/chat"), json=payload, timeout=120)
    resp.raise_for_status()
    return resp.json()["message"]["content"]


def _build_messages(messages: list[dict], system: str) -> list[dict]:
    result = []
    if system:
        result.append({"role": "system", "content": system})
    result.extend(messages)
    return result
