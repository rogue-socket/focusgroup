# Evaluation failure patterns

Use these as grounded case patterns. Do not invent company-specific details; the point is the
failure mechanism and the evidence it requires.

## Happy-path-only evaluation

A demo succeeds because the evaluator always phrases the request ideally. Countermeasure:
contrasting personas and initial states tied to explicit requirements.

## Judge-only validation

An LLM says an answer was good while a forbidden action occurred in the trace. Countermeasure:
safety invariants and state checks take precedence over a judge's prose verdict.

## Flaky result treated as a product fact

One stochastic run is used to declare success or failure. Countermeasure: repeat important
scenarios, report variance, and preserve configuration with the artifacts.

## Persona stereotype instead of behavior

Demographic labels substitute for clear intentions and interaction traits. Countermeasure:
axis-based personas with inspectable YAML values.

## Unbounded autonomous evaluation

A test loops, spends unexpectedly, or invokes unsafe side effects. Countermeasure: max turns,
stuck detection, cost caps, and an explicit safe test target.
