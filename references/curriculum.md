# Evaluation curriculum

Use this as the foundations-first syllabus. Each unit produces an artifact that the next unit
uses; do not teach a unit only as vocabulary.

## Unit 1 — What dynamic evaluation measures

Distinguish unit tests, static evals, and persona-driven conversations. Outcome: one sentence
describing a failure that only a multi-turn user interaction can expose.

## Unit 2 — Requirements and evidence

Classify promises as functional, safety, performance, IX, or correctness. Outcome:
`requirements.md` with a requirement ID and the cheapest suitable oracle for each promise.

## Unit 3 — Personas as behavioral axes

Define competence, patience, adversariality, communication style, and prior knowledge without
using demographics as a proxy. Outcome: a small, diverse project-level persona pool.

## Unit 4 — Scenarios and bounds

Compose persona × intention × initial state × requirement IDs × bounds. Outcome: one reviewable
scenario with a max-turn, stuck, and cost boundary.

## Unit 5 — Oracles and traces

Prefer state checks, trace invariants, and metrics over LLM judgment. Outcome: a run whose
`result.json` points to evidence in state or trace artifacts.

## Unit 6 — Regression and themes

Repeat important scenarios, compare runs, and cluster persona debriefs without overstating
small samples. Outcome: a focused report with a concrete product follow-up.

## Practical bridge

After Unit 3, learners may switch to the practice-first route in `SKILL.md`; after one real run,
return to the lowest unfinished unit rather than skipping coverage design.
