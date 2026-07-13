# Anti-patterns with paired examples

## LLM judge as the only oracle

**Bad:** "The judge liked the answer, so the agent is safe."

**Better:** Check the action trace for forbidden behavior first; use a judge only for genuinely
semantic correctness that cannot be made deterministic.

## Persona generated per feature

**Bad:** Regenerate personas for every feature and lose behavioral comparability.

**Better:** Keep a project-level pool and vary scenarios, not the definition of the user.

## Run before review

**Bad:** Generate many scenarios and spend model budget immediately.

**Better:** Review three scenarios, cost, bounds, and side-effect safety before the first run.

## Fixing the test to hide a failure

**Bad:** Rewrite the scenario after a failing run without retaining the reproduction.

**Better:** Preserve the old artifact; add a narrower scenario only if it makes the requirement
more precise.
