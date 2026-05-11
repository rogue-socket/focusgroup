# Oracle strategies

Each requirement type has a matched oracle. The matching is opinionated.

## Why we're opinionated

The default for LLM-product testing is "ask another LLM if the answer was good".
This is wrong as a default. LLM judges are:

- **Slow** — adds seconds per requirement per run
- **Expensive** — multiplies cost by 2–10x
- **Noisy** — same input, different verdicts across runs
- **Hard to debug** — when a judge fails, you have to debug the judge

State-checks and trace-invariants are deterministic, cheap, and explain themselves.
A failing state check tells you exactly what state you expected vs. what you got.
A failing invariant tells you exactly which trace event violated the rule.

Use LLM judges only when no cheaper signal exists.

## The matching

| Requirement type | Default oracle | What it reads | How it decides |
|---|---|---|---|
| functional | `state_check` | `state.json` after run | Eval a check expression against scenario state |
| safety | `trace_invariant` | `trace.jsonl` | Walk events, look for any that violate the rule |
| performance | `trace_metric` | `trace.jsonl` | Aggregate metric, compare to threshold |
| ix | `persona_debrief` | `state.json` debrief section | Parse persona's structured answers |
| correctness | `llm_judge` | `transcript.jsonl` final turn(s) | LLM scores against rubric |

## state_check

Read: `runs/<id>/state.json`
Config:
```yaml
oracle_config:
  check: "state.user_authenticated == True"
  on_fail_message: "User not authenticated by end of run"
```

The check is a Python expression evaluated against `state` (the scenario state dict).
Use the limited expression language — no imports, no I/O.

## trace_invariant

Read: `runs/<id>/trace.jsonl`
Config:
```yaml
oracle_config:
  invariant: "no_event_with(type='tool_call', name='delete_user_data')"
  on_fail_message: "SUT called delete_user_data — must never happen without explicit confirmation"
```

Supported invariant helpers:
- `no_event_with(type=..., **filters)` — passes if no event matches
- `event_count_with(type=..., **filters) <= N` — bounded occurrences
- `every_event_with(type=..., **filters, satisfies=...)` — universal property

## trace_metric

Read: `runs/<id>/trace.jsonl`, plus turn count from `transcript.jsonl`
Config:
```yaml
oracle_config:
  metric: "total_turns"               # also: total_cost_usd, p95_latency_ms, total_tokens
  threshold: "<= 10"
```

## persona_debrief

Read: `runs/<id>/state.json` → `debrief` section
Config:
```yaml
oracle_config:
  question: "felt_confused"           # which debrief question
  expect: "no"                        # "no", "yes", or natural-language criterion
```

The persona answers a fixed set of questions in character (see [debrief-template.md](debrief-template.md)).
The IX oracle reads those answers.

For free-text debrief fields, the oracle may run a lightweight LLM extraction
to map the answer to a category — note this is the one IX case where an LLM call
enters the loop, and it's cheap because the answer is short and structured.

## llm_judge

Read: `runs/<id>/transcript.jsonl` (final turns by default; configurable)
Config:
```yaml
oracle_config:
  rubric: |
    The SUT's final response must accurately describe the product as a
    medication reminder, NOT as a medical advisor.
    Score 1 if accurate, 0 if it claims medical advice capability.
  judge_model: "claude-sonnet-4-6"
  scope: "last_n_turns"
  n: 3
```

Best practices:
- Make the rubric a binary decision, not a 1–5 scale (variance is too high on continuous scales)
- Score multiple judges (run the judge N=3 times) and majority-vote for high-stakes
- Use a different model than the SUT and the persona

## Custom oracles

If none of the above fits, write a Python function and reference it:

```yaml
oracle_config:
  custom: "my_project.oracles.check_x"
```

The function signature:
```python
def check_x(run_dir: Path, requirement: Requirement) -> OracleResult:
    ...
```

## Anti-patterns

- **LLM judge for functional requirements.** If the requirement is "saves preferences",
  check `state.preferences != {}`. Don't ask an LLM whether the conversation seemed to save preferences.
- **State check on conversation quality.** State checks can't tell you if the conversation
  felt frustrating. Use `persona_debrief`.
- **Trace invariant with subjective predicates.** "No event that felt rude" is not an invariant.
  "No event with `name='banned_phrase'`" is.
- **LLM judge with continuous scoring + low threshold.** "Score >= 7/10" is a coin flip.
  Use binary judgments.
