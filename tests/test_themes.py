from runner import themes


def test_llm_cluster_codex_mode(monkeypatch):
    def fake_complete_text(prompt, model=None):
        assert "RECURRING THEMES" in prompt
        assert "confusing" in prompt
        return "- Confusion: users were confused"

    monkeypatch.setattr(themes.codex_client, "complete_text", fake_complete_text)

    result = themes._llm_cluster(["This was confusing."], "codex")

    assert "Confusion" in result
