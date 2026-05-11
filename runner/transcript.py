"""Transcript and trace I/O.

`transcript.jsonl` is the source of truth — one JSON object per turn.
`transcript.md` is a human-readable rendering produced from the JSONL.
`trace.jsonl` is structured events for invariant oracles.
`state.json` holds turn ownership, scenario state, persona internals, debrief.
"""
from __future__ import annotations

import json
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Iterable


@dataclass
class TranscriptTurn:
    turn: int
    role: str                 # "user" | "sut" | "tool_call"
    content: str
    ts: float = field(default_factory=time.time)
    metadata: dict[str, Any] = field(default_factory=dict)


def write_turn(path: Path, turn: TranscriptTurn) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a") as f:
        f.write(json.dumps(asdict(turn)) + "\n")


def read_turns(path: Path) -> list[TranscriptTurn]:
    if not path.exists():
        return []
    out: list[TranscriptTurn] = []
    with path.open() as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            d = json.loads(line)
            out.append(TranscriptTurn(**d))
    return out


def write_trace_event(path: Path, event: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a") as f:
        f.write(json.dumps(event) + "\n")


def read_trace(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    out: list[dict[str, Any]] = []
    with path.open() as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            out.append(json.loads(line))
    return out


def write_state(path: Path, state: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(state, indent=2, default=str))
    tmp.replace(path)


def read_state(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    return json.loads(path.read_text())


def render_markdown(turns: Iterable[TranscriptTurn], state: dict[str, Any]) -> str:
    lines: list[str] = []
    lines.append(f"# Run: {state.get('scenario_id', '?')}")
    lines.append("")
    lines.append(f"**Persona:** {state.get('persona_id', '?')}")
    lines.append(f"**Intention:** {state.get('intention', '?')}")
    lines.append("")
    lines.append("## Transcript")
    lines.append("")
    for t in turns:
        if t.role == "user":
            lines.append(f"### Turn {t.turn} — persona")
        elif t.role == "sut":
            lines.append(f"### Turn {t.turn} — SUT")
        elif t.role == "tool_call":
            lines.append(f"### Turn {t.turn} — tool call: {t.metadata.get('name', '?')}")
        else:
            lines.append(f"### Turn {t.turn} — {t.role}")
        lines.append("")
        lines.append(t.content if t.content else "_(empty)_")
        lines.append("")
    if "debrief" in state:
        d = state["debrief"]
        lines.append("## Debrief (in persona's voice)")
        lines.append("")
        lines.append(f"- **Accomplished goal:** {d.get('accomplished_goal')} — {d.get('accomplished_goal_reason','')}")
        lines.append(f"- **Stuck points:** {d.get('stuck_points','')}")
        lines.append(f"- **Pain points:** {d.get('pain_points','')}")
        lines.append(f"- **Felt trustworthy:** {d.get('felt_trustworthy')} — {d.get('felt_trustworthy_reason','')}")
        lines.append(f"- **Would return:** {d.get('would_return')}")
        lines.append(f"- **One change:** {d.get('one_change','')}")
        lines.append("")
    return "\n".join(lines)
