"""Persona ↔ SUT conversation loop.

Drives a single scenario to completion or termination, writing transcript,
trace, and state artifacts along the way.
"""
from __future__ import annotations

import time
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Optional

from adapters.base import Session, SUTResponse
from runner.persona import PersonaLLM
from runner.schemas import Persona, Scenario
from runner.transcript import (
    TranscriptTurn,
    write_state,
    write_trace_event,
    write_turn,
)


@dataclass
class LoopResult:
    completed: bool
    termination_reason: str
    turns: int
    debrief: dict
    cost_estimate_usd: float


def run_loop(
    scenario: Scenario,
    persona: Persona,
    adapter_respond: Callable[[str, Session], SUTResponse],
    run_dir: Path,
    persona_llm: Optional[PersonaLLM] = None,
) -> LoopResult:
    transcript_path = run_dir / "transcript.jsonl"
    trace_path = run_dir / "trace.jsonl"
    state_path = run_dir / "state.json"

    persona_llm = persona_llm or PersonaLLM(persona, scenario.intention)
    session = Session(
        scenario_id=scenario.id,
        persona_id=persona.id,
        initial_state=scenario.initial_state,
    )

    state_snapshot = {
        "scenario_id": scenario.id,
        "persona_id": persona.id,
        "intention": scenario.intention,
        "owner": "persona",
        "turn": 0,
        "session_state": session.state,
        "termination_reason": None,
        "started_at": time.time(),
    }
    write_state(state_path, state_snapshot)

    bounds = scenario.bounds
    stuck_counter = 0
    last_progress_state: dict | None = None
    total_cost_usd = 0.0
    termination_reason = None

    sut_text: Optional[str] = None
    turn_index = 0

    while True:
        # Persona turn
        state_snapshot["owner"] = "persona"
        write_state(state_path, state_snapshot)

        pturn = persona_llm.next_turn(sut_text=sut_text, opening=(turn_index == 0))
        if pturn.text:
            turn = TranscriptTurn(turn=turn_index, role="user", content=pturn.text)
            write_turn(transcript_path, turn)
            session._append_turn(_to_session_turn(turn))

        if pturn.done and bounds.persona_can_declare_done:
            termination_reason = "persona_declared_done"
            break

        # check max turns
        if turn_index >= bounds.max_turns:
            termination_reason = "max_turns"
            break

        # SUT turn
        state_snapshot["owner"] = "sut"
        state_snapshot["turn"] = turn_index
        write_state(state_path, state_snapshot)

        try:
            response = adapter_respond(pturn.text, session)
        except Exception as e:
            response = SUTResponse(text=f"[adapter exception: {e!r}]", metadata={"error": True})

        sut_turn = TranscriptTurn(
            turn=turn_index,
            role="sut",
            content=response.text,
            metadata=response.metadata,
        )
        write_turn(transcript_path, sut_turn)
        session._append_turn(_to_session_turn(sut_turn))

        # trace events
        for tc in response.tool_calls:
            write_trace_event(trace_path, {
                "type": "tool_call",
                "turn": turn_index,
                "ts": time.time(),
                "name": tc.name,
                "arguments": tc.arguments,
                "result": tc.result,
                "error": tc.error,
            })
        write_trace_event(trace_path, {
            "type": "sut_turn",
            "turn": turn_index,
            "ts": time.time(),
            "latency_ms": response.metadata.get("latency_ms"),
            "tokens_in": response.metadata.get("tokens_in"),
            "tokens_out": response.metadata.get("tokens_out"),
        })

        # cost accumulation (rough)
        cost = response.metadata.get("cost_usd")
        if cost is None:
            ti = response.metadata.get("tokens_in") or 0
            to = response.metadata.get("tokens_out") or 0
            cost = (ti / 1_000_000) * 3.0 + (to / 1_000_000) * 15.0  # rough Sonnet pricing
        total_cost_usd += float(cost)

        if total_cost_usd >= bounds.cost_cap_usd:
            termination_reason = "cost_cap"
            break

        # stuck detection: identical session.state for N turns
        if session.state == last_progress_state:
            stuck_counter += 1
        else:
            stuck_counter = 0
            last_progress_state = dict(session.state)
        if stuck_counter >= bounds.stuck_detection_turns:
            termination_reason = "stuck"
            break

        sut_text = response.text
        turn_index += 1

    # Debrief
    debrief = persona_llm.debrief()

    state_snapshot.update({
        "owner": "ended",
        "turn": turn_index,
        "session_state": session.state,
        "termination_reason": termination_reason,
        "debrief": debrief,
        "ended_at": time.time(),
        "cost_estimate_usd": total_cost_usd,
        "completed": termination_reason
        in ("persona_declared_done", "max_turns"),
    })
    write_state(state_path, state_snapshot)

    return LoopResult(
        completed=termination_reason in ("persona_declared_done", "max_turns"),
        termination_reason=termination_reason or "unknown",
        turns=turn_index + 1,
        debrief=debrief,
        cost_estimate_usd=total_cost_usd,
    )


def _to_session_turn(t: TranscriptTurn):
    from adapters.base import Turn
    return Turn(
        role=t.role,
        content=t.content,
        turn=t.turn,
        ts=t.ts,
        metadata=t.metadata,
    )
