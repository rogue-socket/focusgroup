from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_skill_run_flag_matches_runner_cli():
    skill = (ROOT / "SKILL.md").read_text()
    runner = (ROOT / "runner" / "run.py").read_text()

    assert "--scenario <ids>" in skill
    assert 'add_argument("--scenario"' in runner
    assert "--scenarios" not in skill


def test_skill_and_readme_define_both_adoption_paths():
    skill = (ROOT / "SKILL.md").read_text().lower()
    readme = (ROOT / "README.md").read_text().lower()

    for document in (skill, readme):
        assert "foundations-first" in document
        assert "practice-first" in document

    assert "requirements → oracle choice → personas → scenarios → run → themes" in skill
    assert "run the deterministic greeting example" in skill


def test_shared_skill_anatomy_is_present():
    for path in (
        "AGENTS.md",
        "CLAUDE.md",
        ".github/copilot-instructions.md",
        "SKILL_ANATOMY.md",
        "references/curriculum.md",
        "references/practical-mode.md",
        "references/exercise-bank.md",
        "references/incidents.md",
        "references/theory-modes.md",
        "references/session-control.md",
        "references/spaced-repetition.md",
        "references/anti-patterns-with-examples.md",
        "references/host-adapters.md",
    ):
        assert (ROOT / path).is_file(), f"missing shared skill component: {path}"


def test_transcript_learning_rules_are_documented():
    practical = (ROOT / "references" / "practical-mode.md").read_text()
    session = (ROOT / "references" / "session-control.md").read_text()

    assert "Minimum evidence bundle for a side-effect-free run" in practical
    assert "mock-tool call log" in practical
    assert "Complete the current question before advancing" in session
