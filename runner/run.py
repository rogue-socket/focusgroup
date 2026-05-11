"""focusgroup run — execute scenarios end-to-end.

Usage:
    python -m runner.run --feature greeting
    python -m runner.run --scenario greeting-novice-anxious
    python -m runner.run --sample 0.2
    python -m runner.run --scenario greeting-novice-anxious --n 5

Reads from current working directory:
    adapter.py
    personas/*.yaml
    features/<feature>/scenarios/*.yaml
    requirements.md (or .yaml)

Writes to:
    runs/<timestamp>-<scenario-id>/{transcript.jsonl,transcript.md,state.json,trace.jsonl,result.json}
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import random
import sys
import time
from pathlib import Path
from typing import Callable

from runner.loader import (
    find_requirements_doc,
    load_all_scenarios,
    load_personas_dir,
    load_requirements,
    load_scenarios_for_feature,
)
from runner.oracles import evaluate
from runner.persona_loop import run_loop
from runner.schemas import Requirement, Scenario
from runner.transcript import read_state, read_turns, render_markdown


def _load_adapter(project_dir: Path) -> Callable:
    """Load the user's adapter.py respond function."""
    adapter_path = project_dir / "adapter.py"
    if not adapter_path.exists():
        raise SystemExit(f"No adapter.py found in {project_dir}.")
    spec = importlib.util.spec_from_file_location("user_adapter", adapter_path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules["user_adapter"] = mod
    spec.loader.exec_module(mod)
    if not hasattr(mod, "respond"):
        raise SystemExit("adapter.py must define respond(user_text, session) -> SUTResponse")
    return mod.respond


def _resolve_scenarios(args: argparse.Namespace, project_dir: Path) -> list[Scenario]:
    features_dir = project_dir / "features"
    if args.scenario:
        scenarios = load_all_scenarios(features_dir)
        wanted = {s.strip() for s in args.scenario.split(",")}
        out = [s for s in scenarios if s.id in wanted]
        if len(out) != len(wanted):
            missing = wanted - {s.id for s in out}
            raise SystemExit(f"Scenarios not found: {missing}")
        return out
    if args.feature:
        return load_scenarios_for_feature(features_dir, args.feature)
    scenarios = load_all_scenarios(features_dir)
    if args.sample is not None and 0 < args.sample < 1:
        random.seed(args.seed)
        k = max(1, int(len(scenarios) * args.sample))
        scenarios = random.sample(scenarios, k)
    return scenarios


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="focusgroup-run")
    p.add_argument("--feature", help="run all scenarios for a feature")
    p.add_argument("--scenario", help="run one or more scenario IDs (comma-separated)")
    p.add_argument("--sample", type=float, help="sample fraction (0-1) of all scenarios")
    p.add_argument("--n", type=int, default=1, help="repeat each scenario N times")
    p.add_argument("--seed", type=int, default=0, help="random seed for sampling")
    p.add_argument("--project-dir", default=".", help="project root (default: cwd)")
    args = p.parse_args(argv)

    project_dir = Path(args.project_dir).resolve()
    adapter_respond = _load_adapter(project_dir)
    personas = load_personas_dir(project_dir / "personas")
    if not personas:
        raise SystemExit("No personas found under personas/.")

    req_doc = find_requirements_doc(project_dir)
    if not req_doc:
        raise SystemExit("No requirements doc found. Run `focusgroup init` first.")
    requirements = load_requirements(req_doc)

    scenarios = _resolve_scenarios(args, project_dir)
    if not scenarios:
        raise SystemExit("No scenarios resolved. Check --feature / --scenario / project layout.")

    runs_dir = project_dir / "runs"
    runs_dir.mkdir(exist_ok=True)
    summary: list[dict] = []

    for scen in scenarios:
        for rep in range(args.n):
            persona = personas.get(scen.persona)
            if not persona:
                print(f"[skip] persona {scen.persona} not found for scenario {scen.id}")
                continue
            ts = time.strftime("%Y%m%dT%H%M%S")
            suffix = f"-rep{rep}" if args.n > 1 else ""
            run_dir = runs_dir / f"{ts}-{scen.id}{suffix}"
            run_dir.mkdir(parents=True, exist_ok=True)

            print(f"\n=== {scen.id} (persona={persona.id}) → {run_dir.name}")
            loop_result = run_loop(scen, persona, adapter_respond, run_dir)

            # Render markdown
            turns = read_turns(run_dir / "transcript.jsonl")
            state = read_state(run_dir / "state.json")
            (run_dir / "transcript.md").write_text(render_markdown(turns, state))

            # Evaluate oracles
            req_objs: list[Requirement] = []
            for rid in scen.requirements:
                req = requirements.get(rid)
                if not req:
                    print(f"  [warn] requirement {rid} referenced but not defined")
                    continue
                req_objs.append(req)
            results = evaluate(run_dir, req_objs, scen)
            (run_dir / "result.json").write_text(
                json.dumps([r.model_dump() for r in results], indent=2)
            )

            passed = sum(1 for r in results if r.passed)
            print(f"  termination: {loop_result.termination_reason} | "
                  f"turns: {loop_result.turns} | "
                  f"cost~${loop_result.cost_estimate_usd:.4f} | "
                  f"oracles: {passed}/{len(results)} passed")
            for r in results:
                mark = "✓" if r.passed else "✗"
                print(f"    {mark} {r.requirement_id} [{r.oracle}] — {r.evidence}")
            summary.append({
                "run_dir": str(run_dir),
                "scenario": scen.id,
                "persona": persona.id,
                "turns": loop_result.turns,
                "termination_reason": loop_result.termination_reason,
                "cost_usd": loop_result.cost_estimate_usd,
                "oracle_results": [r.model_dump() for r in results],
            })

    print("\n=== summary ===")
    print(f"{len(summary)} runs.")
    failed = sum(1 for s in summary if any(not r["passed"] for r in s["oracle_results"]))
    print(f"{failed} runs had at least one oracle failure.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
