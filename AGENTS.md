# Project Instructions

This repository packages the `focusgroup` skill and its Python runtime.

When the user asks to test a conversational agent, create persona-driven evaluation scenarios,
or run a dynamic eval, load `SKILL.md` and follow its path selector. Use `references/` lazily;
use `templates/`, `adapters/`, and `runner/` only for the active evaluation task.

When the user asks to maintain this repository, preserve deterministic oracle coverage and run
`python3 -m pytest tests` after changing the skill, runtime, templates, or references.
