from pathlib import Path
from types import SimpleNamespace

import pytest

from runner import codex_client


def test_complete_json_invokes_codex_exec(monkeypatch):
    calls = []

    def fake_run(cmd, input, text, capture_output, check):
        calls.append({
            "cmd": cmd,
            "input": input,
            "text": text,
            "capture_output": capture_output,
            "check": check,
        })
        out_path = Path(cmd[cmd.index("-o") + 1])
        out_path.write_text('{"ok": true}')
        return SimpleNamespace(returncode=0, stdout="", stderr="")

    monkeypatch.setenv("FOCUSGROUP_CODEX_BIN", "codex-test")
    monkeypatch.setenv("FOCUSGROUP_CODEX_MODEL", "gpt-test")
    monkeypatch.setattr(codex_client.subprocess, "run", fake_run)

    result = codex_client.complete_json(
        "prompt text",
        {"type": "object", "properties": {"ok": {"type": "boolean"}}},
    )

    assert result == {"ok": True}
    cmd = calls[0]["cmd"]
    assert cmd[:3] == ["codex-test", "exec", "--json"]
    assert "--output-schema" in cmd
    assert ["--model", "gpt-test"] == cmd[cmd.index("--model") : cmd.index("--model") + 2]
    assert cmd[-1] == "-"
    assert calls[0]["input"] == "prompt text"


def test_complete_text_falls_back_to_jsonl(monkeypatch):
    def fake_run(cmd, input, text, capture_output, check):
        return SimpleNamespace(
            returncode=0,
            stdout='{"type":"final","message":"done"}\n',
            stderr="",
        )

    monkeypatch.setattr(codex_client.subprocess, "run", fake_run)

    assert codex_client.complete_text("prompt") == "done"


def test_complete_text_jsonl_fallback_ignores_event_type(monkeypatch):
    def fake_run(cmd, input, text, capture_output, check):
        return SimpleNamespace(
            returncode=0,
            stdout='{"type":"agent_message","payload":{"content":"real text"}}\n',
            stderr="",
        )

    monkeypatch.setattr(codex_client.subprocess, "run", fake_run)

    assert codex_client.complete_text("prompt") == "real text"


def test_complete_text_error_includes_context_and_output_tails(monkeypatch):
    def fake_run(cmd, input, text, capture_output, check):
        return SimpleNamespace(
            returncode=1,
            stdout="stdout detail\n" * 500,
            stderr="stderr detail",
        )

    monkeypatch.setenv("FOCUSGROUP_CODEX_MODEL", "gpt-test")
    monkeypatch.setenv("FOCUSGROUP_CODEX_SANDBOX", "workspace-write")
    monkeypatch.setenv("FOCUSGROUP_CODEX_CWD", "/tmp/project")
    monkeypatch.setattr(codex_client.subprocess, "run", fake_run)

    with pytest.raises(codex_client.CodexError) as exc:
        codex_client.complete_text(
            "prompt",
            output_schema={"type": "object"},
        )

    message = str(exc.value)
    assert "codex exec failed with exit code 1" in message
    assert "model: gpt-test" in message
    assert "sandbox: workspace-write" in message
    assert "cwd: /tmp/project" in message
    assert "output_schema: yes" in message
    assert "stderr tail:\nstderr detail" in message
    assert "stdout tail:" in message
    assert "stdout detail" in message
