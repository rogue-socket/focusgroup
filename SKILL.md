---
name: focusgroup
description: Build and run persona-driven dynamic test suites for conversational AI products. Use when the user wants to stress-test a conversational agent, chatbot, or LLM-backed module with realistic simulated users; generate or run focus-group-style tests; or create persona pools, scenarios, and oracles tied to requirements (functional, safety, performance, IX, correctness). Triggers on phrases like "test my agent", "persona test", "focus group", "dynamic eval", "simulate users", "stress test conversational", and when designing acceptance tests for chat-based products. Do NOT use for pure unit-testable logic, UI/browser automation, or non-conversational systems.
---

# focusgroup

A skill for **persona-driven dynamic testing** of conversational AI products.

The mental model: treat the system under test (SUT) the way a real focus group treats a prototype.
Recruit diverse personas, give each one a real intention, watch them try to accomplish it,
then debrief them in character and aggregate findings across runs.

Static evals and unit tests catch logic bugs. focusgroup catches the things that only emerge
when a stubborn novice, an impatient expert, and a probing adversary actually use the thing.

## When to use this skill

**Use it when:**
- The user has a conversational agent / chatbot / LLM-backed module to test
- They want acceptance tests tied to product requirements, not just regression tests
- They want to surface IX failures (confusion, frustration, abandonment) that judges-of-correctness miss
- They want regression coverage that survives prompt and model changes

**Do not use it for:**
- Pure unit-testable logic (use pytest)
- UI / browser automation (use Playwright)
- Non-conversational systems (batch jobs, classifiers without dialogue, etc.)

If the user's target isn't conversational, say so and stop.

## Choose a path

When a user is new to focusgroup, offer these two routes before choosing the first command.
Do not infer the route from seniority: someone experienced with agents may still want the
bottom-up explanation, and someone new may learn better from a successful first run.

| Path | Shape | First outcome |
|---|---|---|
| **Foundations-first** | Bottom-up: requirements → oracle choice → personas → scenarios → run → themes | A small, traceable test plan whose requirements and oracles are understood before execution |
| **Practice-first** | Top-down: run the deterministic greeting example → inspect artifacts → adapt one scenario to the user's SUT → fill in the missing requirements and coverage | One real run and its transcript, state, trace, and result files |

If the user says they want to understand evaluation design, is defining a new product, or is
worried about safety/correctness coverage, suggest **foundations-first**. If they want to see
the tool work, already have a conversational SUT, or ask for a quick smoke test, suggest
**practice-first**. The user can switch at any command boundary.

### Foundations-first (bottom-up)

1. Explain the five requirement types using the user's product, then create or review
   `requirements.md` with at least one requirement and the cheapest suitable oracle.
2. Explain persona axes, then create a small pool with deliberately different competence,
   patience, and adversariality.
3. Create one scenario that names requirement IDs and explicit loop bounds.
4. Scaffold the adapter, run that one scenario, and inspect its `result.json` against the
   requirement before adding more scenarios or generating themes.

### Practice-first (top-down, teaching by doing)

1. Run the deterministic greeting example first. It requires no API key:

   ```bash
   FOCUSGROUP_PERSONA_MODE=stub FOCUSGROUP_JUDGE_MODE=stub \
       python -m runner.run --project-dir examples/example-project --scenario greeting-novice-anxious
   ```

2. Open the resulting `transcript.md`, `state.json`, `trace.jsonl`, and `result.json`. Explain
   each file only after the learner has seen it in a real run.
3. Copy the smallest relevant adapter template into the user's project, create one scenario for
   one requirement, and run it at `--n 1`.
4. Backfill the requirement categories, persona pool, and scenario coverage through the normal
   `init` and `add-feature` flow. Do not treat one passing smoke run as a complete eval suite.

## The four commands

This skill orchestrates four operations. When the user invokes focusgroup, identify which command
applies and follow the matching playbook below.

| Command | When | Side effects |
|---|---|---|
| `init` | Once per project, before anything else | Creates `requirements.md` (or confirms existing), scaffolds `adapter.py`, generates persona pool under `personas/` |
| `add-feature <name>` | Adding a new feature to test | Creates `features/<name>/scenarios/*.yaml`, reusing project personas |
| `run` | Executing scenarios | Writes `runs/<timestamp>/` artifacts |
| `report themes` | Synthesizing findings | Reads `runs/`, emits clustered feedback |

### Command 1: `init`

1. **Check for an existing requirements doc.** Search these paths in order:
   `requirements.md`, `REQUIREMENTS.md`, `docs/requirements.md`, `docs/requirements.yaml`,
   `spec.md`, `PRD.md`.

   - If found: parse it. Categorize each statement as functional / safety / performance / IX / correctness.
     Show the user the categorization and flag missing categories. Confirm or correct with them.
   - If missing: walk the user through authoring a minimal one. Ask one targeted question per category:
     - Functional: "What is the SUT supposed to accomplish on a successful run?"
     - Safety: "What must it never do, even under pressure?"
     - Performance: "What are the budgets — turns, latency, tokens, cost?"
     - IX: "How should it feel to use? What's the failure mode you care about — confusion? frustration? abandonment?"
     - Correctness: "Are there factual or output-shape constraints that must hold?"
     Write the result to `requirements.md` using `templates/requirements.md.template`.

2. **Assign requirement IDs.** Functional `F-001`, safety `S-001`, performance `P-001`,
   IX `I-001`, correctness `C-001`. These IDs are referenced by scenarios and trace
   back from failure reports.

3. **Generate the persona pool.** Hybrid generation:
   - Start with 5–8 seed archetypes from `templates/persona-archetypes/` that fit the product domain.
   - Use the persona LLM to produce 2–3 variants per archetype, shifting axis values
     (competence, patience, adversariality, communication style, prior knowledge).
   - Write each persona as YAML under `personas/<name>.yaml`. Confirm the pool with the user.
   - **Personas are project-level and reused across features.** Do not regenerate per feature.

4. **Scaffold the adapter.** Ask the user how the SUT is reachable:
   - OpenAI-compatible chat API → copy `adapters/openai_compatible.py` and prompt for endpoint/model
   - Generic HTTP POST `/chat` → copy `adapters/http_chat.py` and prompt for request/response shape
   - stdio CLI → copy `adapters/stdio_cli.py` and prompt for command
   - Python callable (in-process) → copy `adapters/python_callable.py` and prompt for import path
   - Custom → copy `adapters/base.py` and have them implement `respond()`
   Write to `adapter.py` at project root.

5. **Surface a cost estimate.** Before the user runs anything, estimate cost based on
   persona pool size × default scenarios per feature × loop bounds × token estimates for
   persona-side and judge-side LLMs. State the estimate explicitly.

### Command 2: `add-feature <name>`

1. **Read the requirements doc** and identify which requirements apply to this feature.
   Confirm the subset with the user.
2. **Generate scenarios.** Each scenario is `persona × intention × initial state × requirements × bounds`.
   - Pull 3–5 personas from the project pool, weighted toward axis diversity.
   - For each persona, generate 1–2 plausible intentions for this feature.
   - Reference specific requirement IDs.
   - Set loop bounds (defaults: 20 turns, cost cap $0.50, stuck detection over 5 turns).
   - Write each scenario as `features/<name>/scenarios/<scenario-id>.yaml` using `templates/scenario.yaml.template`.
3. **Show the user the generated scenarios.** Ask for adjustments. Don't run yet.
4. **Default scale:** start with 3 scenarios. Surface a cost estimate before scaling further.

### Command 3: `run`

Flags:
- `--feature <name>` — run all scenarios for a feature
- `--scenario <id>` — run a single scenario
- `--sample <0.0–1.0>` — sample fraction of available scenarios (default `0.2` for fast dev feedback)
- `--n <int>` — repeat each scenario N times (default 1, recommend 5 for high-stakes scenarios)

Implementation:
1. Resolve scenarios via flags. Show the user the resolved list + cost estimate. Confirm.
2. Invoke `python -m runner.run --scenario <ids>`.
3. For each scenario:
   - Create `runs/<timestamp>-<scenario-id>/`
   - Run `persona_loop.py`, which alternates persona turn → adapter turn until a loop bound trips
   - Write `transcript.jsonl` (source of truth), `transcript.md` (rendered), `state.json` (turn ownership, scenario state, persona internals, debrief), `trace.jsonl` (structured events)
   - On end-of-run: persona answers debrief questions in character → appended to `state.json`
   - Run oracles matched to each referenced requirement type → `result.json`
4. Print a per-run summary table.

### Command 4: `report themes [--since DATE]`

1. Walk `runs/` directory (filter by `--since` if given).
2. Cluster persona debrief responses by theme (LLM-assisted).
3. Segment failures by persona axis (e.g. "novice-anxious personas fail F-003 at 80%, experts fail at 5%").
4. Diff against the previous report: new themes, resolved themes, regressions.
5. Distinguish "always fails" (deterministic bugs) from "sometimes fails" (flaky / stochastic).
6. Write `reports/<timestamp>.md` and print summary.

## Core primitives

See the reference docs for full schemas:
- [reference/persona-schema.md](reference/persona-schema.md)
- [reference/scenario-schema.md](reference/scenario-schema.md)
- [reference/requirement-schema.md](reference/requirement-schema.md)
- [reference/adapter-protocol.md](reference/adapter-protocol.md)
- [reference/oracle-strategies.md](reference/oracle-strategies.md)
- [reference/debrief-template.md](reference/debrief-template.md)

## Learning and operating references

Load only the reference needed by the selected path or current command:

- `references/curriculum.md` — foundations-first evaluation syllabus
- `references/practical-mode.md` — practice-first smoke-to-suite workflow
- `references/exercise-bank.md` — small artifact-based practice tasks
- `references/incidents.md` — common evaluation failure mechanisms
- `references/theory-modes.md` — explain, trace-walk, Socratic, build, and review modes
- `references/session-control.md` — target-project resume, checkpoint, and pause rules
- `references/spaced-repetition.md` — regression rerun cadence
- `references/anti-patterns-with-examples.md` — paired evaluation failure patterns
- `references/host-adapters.md` — Claude Code, Codex, and GitHub Copilot entry rules

### Persona axes (NOT demographics)

Personas are stable bundles of testing-relevant traits:
- **competence** (0–1): how well they understand the domain
- **patience** (0–1): how many turns before they give up
- **adversariality** (0–1): how much they probe / try to break things
- **communication style**: terse, verbose, formal, casual, vague, precise
- **prior knowledge**: what they assume about the product before starting

A persona is project-level. The same novice-anxious persona is reused across features.

### Requirement types and matched oracles

| Requirement type | Oracle strategy | Why |
|---|---|---|
| Functional | Goal-state check via `session.state` | Deterministic, cheap, unambiguous |
| Safety | Hard invariants on `trace.jsonl` | A safety violation is a fact, not a judgment |
| Performance | Quantitative metrics on trace | Counted, not judged |
| IX | Structured persona debrief in `state.json` | The persona is the user; their experience is the metric |
| Correctness | LLM judge with rubric | Last resort — only when no cheaper signal exists |

**Be opinionated about this.** Push users toward state checks and invariants first.
LLM judges are slow, expensive, and noisy. They are the fallback, not the default.
See [reference/oracle-strategies.md](reference/oracle-strategies.md) for the full reasoning.

## Loop bounds

Every scenario terminates via at least one of:
1. **Max turns** (default 20)
2. **Persona declares done** (in character — "thanks, that's all I needed")
3. **Stuck detection** (no measurable progress for N consecutive turns, default 5)
4. **Cost cap** (tokens or dollars, default $0.50)

All four are enabled by default. Configurable per scenario.

## File-based communication

Each run writes to `runs/<timestamp>-<scenario-id>/`:

| File | Role |
|---|---|
| `transcript.jsonl` | Source of truth. One JSON object per turn. `{"role": "user"|"sut"|"tool_call", "content": ..., "ts": ..., "turn": N}` |
| `transcript.md` | Human-readable view rendered from JSONL |
| `state.json` | Turn ownership lock, scenario state, persona internals, end-of-run debrief |
| `trace.jsonl` | Structured events for invariant oracles (tool calls, latencies, token counts) |
| `result.json` | Per-requirement-ID pass/fail verdict + evidence |

Turn ownership in `state.json` exists to prevent the persona loop and the adapter from
writing simultaneously. The runner writes `"owner": "persona"` or `"owner": "sut"` and flips
it after each turn.

## Defaults

- Persona pool: 5 archetypes, 2 variants each = ~10 personas total
- Scenarios per new feature: 3 to start
- `--sample 0.2` for iterative development
- Aggregate N=5 runs per high-stakes scenario before drawing conclusions
- Persona LLM, judge LLM, SUT LLM are configured **separately** — warn if all three are the same model (an LLM judging its own outputs is a known failure mode)
- Runtime LLM modes: `FOCUSGROUP_PERSONA_MODE`, `FOCUSGROUP_JUDGE_MODE`, and `FOCUSGROUP_THEMES_MODE` accept `anthropic`/`claude`, `codex`, or `stub` where applicable. Codex mode uses the local `codex` CLI and the user's existing local login.

## Anti-patterns to flag

- **LLM judge as the only oracle.** Push back. Suggest a state-check or invariant first.
- **Demographic personas.** "30-year-old marketing manager from Brooklyn" tells you nothing about how they'll break the SUT. Push toward axis-based personas.
- **Personas regenerated per feature.** Personas are project-level. Reuse them.
- **Running before reviewing scenarios.** Always show the user the generated scenarios first.
- **Running at full scale before estimating cost.** Always show cost estimate, always start with `--sample 0.2`.

## Out of scope for v1

- UI / browser SUTs
- Mining personas from real production transcripts
- Visual report dashboards
- Parallel scenario execution
- Distributed runs

See `README.md` future work section.
