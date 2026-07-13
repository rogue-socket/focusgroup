# Practical mode

Use this for the practice-first path or whenever a learner wants immediate evidence.

1. Run the deterministic greeting example with stub modes before spending on a real model.
2. Inspect `transcript.md`, `state.json`, `trace.jsonl`, and `result.json` in that order.
3. Copy one adapter template into the target project and make one scenario pass through the
   whole loop at `--n 1`.
4. Add one requirement category or oracle at a time; do not scaffold a large persona pool before
   a first run proves the adapter boundary works.
5. Before scaling, estimate cost and review scenarios. Use `--sample` for iterative feedback.

## Minimum evidence bundle for a side-effect-free run

When the SUT normally reaches accounts, payments, email, or other real systems, do not call a
run safe merely because the transcript sounds safe. Capture all of the following:

1. A mock-tool call log proving zero production lookups, mutations, and sends.
2. An explicit tool allowlist (or denylist) proving all unapproved tools were unavailable.
3. The identifier or version of the approved instruction, fixture, or policy returned to the
   persona.
4. Requirement-linked transcript and trace evidence for every functional and safety assertion.

For a password-reset smoke test, assert the approved instructions are returned, no credential is
requested, and no account lookup, password change, email, or SMS send occurs. Keep the action a
no-op even when the production bot normally performs those calls.

If the first run fails because the adapter cannot reach the SUT, fix that integration boundary
before diagnosing persona behavior or changing prompts.
