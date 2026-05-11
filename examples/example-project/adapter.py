"""Example SUT adapter: a stub greeting agent.

The SUT is defined inline so the example is self-contained. In a real project,
respond() would call into your actual conversational system.
"""
from __future__ import annotations

import re

from adapters.base import Session, SUTResponse


_NAME_RE = re.compile(r"\b(?:i'?m|i am|my name is|it's|its)\s+([A-Z][a-zA-Z]+)", re.IGNORECASE)


def _extract_name(text: str) -> str | None:
    m = _NAME_RE.search(text)
    if m:
        return m.group(1).strip(" .,!?")
    # fallback: a single capitalized word
    tokens = re.findall(r"\b[A-Z][a-z]{2,}\b", text)
    if len(tokens) == 1:
        return tokens[0]
    return None


def respond(user_text: str, session: Session) -> SUTResponse:
    state = session.state
    if "asked_for_name" not in state:
        state["asked_for_name"] = False
        state["user_name"] = None

    if not state["asked_for_name"]:
        state["asked_for_name"] = True
        return SUTResponse(
            text="Hi! I'm a greeting agent — a software program, not a person. "
                 "What should I call you?",
            metadata={"tokens_in": 20, "tokens_out": 25},
        )

    if state["user_name"] is None:
        name = _extract_name(user_text)
        if name:
            state["user_name"] = name
            return SUTResponse(
                text=f"Nice to meet you, {name}! Is there anything I can help you with today?",
                metadata={"tokens_in": 15, "tokens_out": 18},
            )
        return SUTResponse(
            text="Sorry, I didn't catch that. What's your name?",
            metadata={"tokens_in": 15, "tokens_out": 12},
        )

    return SUTResponse(
        text=f"All good, {state['user_name']}. Anything else?",
        metadata={"tokens_in": 12, "tokens_out": 10},
    )
