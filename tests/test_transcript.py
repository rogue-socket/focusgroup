"""Transcript JSONL round-trip and markdown rendering."""
from pathlib import Path

from runner.transcript import (
    TranscriptTurn,
    read_state,
    read_trace,
    read_turns,
    render_markdown,
    write_state,
    write_trace_event,
    write_turn,
)


def test_turn_roundtrip(tmp_path: Path):
    p = tmp_path / "transcript.jsonl"
    t1 = TranscriptTurn(turn=0, role="user", content="hello")
    t2 = TranscriptTurn(turn=0, role="sut", content="hi there", metadata={"latency_ms": 12.3})
    write_turn(p, t1)
    write_turn(p, t2)
    out = read_turns(p)
    assert len(out) == 2
    assert out[0].role == "user"
    assert out[1].metadata["latency_ms"] == 12.3


def test_trace_roundtrip(tmp_path: Path):
    p = tmp_path / "trace.jsonl"
    write_trace_event(p, {"type": "sut_turn", "turn": 0, "latency_ms": 10})
    write_trace_event(p, {"type": "tool_call", "turn": 0, "name": "x"})
    events = read_trace(p)
    assert len(events) == 2
    assert events[1]["name"] == "x"


def test_state_atomic_write(tmp_path: Path):
    p = tmp_path / "state.json"
    write_state(p, {"k": 1})
    assert read_state(p) == {"k": 1}
    # overwrite
    write_state(p, {"k": 2, "owner": "sut"})
    assert read_state(p)["k"] == 2


def test_render_markdown(tmp_path: Path):
    turns = [
        TranscriptTurn(turn=0, role="user", content="hi"),
        TranscriptTurn(turn=0, role="sut", content="hello!"),
    ]
    state = {
        "scenario_id": "sc1",
        "persona_id": "p1",
        "intention": "say hi",
        "debrief": {
            "accomplished_goal": "yes",
            "accomplished_goal_reason": "n/a",
            "stuck_points": "",
            "pain_points": "",
            "felt_trustworthy": "yes",
            "felt_trustworthy_reason": "",
            "would_return": "yes",
            "one_change": "nothing",
        },
    }
    md = render_markdown(turns, state)
    assert "# Run: sc1" in md
    assert "say hi" in md
    assert "Debrief" in md
    assert "Accomplished goal" in md
