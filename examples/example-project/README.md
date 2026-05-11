# Example focusgroup project: greeting agent

A minimal end-to-end demo of focusgroup. The SUT is a 30-line stub greeting agent
defined inline in `adapter.py`. It greets the user, asks their name, and remembers it.

## Run it

From the repo root, with the focusgroup `adapters/` and `runner/` modules on the path:

```bash
FOCUSGROUP_PERSONA_MODE=stub FOCUSGROUP_JUDGE_MODE=stub \
    python -m runner.run \
    --project-dir examples/example-project \
    --feature greeting
```

This uses the deterministic stub persona LLM (no API key needed), executes all scenarios
under `features/greeting/scenarios/`, and writes results to `examples/example-project/runs/`.

You can also run a single scenario:

```bash
FOCUSGROUP_PERSONA_MODE=stub FOCUSGROUP_JUDGE_MODE=stub \
    python -m runner.run \
    --project-dir examples/example-project \
    --scenario greeting-novice-anxious
```

## With a real persona LLM

```bash
export ANTHROPIC_API_KEY=...
python -m runner.run \
    --project-dir examples/example-project \
    --feature greeting
```

## Layout

```
examples/example-project/
├── requirements.md           # 5 requirements, one per type
├── adapter.py                # stub SUT + python_callable adapter
├── personas/                 # 2 personas reused across scenarios
│   ├── novice-anxious.yaml
│   └── expert-terse.yaml
└── features/
    └── greeting/
        └── scenarios/
            ├── greeting-novice-anxious.yaml
            └── greeting-expert-terse.yaml
```

The `personas/` and `features/` directories follow the layout focusgroup expects
in any project that uses it.
