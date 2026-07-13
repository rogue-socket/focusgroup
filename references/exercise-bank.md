# Exercise bank

Choose one small exercise at a time. Each exercise should create or inspect an actual artifact.

## Requirement-to-oracle mapping

Given five product promises, classify each type and choose the cheapest valid oracle. Success:
no requirement reaches for an LLM judge when a state check, invariant, or metric would work.

## Persona contrast

Create two personas that pursue the same intention with contrasting competence and patience.
Success: their scenario behavior differs for a reason visible in the persona YAML.

## Stuck-loop reproduction

Create a deterministic adapter that repeats an unhelpful response. Success: the scenario stops
at its configured stuck boundary and the trace records the reason.

## Safety invariant

Add an action that must never occur, write a trace invariant, and reproduce one passing and one
failing run. Success: `result.json` contains evidence for both verdicts.

## Theme calibration

Run a small fixture set, compare a deterministic failure with a stochastic one, and write a
report that states sample size and does not generalize beyond it.
