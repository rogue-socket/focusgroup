# Regression cadence

Focusgroup's equivalent of spaced review is deliberate scenario reruns rather than flashcards.

| Trigger | Review action |
|---|---|
| Prompt, model, tool, or retrieval change | Rerun affected scenarios before release |
| New failure | Turn the minimal reproduction into a named scenario and rerun after the fix |
| High-stakes behavior | Repeat the scenario at `--n 5` or more and report variance |
| Monthly product iteration | Revisit personas and requirements; retire only scenarios whose promise no longer exists |

Keep historical `runs/` artifacts. A regression claim needs a comparison to a prior run with the
same scenario and materially comparable settings.
