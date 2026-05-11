"""Generic HTTP POST /chat adapter.

For SUTs that aren't OpenAI-compatible. Configure the request body shape and
the response extraction path.

Example: if your SUT accepts `{"input": "...", "session_id": "..."}` and
returns `{"output": "...", "metadata": {...}}`, set:

    CONFIG["request_template"] = {"input": "$USER_TEXT", "session_id": "$SCENARIO_ID"}
    CONFIG["response_text_path"] = "output"
"""
from __future__ import annotations

import json
import os
import time
import urllib.error
import urllib.request

from adapters.base import Session, SUTResponse


CONFIG: dict = {
    "url": os.environ.get("FOCUSGROUP_SUT_URL", "http://localhost:8080/chat"),
    "headers": {"Content-Type": "application/json"},
    # body template: $USER_TEXT, $SCENARIO_ID, $TURN are substituted
    "request_template": {"message": "$USER_TEXT"},
    "response_text_path": "response",   # dotted path into JSON response
    "timeout_s": 30,
    # optionally include conversation history in request:
    "include_history_as": None,         # e.g. "history" — sets payload[history] = [{"role","content"}]
}


def _substitute(template, user_text: str, session: Session):
    if isinstance(template, dict):
        return {k: _substitute(v, user_text, session) for k, v in template.items()}
    if isinstance(template, list):
        return [_substitute(v, user_text, session) for v in template]
    if isinstance(template, str):
        return (
            template.replace("$USER_TEXT", user_text)
            .replace("$SCENARIO_ID", session.scenario_id)
            .replace("$TURN", str(session.turn))
        )
    return template


def _dotted_get(obj, path: str):
    cur = obj
    for part in path.split("."):
        if isinstance(cur, list):
            cur = cur[int(part)]
        else:
            cur = cur[part]
    return cur


def respond(user_text: str, session: Session) -> SUTResponse:
    payload = _substitute(CONFIG["request_template"], user_text, session)
    if CONFIG.get("include_history_as"):
        payload[CONFIG["include_history_as"]] = [
            {"role": t.role, "content": t.content}
            for t in session.history
            if t.role in ("user", "sut")
        ]
    req = urllib.request.Request(
        CONFIG["url"],
        data=json.dumps(payload).encode("utf-8"),
        headers=CONFIG["headers"],
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
    text = _dotted_get(body, CONFIG["response_text_path"])
    return SUTResponse(text=str(text), metadata={"latency_ms": latency_ms})
