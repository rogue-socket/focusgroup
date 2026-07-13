# Host adapters

| Host | Discovery file | Start instruction |
|---|---|---|
| Claude Code | `SKILL.md` and `CLAUDE.md` | `focusgroup init` or `test my agent with focusgroup` |
| Codex | `AGENTS.md` or `~/.codex/skills/focusgroup` | `Use the focusgroup skill to test this conversational agent.` |
| GitHub Copilot | `.github/copilot-instructions.md` | `Use the focusgroup skill in this repo to test my conversational agent.` |

All hosts use the target project as the workspace. Load `SKILL.md` first and lazy-load the
reference for the selected path or active command. The Python runtime requires the dependencies
in `requirements.txt`; Codex-backed model calls require a locally authenticated `codex` CLI.
