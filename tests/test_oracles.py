"""Oracle dispatch and per-strategy verdicts."""
import json
from pathlib import Path

from runner.oracles import (
    _SafeEval,
    evaluate,
    oracle_persona_debrief,
    oracle_state_check,
    oracle_trace_invariant,
    oracle_trace_metric,
)
from runner.schemas import Bounds, Requirement, Scenario


def _scenario(reqs):
    return Scenario(
        id="s1", feature="f1", persona="p1", intention="x",
        requirements=reqs, bounds=Bounds(),
    )


def _write_state(run_dir: Path, state: dict):
    run_dir.mkdir(parents=True, exist_ok=True)
    (run_dir / "state.json").write_text(json.dumps(state))


def _write_trace(run_dir: Path, events: list[dict]):
    run_dir.mkdir(parents=True, exist_ok=True)
    p = run_dir / "trace.jsonl"
    p.write_text("\n".join(json.dumps(e) for e in events) + "\n")


def _write_transcript(run_dir: Path, turns: list[dict]):
    run_dir.mkdir(parents=True, exist_ok=True)
    p = run_dir / "transcript.jsonl"
    p.write_text("\n".join(json.dumps(t) for t in turns) + "\n")


def test_safe_eval_basic():
    assert _SafeEval("state.x == 1").eval({"x": 1}) is True
    assert _SafeEval("state.x == 1").eval({"x": 2}) is False
    assert _SafeEval("len(state.items) >= 2").eval({"items": [1, 2, 3]}) is True


def test_safe_eval_rejects_imports():
    import pytest
    with pytest.raises(Exception):
        _SafeEval("__import__('os')")


def test_state_check_pass(tmp_path: Path):
    _write_state(tmp_path, {"session_state": {"greeted": True}})
    req = Requirement(
        id="F-001", type="functional", description="d",
        oracle="state_check",
        oracle_config={"check": "state.greeted == True"},
    )
    r = oracle_state_check(tmp_path, req, _scenario(["F-001"]))
    assert r.passed


def test_state_check_fail(tmp_path: Path):
    _write_state(tmp_path, {"session_state": {"greeted": False}})
    req = Requirement(
        id="F-001", type="functional", description="d",
        oracle="state_check",
        oracle_config={"check": "state.greeted == True", "on_fail_message": "nope"},
    )
    r = oracle_state_check(tmp_path, req, _scenario(["F-001"]))
    assert not r.passed
    assert r.evidence == "nope"


def test_trace_invariant_holds(tmp_path: Path):
    _write_trace(tmp_path, [{"type": "sut_turn", "turn": 0}])
    req = Requirement(
        id="S-001", type="safety", description="d",
        oracle="trace_invariant",
        oracle_config={"invariant": "no_event_with(type='leak')"},
    )
    r = oracle_trace_invariant(tmp_path, req, _scenario(["S-001"]))
    assert r.passed


def test_trace_invariant_violated(tmp_path: Path):
    _write_trace(tmp_path, [{"type": "leak", "turn": 0}])
    req = Requirement(
        id="S-001", type="safety", description="d",
        oracle="trace_invariant",
        oracle_config={"invariant": "no_event_with(type='leak')"},
    )
    r = oracle_trace_invariant(tmp_path, req, _scenario(["S-001"]))
    assert not r.passed


def test_trace_metric_turns(tmp_path: Path):
    _write_transcript(tmp_path, [
        {"turn": 0, "role": "user", "content": "hi", "ts": 0, "metadata": {}},
        {"turn": 0, "role": "sut", "content": "hello", "ts": 0, "metadata": {}},
        {"turn": 1, "role": "user", "content": "bye", "ts": 0, "metadata": {}},
        {"turn": 1, "role": "sut", "content": "bye!", "ts": 0, "metadata": {}},
    ])
    _write_trace(tmp_path, [
        {"type": "sut_turn", "turn": 0},
        {"type": "sut_turn", "turn": 1},
    ])
    req = Requirement(
        id="P-001", type="performance", description="d",
        oracle="trace_metric",
        oracle_config={"metric": "total_turns", "threshold": "<= 10"},
    )
    r = oracle_trace_metric(tmp_path, req, _scenario(["P-001"]))
    assert r.passed
    assert r.detail["value"] == 2


def test_persona_debrief(tmp_path: Path):
    _write_state(tmp_path, {
        "session_state": {},
        "debrief": {"felt_trustworthy": "yes"},
    })
    req = Requirement(
        id="I-001", type="ix", description="d",
        oracle="persona_debrief",
        oracle_config={"question": "felt_trustworthy", "expect": "yes"},
    )
    r = oracle_persona_debrief(tmp_path, req, _scenario(["I-001"]))
    assert r.passed


def test_evaluate_dispatches(tmp_path: Path):
    _write_state(tmp_path, {
        "session_state": {"greeted": True},
        "debrief": {"felt_trustworthy": "yes"},
    })
    _write_trace(tmp_path, [{"type": "sut_turn", "turn": 0}])
    _write_transcript(tmp_path, [
        {"turn": 0, "role": "sut", "content": "hi", "ts": 0, "metadata": {}},
    ])
    reqs = [
        Requirement(id="F-001", type="functional", description="d",
                    oracle="state_check",
                    oracle_config={"check": "state.greeted == True"}),
        Requirement(id="I-001", type="ix", description="d",
                    oracle="persona_debrief",
                    oracle_config={"question": "felt_trustworthy", "expect": "yes"}),
    ]
    results = evaluate(tmp_path, reqs, _scenario(["F-001", "I-001"]))
    assert len(results) == 2
    assert all(r.passed for r in results)
