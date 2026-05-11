"""Persona LLM driver.

Two modes:
  - "anthropic": uses the anthropic SDK with a configurable model
  - "stub": deterministic, no API key needed — emits canned utterances from
    persona.speech_examples, then declares done. Used by tests and the
    bundled example project.

Mode is chosen via env var FOCUSGROUP_PERSONA_MODE (default "anthropic")
or by passing mode= to PersonaLLM.
"""
from __future__ import annotations

import json
import os
from dataclasses import dataclass
from typing import Optional

from runner.schemas import Persona


DEBRIEF_INSTRUCTIONS = """\
The session has ended. Step out of the conversation but STAY IN CHARACTER as your persona.
Reflect on the experience you just had. Answer the questions below honestly,
the way you would in a post-session debrief. Be specific about moments that stood
out — good or bad.

Respond in JSON with these exact keys, no other text:
{
  "accomplished_goal": "yes" | "partial" | "no" | "gave_up",
  "accomplished_goal_reason": "...",
  "stuck_points": "...",
  "pain_points": "...",
  "felt_trustworthy": "yes" | "mostly" | "unsure" | "no",
  "felt_trustworthy_reason": "...",
  "would_return": "yes" | "maybe" | "no",
  "one_change": "..."
}
"""


@dataclass
class PersonaTurn:
    text: str
    done: bool                 # whether persona signaled <<DONE>>


class PersonaLLM:
    def __init__(
        self,
        persona: Persona,
        intention: str,
        mode: Optional[str] = None,
        model: Optional[str] = None,
    ):
        self.persona = persona
        self.intention = intention
        self.mode = mode or os.environ.get("FOCUSGROUP_PERSONA_MODE", "anthropic")
        self.model = model or os.environ.get(
            "FOCUSGROUP_PERSONA_MODEL", "claude-sonnet-4-6"
        )
        self._history: list[dict] = []
        self._stub_index = 0
        if self.mode == "anthropic":
            self._client = self._init_anthropic()
        else:
            self._client = None

    def _init_anthropic(self):
        try:
            import anthropic
        except ImportError as e:
            raise RuntimeError(
                "Install the anthropic SDK or set FOCUSGROUP_PERSONA_MODE=stub."
            ) from e
        return anthropic.Anthropic()

    @property
    def system_prompt(self) -> str:
        return (
            f"{self.persona.system_prompt}\n\n"
            f"Your current intention for this session: {self.intention}\n"
        )

    def opening_turn(self) -> PersonaTurn:
        return self.next_turn(sut_text=None, opening=True)

    def next_turn(self, sut_text: Optional[str], opening: bool = False) -> PersonaTurn:
        if self.mode == "stub":
            return self._stub_turn(sut_text, opening)
        return self._anthropic_turn(sut_text, opening)

    def _stub_turn(self, sut_text: Optional[str], opening: bool) -> PersonaTurn:
        examples = self.persona.speech_examples or [
            f"[stub] I am {self.persona.id}, trying to {self.intention[:60]}",
        ]
        if self._stub_index >= len(examples):
            return PersonaTurn(text="thanks, that's all I needed. <<DONE>>", done=True)
        text = examples[self._stub_index]
        self._stub_index += 1
        done = "<<DONE>>" in text
        return PersonaTurn(text=text, done=done)

    def _anthropic_turn(self, sut_text: Optional[str], opening: bool) -> PersonaTurn:
        if sut_text is not None:
            self._history.append({"role": "user", "content": sut_text})
        if opening and not self._history:
            opener = (
                "Begin the conversation now. Stay in character. "
                "Start with whatever your persona would say in the first turn."
            )
            self._history.append({"role": "user", "content": opener})
        msg = self._client.messages.create(
            model=self.model,
            max_tokens=512,
            system=self.system_prompt,
            messages=self._history,
        )
        text = "".join(b.text for b in msg.content if hasattr(b, "text"))
        self._history.append({"role": "assistant", "content": text})
        done = "<<DONE>>" in text
        clean = text.replace("<<DONE>>", "").strip()
        return PersonaTurn(text=clean, done=done)

    def debrief(self) -> dict:
        """Prompt the persona for a structured debrief. Returns dict or raises."""
        if self.mode == "stub":
            return {
                "accomplished_goal": "partial",
                "accomplished_goal_reason": "stubbed run",
                "stuck_points": "n/a (stub)",
                "pain_points": "n/a (stub)",
                "felt_trustworthy": "unsure",
                "felt_trustworthy_reason": "stubbed run",
                "would_return": "maybe",
                "one_change": "n/a (stub)",
            }
        self._history.append({"role": "user", "content": DEBRIEF_INSTRUCTIONS})
        msg = self._client.messages.create(
            model=self.model,
            max_tokens=512,
            system=self.system_prompt,
            messages=self._history,
        )
        text = "".join(b.text for b in msg.content if hasattr(b, "text"))
        # find JSON object in text
        start = text.find("{")
        end = text.rfind("}")
        if start == -1 or end == -1:
            return {
                "accomplished_goal": "no",
                "accomplished_goal_reason": f"debrief parse failed: {text[:200]}",
                "stuck_points": "",
                "pain_points": "",
                "felt_trustworthy": "unsure",
                "felt_trustworthy_reason": "",
                "would_return": "no",
                "one_change": "",
            }
        return json.loads(text[start : end + 1])
