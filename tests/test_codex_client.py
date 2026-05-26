from pathlib import Path
from types import SimpleNamespace

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
