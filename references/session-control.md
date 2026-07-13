# Session control

Focusgroup state belongs to the target project, not this repository. At session start, inspect
the target's `requirements.md`, `personas/`, `features/`, and newest `runs/` result before
proposing work.

## Checkpoint after every meaningful step

Record the next action in the target project's issue, PR, or `reports/` output. A good
checkpoint names the scenario, requirement IDs, observed verdict, evidence path, and next
decision.

## Resume protocol

1. Identify the latest run and whether it failed deterministically, stochastically, or due to
   infrastructure.
2. Propose one smallest next action: adapter repair, oracle repair, scenario change, or product
   fix.
3. Preserve old run artifacts; never overwrite evidence to make a rerun look cleaner.

## Complete the current question before advancing

When a user asks a direct question about setup, cost, side effects, evidence, or an oracle,
answer it before proposing the next scenario or run. Do not replace an auditability question
with a generic “run it and inspect the trace” instruction: name the exact artifact and assertion
that will prove the claim.

## Pause protocol

Stop before a paid or broad run if scenarios have not been reviewed, cost is unknown, or the
SUT's side effects are not explicitly safe for the test environment.
