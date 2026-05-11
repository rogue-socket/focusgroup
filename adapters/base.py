"""Base adapter protocol.

User-side contract:

    from adapters.base import Session, SUTResponse, ToolCall

    def respond(user_text: str, session: Session) -> SUTResponse:
        ...

See reference/adapter-protocol.md for the full protocol.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class ToolCall:
    name: str
    arguments: dict[str, Any] = field(default_factory=dict)
    result: Any | None = None
    error: str | None = None

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "arguments": self.arguments,
            "result": self.result,
            "error": self.error,
        }


@dataclass
class SUTResponse:
    text: str
    tool_calls: list[ToolCall] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class Turn:
    role: str               # "user" | "sut" | "tool_call"
    content: str
    turn: int
    ts: float
    metadata: dict[str, Any] = field(default_factory=dict)


class Session:
    """Mutable session state passed to the adapter on every turn.

    `state` is a free-form dict the adapter writes to for cross-turn memory.
    `history` is read-only — appended by the runner after each turn.
    """

    def __init__(
        self,
        scenario_id: str,
        persona_id: str,
        initial_state: dict | None = None,
    ):
        self.scenario_id = scenario_id
        self.persona_id = persona_id
        self.state: dict[str, Any] = dict(initial_state or {})
        self.turn: int = 0
        self._history: list[Turn] = []

    @property
    def history(self) -> list[Turn]:
        return list(self._history)  # defensive copy

    def _append_turn(self, turn: Turn) -> None:
        """Runner-only — appends a turn to history."""
        self._history.append(turn)


def respond(user_text: str, session: Session) -> SUTResponse:  # pragma: no cover
    """Default placeholder. Override in your project's adapter.py."""
    raise NotImplementedError("Implement respond() in your project's adapter.py.")
