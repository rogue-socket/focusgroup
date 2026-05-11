"""Oracle dispatch — one strategy per requirement type.

See reference/oracle-strategies.md for the design rationale.

The oracles take (run_dir, requirement, scenario) and return an OracleResult.
"""
from __future__ import annotations

import ast
import json
import os
import statistics
from pathlib import Path
from typing import Any, Callable

from runner.schemas import OracleResult, Requirement, Scenario
from runner.transcript import read_state, read_trace, read_turns


# ---------- state_check ----------

class _SafeEval(ast.NodeVisitor):
    """Whitelist a small expression language over a `state` dict."""

    ALLOWED_NODES = (
        ast.Expression, ast.BoolOp, ast.BinOp, ast.UnaryOp, ast.Compare,
        ast.Call, ast.Constant, ast.Name, ast.Load, ast.Attribute,
        ast.Subscript, ast.Index, ast.Tuple, ast.List, ast.Dict,
        ast.And, ast.Or, ast.Not, ast.Eq, ast.NotEq, ast.Lt, ast.LtE,
        ast.Gt, ast.GtE, ast.In, ast.NotIn, ast.Is, ast.IsNot,
        ast.Add, ast.Sub, ast.Mult, ast.Div, ast.Mod,
    )

    def __init__(self, expr: str):
        self.expr = expr
        self.tree = ast.parse(expr, mode="eval")
        self._validate(self.tree)

    def _validate(self, node):
        if not isinstance(node, self.ALLOWED_NODES):
            raise ValueError(f"disallowed node in oracle expression: {type(node).__name__}")
        if isinstance(node, ast.Name) and node.id.startswith("_"):
            raise ValueError(f"disallowed identifier in oracle expression: {node.id}")
        if isinstance(node, ast.Attribute) and node.attr.startswith("_"):
            raise ValueError(f"disallowed attribute in oracle expression: {node.attr}")
        for child in ast.iter_child_nodes(node):
            self._validate(child)

    def eval(self, state: dict) -> Any:
        return eval(  # noqa: S307 — restricted by AST whitelist above
            compile(self.tree, "<oracle>", "eval"),
            {"__builtins__": {}, "len": len, "any": any, "all": all},
            {"state": _AttrDict(state)},
        )


class _AttrDict(dict):
    """dict with attribute access for cleaner oracle expressions.

    Stored keys win over dict methods — `state.items` returns state["items"] if present.
    """

    def __getattribute__(self, key):
        if not key.startswith("_") and dict.__contains__(self, key):
            v = dict.__getitem__(self, key)
            return _AttrDict(v) if isinstance(v, dict) else v
        return dict.__getattribute__(self, key)

    def __getattr__(self, key):
        if dict.__contains__(self, key):
            v = dict.__getitem__(self, key)
            return _AttrDict(v) if isinstance(v, dict) else v
        raise AttributeError(key)


def oracle_state_check(run_dir: Path, req: Requirement, scenario: Scenario) -> OracleResult:
    cfg = scenario.oracle_overrides.get(req.id, {}) or req.oracle_config
    check = cfg.get("check")
    if not check:
        return OracleResult(
            requirement_id=req.id,
            oracle="state_check",
            passed=False,
            evidence="missing oracle_config.check expression",
        )
    state = read_state(run_dir / "state.json")
    session_state = state.get("session_state", {})
    try:
        result = _SafeEval(check).eval(session_state)
    except Exception as e:
        return OracleResult(
            requirement_id=req.id,
            oracle="state_check",
            passed=False,
            evidence=f"check evaluation error: {e!r}",
            detail={"state": session_state, "check": check},
        )
    if result:
        evidence = "check passed"
    else:
        evidence = cfg.get("on_fail_message") or f"check failed: {check}"
    return OracleResult(
        requirement_id=req.id,
        oracle="state_check",
        passed=bool(result),
        evidence=evidence,
        detail={"state": session_state, "check": check, "result": bool(result)},
    )


# ---------- trace_invariant ----------

_INVARIANT_HELPERS = {}


def _register(name):
    def deco(fn):
        _INVARIANT_HELPERS[name] = fn
        return fn
    return deco


@_register("no_event_with")
def _no_event_with(events, **filters):
    return not any(_event_matches(e, filters) for e in events)


@_register("event_count_with")
def _event_count_with(events, **filters):
    return sum(1 for e in events if _event_matches(e, filters))


def _event_matches(event: dict, filters: dict) -> bool:
    for k, v in filters.items():
        if event.get(k) != v:
            return False
    return True


def oracle_trace_invariant(run_dir: Path, req: Requirement, scenario: Scenario) -> OracleResult:
    cfg = scenario.oracle_overrides.get(req.id, {}) or req.oracle_config
    invariant = cfg.get("invariant")
    if not invariant:
        return OracleResult(
            requirement_id=req.id,
            oracle="trace_invariant",
            passed=False,
            evidence="missing oracle_config.invariant",
        )
    events = read_trace(run_dir / "trace.jsonl")
    try:
        # tiny DSL: parse `helper(arg=value, ...)`
        result = _eval_invariant(invariant, events)
    except Exception as e:
        return OracleResult(
            requirement_id=req.id,
            oracle="trace_invariant",
            passed=False,
            evidence=f"invariant evaluation error: {e!r}",
            detail={"invariant": invariant},
        )
    # invariants can return bool OR a count to be compared
    if isinstance(result, bool):
        passed = result
    else:
        passed = bool(result)
    if passed:
        evidence = "invariant holds"
    else:
        evidence = cfg.get("on_fail_message") or f"invariant violated: {invariant}"
    return OracleResult(
        requirement_id=req.id,
        oracle="trace_invariant",
        passed=passed,
        evidence=evidence,
        detail={"invariant": invariant, "result": result},
    )


def _eval_invariant(expr: str, events: list[dict]) -> Any:
    # support either bare helper call or a comparison
    tree = ast.parse(expr, mode="eval")
    return _eval_node(tree.body, events)


def _eval_node(node, events):
    if isinstance(node, ast.Compare):
        left = _eval_node(node.left, events)
        right = _eval_node(node.comparators[0], events)
        op = node.ops[0]
        if isinstance(op, ast.LtE): return left <= right
        if isinstance(op, ast.GtE): return left >= right
        if isinstance(op, ast.Lt): return left < right
        if isinstance(op, ast.Gt): return left > right
        if isinstance(op, ast.Eq): return left == right
        if isinstance(op, ast.NotEq): return left != right
        raise ValueError(f"unsupported op: {op}")
    if isinstance(node, ast.Call):
        name = node.func.id if isinstance(node.func, ast.Name) else None
        if name not in _INVARIANT_HELPERS:
            raise ValueError(f"unknown invariant helper: {name}")
        kwargs = {kw.arg: _eval_node(kw.value, events) for kw in node.keywords}
        return _INVARIANT_HELPERS[name](events, **kwargs)
    if isinstance(node, ast.Constant):
        return node.value
    if isinstance(node, ast.Name):
        # bare identifier; e.g. True/False already handled by Constant
        raise ValueError(f"bare name not allowed: {node.id}")
    raise ValueError(f"unsupported node: {type(node).__name__}")


# ---------- trace_metric ----------

def oracle_trace_metric(run_dir: Path, req: Requirement, scenario: Scenario) -> OracleResult:
    cfg = scenario.oracle_overrides.get(req.id, {}) or req.oracle_config
    metric = cfg.get("metric")
    threshold = cfg.get("threshold")
    if not metric or not threshold:
        return OracleResult(
            requirement_id=req.id,
            oracle="trace_metric",
            passed=False,
            evidence="missing oracle_config.metric or threshold",
        )
    events = read_trace(run_dir / "trace.jsonl")
    turns = read_turns(run_dir / "transcript.jsonl")
    value = _compute_metric(metric, events, turns)
    passed = _compare(value, threshold)
    return OracleResult(
        requirement_id=req.id,
        oracle="trace_metric",
        passed=passed,
        evidence=f"{metric} = {value}, expected {threshold}",
        detail={"metric": metric, "value": value, "threshold": threshold},
    )


def _compute_metric(metric: str, events: list[dict], turns: list) -> float:
    if metric == "total_turns":
        return len({t.turn for t in turns if t.role == "sut"})
    if metric == "total_cost_usd":
        # not directly tracked here — pull latency proxy from sut_turn events
        return sum(e.get("cost_usd") or 0 for e in events if e.get("type") == "sut_turn")
    if metric == "total_tokens":
        return sum(
            (e.get("tokens_in") or 0) + (e.get("tokens_out") or 0)
            for e in events if e.get("type") == "sut_turn"
        )
    if metric == "p95_latency_ms":
        latencies = [e["latency_ms"] for e in events if e.get("type") == "sut_turn" and e.get("latency_ms") is not None]
        if not latencies:
            return 0.0
        latencies.sort()
        idx = max(0, int(0.95 * len(latencies)) - 1)
        return latencies[idx]
    raise ValueError(f"unknown metric: {metric}")


def _compare(value: float, threshold: str) -> bool:
    threshold = threshold.strip()
    for op, fn in (("<=", lambda a, b: a <= b), (">=", lambda a, b: a >= b),
                   ("<", lambda a, b: a < b), (">", lambda a, b: a > b),
                   ("==", lambda a, b: a == b)):
        if threshold.startswith(op):
            return fn(value, float(threshold[len(op):].strip()))
    raise ValueError(f"unsupported threshold: {threshold!r}")


# ---------- persona_debrief ----------

def oracle_persona_debrief(run_dir: Path, req: Requirement, scenario: Scenario) -> OracleResult:
    cfg = scenario.oracle_overrides.get(req.id, {}) or req.oracle_config
    question = cfg.get("question")
    expected = cfg.get("expect")
    state = read_state(run_dir / "state.json")
    debrief = state.get("debrief") or {}
    if not question:
        return OracleResult(
            requirement_id=req.id, oracle="persona_debrief", passed=False,
            evidence="missing oracle_config.question",
        )
    answer = debrief.get(question)
    if answer is None:
        return OracleResult(
            requirement_id=req.id, oracle="persona_debrief", passed=False,
            evidence=f"debrief missing field: {question}",
        )
    passed = (str(answer).strip().lower() == str(expected).strip().lower())
    return OracleResult(
        requirement_id=req.id, oracle="persona_debrief",
        passed=passed,
        evidence=f"debrief[{question}] = {answer!r}, expected {expected!r}",
        detail={"answer": answer, "expected": expected, "debrief": debrief},
    )


# ---------- llm_judge ----------

def oracle_llm_judge(run_dir: Path, req: Requirement, scenario: Scenario) -> OracleResult:
    cfg = scenario.oracle_overrides.get(req.id, {}) or req.oracle_config
    rubric = cfg.get("rubric")
    if not rubric:
        return OracleResult(
            requirement_id=req.id, oracle="llm_judge", passed=False,
            evidence="missing oracle_config.rubric",
        )

    mode = os.environ.get("FOCUSGROUP_JUDGE_MODE", "anthropic")
    if mode == "stub":
        # deterministic — always passes; surface that this is stubbed
        return OracleResult(
            requirement_id=req.id, oracle="llm_judge", passed=True,
            evidence="[stub judge] would have evaluated rubric",
            detail={"rubric": rubric, "stub": True},
        )

    turns = read_turns(run_dir / "transcript.jsonl")
    scope = cfg.get("scope", "last_n_turns")
    n = int(cfg.get("n", 3))
    if scope == "last_n_turns":
        selected = turns[-n*2:]
    elif scope == "all":
        selected = turns
    else:
        selected = turns[-n*2:]

    transcript_text = "\n".join(f"{t.role}: {t.content}" for t in selected)
    judge_model = cfg.get("judge_model", os.environ.get("FOCUSGROUP_JUDGE_MODEL", "claude-sonnet-4-6"))

    try:
        import anthropic
        client = anthropic.Anthropic()
        prompt = (
            "You are a binary judge for a conversational AI test. "
            "Read the transcript, then apply the rubric. "
            "Reply with JSON ONLY: {\"score\": 0 or 1, \"reason\": \"...\"}."
            f"\n\nRubric:\n{rubric}\n\nTranscript:\n{transcript_text}"
        )
        msg = client.messages.create(
            model=judge_model, max_tokens=300,
            messages=[{"role": "user", "content": prompt}],
        )
        text = "".join(b.text for b in msg.content if hasattr(b, "text"))
        start = text.find("{"); end = text.rfind("}")
        verdict = json.loads(text[start:end+1])
        passed = int(verdict.get("score", 0)) == 1
        return OracleResult(
            requirement_id=req.id, oracle="llm_judge", passed=passed,
            evidence=verdict.get("reason", ""),
            detail={"verdict": verdict, "model": judge_model},
        )
    except Exception as e:
        return OracleResult(
            requirement_id=req.id, oracle="llm_judge", passed=False,
            evidence=f"judge error: {e!r}",
        )


# ---------- dispatch ----------

ORACLES: dict[str, Callable[[Path, Requirement, Scenario], OracleResult]] = {
    "state_check": oracle_state_check,
    "trace_invariant": oracle_trace_invariant,
    "trace_metric": oracle_trace_metric,
    "persona_debrief": oracle_persona_debrief,
    "llm_judge": oracle_llm_judge,
}


def evaluate(run_dir: Path, requirements: list[Requirement], scenario: Scenario) -> list[OracleResult]:
    results: list[OracleResult] = []
    for req in requirements:
        oracle_name = req.resolved_oracle()
        fn = ORACLES.get(oracle_name)
        if not fn:
            results.append(OracleResult(
                requirement_id=req.id, oracle=oracle_name, passed=False,
                evidence=f"no oracle implementation for {oracle_name}",
            ))
            continue
        results.append(fn(run_dir, req, scenario))
    return results
