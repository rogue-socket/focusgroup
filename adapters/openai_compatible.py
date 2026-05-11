"""OpenAI-compatible chat completions adapter.

Configure via environment or by editing the constants below. The SUT is expected
to be an OpenAI-style /v1/chat/completions endpoint (OpenAI, Together, Groq,
vLLM, llama.cpp server, etc.).

Usage in your project's adapter.py:

    from adapters.openai_compatible import respond  # re-export

    # optional: override config
    import adapters.openai_compatible as oc
    oc.CONFIG = oc.CONFIG | {"model": "gpt-4o-mini"}
"""
from __future__ import annotations

import json
import os
import time
import urllib.error
import urllib.request

from adapters.base import Session, SUTResponse


CONFIG: dict = {
    "base_url": os.environ.get("FOCUSGROUP_SUT_BASE_URL", "https://api.openai.com/v1"),
    "model": os.environ.get("FOCUSGROUP_SUT_MODEL", "gpt-4o-mini"),
    "api_key_env": "FOCUSGROUP_SUT_API_KEY",
    "system_prompt": "You are a helpful assistant.",
    "max_tokens": 1024,
    "temperature": 0.7,
    "timeout_s": 30,
}


def _messages_from_history(session: Session, user_text: str) -> list[dict]:
    msgs: list[dict] = [{"role": "system", "content": CONFIG["system_prompt"]}]
    for turn in session.history:
        role = "user" if turn.role == "user" else "assistant"
        if turn.role in ("user", "sut"):
            msgs.append({"role": role, "content": turn.content})
    msgs.append({"role": "user", "content": user_text})
    return msgs


def respond(user_text: str, session: Session) -> SUTResponse:
    api_key = os.environ.get(CONFIG["api_key_env"])
    if not api_key:
        raise RuntimeError(
            f"Missing API key. Set ${CONFIG['api_key_env']} or edit adapters/openai_compatible.py."
        )
    url = f"{CONFIG['base_url'].rstrip('/')}/chat/completions"
    payload = {
        "model": CONFIG["model"],
        "messages": _messages_from_history(session, user_text),
        "max_tokens": CONFIG["max_tokens"],
        "temperature": CONFIG["temperature"],
    }
    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
        },
    )
    t0 = time.monotonic()
    try:
        with urllib.request.urlopen(req, timeout=CONFIG["timeout_s"]) as resp:
            body = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        return SUTResponse(
            text=f"[adapter error: HTTP {e.code} {e.reason}]",
            metadata={"error": True, "http_status": e.code},
        )
    latency_ms = (time.monotonic() - t0) * 1000.0
    choice = body["choices"][0]["message"]["content"]
    usage = body.get("usage") or {}
    return SUTResponse(
        text=choice,
        metadata={
            "latency_ms": latency_ms,
            "tokens_in": usage.get("prompt_tokens"),
            "tokens_out": usage.get("completion_tokens"),
            "model": CONFIG["model"],
        },
    )
