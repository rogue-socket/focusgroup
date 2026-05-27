# focusgroup

**Persona-driven dynamic testing for conversational AI products. Focus groups for your agents.**

Static evals catch regressions. Unit tests catch logic bugs. focusgroup catches the failures
that only emerge when a stubborn novice, an impatient expert, and a probing adversary actually
try to use the thing.

## What it does

You point focusgroup at a conversational system under test (chatbot, agent, LLM-backed module
wrapped in a conversational shell). It:

1. Builds a project-level pool of axis-defined personas (competence, patience, adversariality,
   communication style, prior knowledge — not demographics).
2. Generates scenarios per feature: persona × intention × initial state × requirements × bounds.
3. Runs each scenario as a real conversation between a persona LLM and your SUT.
4. Evaluates each run with the oracle matched to the requirement type:
   - Functional → state check
   - Safety → invariant on trace
   - Performance → metric on trace
   - IX → structured persona debrief, in character
   - Correctness → LLM judge (last resort)
5. Aggregates persona debriefs across runs into focus-group findings — clustered themes,
   failures segmented by persona axis, regression diff vs. last report.

## Installation

This is a Claude skill. Drop the `focusgroup/` directory into your skills location and Claude
will surface it on triggers like "test my agent", "persona test", "focus group", "dynamic eval",
"simulate users".

For the runtime:

```bash
pip install -r requirements.txt
```

Requirements: Python 3.10+, `pydantic`, `pyyaml`. Claude mode also needs
`anthropic`; Codex mode needs a locally authenticated `codex` CLI.

## Model backends

focusgroup can drive persona turns, LLM judges, and LLM theme clustering through
Claude or Codex:

```bash
# Claude / Anthropic backend (default)
export FOCUSGROUP_PERSONA_MODE=claude
export FOCUSGROUP_JUDGE_MODE=claude
export FOCUSGROUP_THEMES_MODE=claude

# Codex backend using your local Codex login
export FOCUSGROUP_PERSONA_MODE=codex
export FOCUSGROUP_JUDGE_MODE=codex
export FOCUSGROUP_THEMES_MODE=codex
```

Codex-specific knobs:

```bash
export FOCUSGROUP_CODEX_BIN=codex          # default
export FOCUSGROUP_CODEX_MODEL=             # optional; omit for Codex default
export FOCUSGROUP_CODEX_PROFILE=           # optional Codex profile
export FOCUSGROUP_CODEX_SANDBOX=read-only  # default for backend LLM calls
```

When `codex exec` fails, focusgroup includes the exit code, selected model, sandbox,
working directory, whether an output schema was used, and bounded stdout/stderr tails in
the raised `CodexError`. That makes transient CLI failures diagnosable even when Codex
prints useful context to stdout instead of stderr.

## Quickstart

In a Claude session in your project directory:

```
You: focusgroup init
Claude: [walks you through requirements, persona pool, adapter scaffold]

You: focusgroup add-feature greeting
Claude: [generates 3 scenarios under features/greeting/scenarios/]

You: focusgroup run --feature greeting --sample 0.2
Claude: [runs sampled scenarios, writes runs/<timestamp>-*/]

You: focusgroup report themes
Claude: [synthesizes findings across runs]
```

## Example

There's a working end-to-end example under `examples/example-project/`. It tests a stub greeting
agent. Run it directly:

```bash
cd examples/example-project
python -m runner.run --scenario greeting-novice-anxious
```

## Core primitives

- **Persona**: stable bundle of testing-relevant axes. Project-level, reused across features.
- **Intention**: the goal for one run.
- **Scenario**: `persona × intention × initial state × requirements × bounds`. Feature-level.
- **Requirement**: typed (functional / safety / performance / IX / correctness), has an ID
  (`F-001`, `S-003`, etc.). Failures trace back to requirement IDs.

See `reference/` for full schemas.

## Why these primitives

**Personas as axes, not demographics.** "30-year-old marketing manager" tells you nothing about
how they'll break your agent. "Competence 0.2, patience 0.3, adversariality 0.8" tells you
exactly how they'll behave.

**State-checks and invariants before LLM judges.** A failing state check is a fact. An LLM
judge is an opinion, and an expensive, slow, noisy one. We push you toward facts first.

**Requirements as the spine.** Every scenario references requirement IDs. Every failure traces
back to a requirement. You can answer "what does this product promise, and which promises is it
keeping?" — not just "is the latest commit better than the previous one?"

## When NOT to use focusgroup

- Pure unit-testable logic — use pytest
- UI / browser automation — use Playwright
- Non-conversational systems (batch jobs, pure classifiers) — use whatever you'd normally use

If your target isn't a multi-turn conversational system, this is the wrong tool.

## Architecture

```
focusgroup/
├── SKILL.md              # Claude's instructions
├── reference/            # schemas and protocols Claude reads
├── templates/            # files Claude copies into your project
├── adapters/             # pre-built SUT wrappers
├── runner/               # the runtime — actually executes scenarios
└── examples/             # working end-to-end project
```

The skill itself is instructions for Claude. The Python code in `runner/` and `adapters/` is the
runtime the skill orchestrates. Claude reads `SKILL.md`, then either invokes these scripts or
generates project-specific files using the templates.

## Future work (out of scope for v1)

- UI / browser SUTs
- Mining personas from real production usage data
- Visual report dashboards
- Parallel scenario execution
- Distributed runs

## License

MIT. See `LICENSE`.
