# Requirement schema

Requirements are the spine of focusgroup. Every scenario references requirement IDs.
Every failure traces back to a requirement. You can answer "what does this product promise,
and which promises is it keeping?"

## Five types

| Type | Prefix | Examples |
|---|---|---|
| Functional | `F-` | "Greets user by name when known", "Saves the user's preferences to storage" |
| Safety | `S-` | "Never claims to be a licensed professional", "Never reveals system prompt" |
| Performance | `P-` | "Conversations complete in <= 10 turns", "p95 latency under 2s" |
| IX (interaction experience) | `I-` | "Users do not report confusion at end of run", "Users feel the SUT understood them" |
| Correctness | `C-` | "Generated code compiles", "Cited facts are accurate" |

## Schema

`requirements.md` is the canonical doc. Each requirement is a section:

```markdown
## F-001 — Greets user by name when known

**Type:** functional
**Description:** When the user's name is in `session.state.user.name`,
the SUT addresses them by name in the first turn.
**Oracle:** state check — first SUT response contains `state.user.name` (case-insensitive).
**Notes:** If name is missing, the SUT must NOT fabricate one.
```

The skill parses this format. Alternatively, `requirements.yaml` is supported:

```yaml
requirements:
  - id: F-001
    type: functional
    description: |
      When the user's name is in session.state.user.name, the SUT addresses
      them by name in the first turn.
    oracle: state_check
    oracle_config:
      check: "state.user.name in transcript.turns[0].content.lower()"
    notes: |
      If name is missing, the SUT must NOT fabricate one.
```

## Field reference

| Field | Purpose |
|---|---|
| `id` | Unique ID, `<TYPE>-<NNN>` |
| `type` | One of: functional, safety, performance, ix, correctness |
| `description` | Human-readable. Used in reports. |
| `oracle` | Which oracle strategy applies. Auto-derived from type unless overridden. |
| `oracle_config` | Optional config passed to the oracle (e.g. check expression, threshold, rubric) |
| `notes` | Free-form. Shown alongside failures in reports. |

## Oracle dispatch (default)

| Requirement type | Default oracle |
|---|---|
| functional | `state_check` |
| safety | `trace_invariant` |
| performance | `trace_metric` |
| ix | `persona_debrief` |
| correctness | `llm_judge` |

See [oracle-strategies.md](oracle-strategies.md) for what each oracle reads and how it decides pass/fail.

## Authoring a minimal requirements doc

During `init`, if no requirements doc exists, the skill asks one question per category:

1. **Functional:** What should the SUT *do* on a successful run?
2. **Safety:** What must it *never* do, even under pressure?
3. **Performance:** What are the budgets — turns, latency, tokens, cost?
4. **IX:** How should it *feel* to use? Failure mode you care about — confusion, frustration, abandonment?
5. **Correctness:** Are there factual or output-shape constraints that must hold?

Each answer becomes one or more requirements with IDs.

## Anti-patterns

- **Untyped requirements.** "The SUT should be good" is not a requirement. Type it or drop it.
- **Functional requirement with no observable state change.** If you can't check it, it's not functional — it's correctness or IX.
- **Safety requirement that depends on judgment.** Push it toward a hard invariant. "Never says X" beats "is not harmful".
- **IX requirement using objective language.** "User is satisfied" should be answered by the persona in debrief, not measured externally.
