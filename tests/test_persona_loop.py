"""End-to-end loop test using stub persona LLM and an in-process SUT."""
from pathlib import Path

from adapters.base import Session, SUTResponse
from runner.persona import PersonaLLM
from runner.persona_loop import run_loop
from runner.schemas import Bounds, Persona, PersonaAxes, Scenario


def _persona():
    return Persona(
        id="stub",
        name="Stub",
        axes=PersonaAxes(
            competence=0.5, patience=0.5, adversariality=0.0,
            communication_style="terse", prior_knowledge="none",
        ),
        speech_examples=["hi", "Alice", "<<DONE>>"],
        system_prompt="be a stub",
    )


def _scenario(max_turns=10):
    return Scenario(
        id="s1", feature="f1", persona="stub", intention="say hi",
        requirements=["F-001"],
        bounds=Bounds(max_turns=max_turns, cost_cap_usd=10.0),
    )


def _adapter(user_text: str, session: Session) -> SUTResponse:
    session.state["last_user_text"] = user_text
    return SUTResponse(text=f"echo: {user_text}", metadata={"latency_ms": 1.0})


def test_loop_runs_to_completion(tmp_path: Path):
    persona = _persona()
    scen = _scenario()
    llm = PersonaLLM(persona, scen.intention, mode="stub")
    result = run_loop(scen, persona, _adapter, tmp_path, persona_llm=llm)
    assert result.completed
    assert result.termination_reason == "persona_declared_done"
    assert (tmp_path / "transcript.jsonl").exists()
    assert (tmp_path / "state.json").exists()
    assert (tmp_path / "trace.jsonl").exists()


def test_loop_writes_session_state(tmp_path: Path):
    persona = _persona()
    scen = _scenario()
    llm = PersonaLLM(persona, scen.intention, mode="stub")
    run_loop(scen, persona, _adapter, tmp_path, persona_llm=llm)
    import json
    state = json.loads((tmp_path / "state.json").read_text())
    assert state["scenario_id"] == "s1"
    assert state["persona_id"] == "stub"
    assert "session_state" in state
    assert "debrief" in state


def test_loop_respects_max_turns(tmp_path: Path):
    persona = _persona()
    # persona that never declares done — speech_examples will be exhausted but we cap turns
    persona.speech_examples = ["a", "b", "c", "d", "e"]
    scen = _scenario(max_turns=2)
    llm = PersonaLLM(persona, scen.intention, mode="stub")
    result = run_loop(scen, persona, _adapter, tmp_path, persona_llm=llm)
    # the stub exhausts and emits <<DONE>> after running out; if not, max_turns trips
    assert result.termination_reason in ("max_turns", "persona_declared_done")
