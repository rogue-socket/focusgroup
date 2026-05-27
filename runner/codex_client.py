"""Codex CLI backend for focusgroup LLM calls."""
from __future__ import annotations

import json
import os
import subprocess
import tempfile
from pathlib import Path
from typing import Any

_OUTPUT_TAIL_CHARS = 4_000


class CodexError(RuntimeError):
    """Raised when the Codex CLI call fails or returns unusable output."""


def complete_text(
    prompt: str,
    *,
    model: str | None = None,
    output_schema: dict[str, Any] | None = None,
) -> str:
    """Run `codex exec` once and return its final message."""
    codex_bin = os.environ.get("FOCUSGROUP_CODEX_BIN", "codex")
    selected_model = model or os.environ.get("FOCUSGROUP_CODEX_MODEL")
    profile = os.environ.get("FOCUSGROUP_CODEX_PROFILE")
    sandbox = os.environ.get("FOCUSGROUP_CODEX_SANDBOX", "read-only")
    cwd = os.environ.get("FOCUSGROUP_CODEX_CWD")

    with tempfile.TemporaryDirectory() as tmp:
        tmp_dir = Path(tmp)
        out_path = tmp_dir / "last_message.txt"
        cmd = [
            codex_bin,
            "exec",
            "--json",
            "--ephemeral",
            "--skip-git-repo-check",
            "-o",
            str(out_path),
        ]
        if cwd:
            cmd.extend(["--cd", cwd])
        if selected_model:
            cmd.extend(["--model", selected_model])
        if profile:
            cmd.extend(["--profile", profile])
        if sandbox:
            cmd.extend(["--sandbox", sandbox])
        if output_schema is not None:
            schema_path = tmp_dir / "output_schema.json"
            schema_path.write_text(json.dumps(output_schema))
            cmd.extend(["--output-schema", str(schema_path)])
        cmd.append("-")

        proc = subprocess.run(
            cmd,
            input=prompt,
            text=True,
            capture_output=True,
            check=False,
        )
        if proc.returncode != 0:
            raise CodexError(
                _failure_message(
                    proc,
                    model=selected_model,
                    sandbox=sandbox,
                    cwd=cwd,
                    output_schema=output_schema,
                )
            )
        if out_path.exists():
            text = out_path.read_text().strip()
            if text:
                return text
        fallback = _last_text_from_jsonl(proc.stdout)
        if fallback:
            return fallback
        raise CodexError("codex exec completed without a final message")


def complete_json(
    prompt: str,
    schema: dict[str, Any],
    *,
    model: str | None = None,
) -> dict[str, Any]:
    """Run Codex with a JSON schema and parse a JSON object from the final message."""
    text = complete_text(prompt, model=model, output_schema=schema)
    try:
        parsed = json.loads(text)
    except json.JSONDecodeError:
        start = text.find("{")
        end = text.rfind("}")
        if start == -1 or end == -1:
            raise CodexError(f"codex returned non-JSON output: {text[:200]}")
        parsed = json.loads(text[start : end + 1])
    if not isinstance(parsed, dict):
        raise CodexError("codex JSON output must be an object")
    return parsed


def _failure_message(
    proc: subprocess.CompletedProcess[str],
    *,
    model: str | None,
    sandbox: str | None,
    cwd: str | None,
    output_schema: dict[str, Any] | None,
) -> str:
    parts = [
        f"codex exec failed with exit code {proc.returncode}",
        f"model: {model or '<default>'}",
        f"sandbox: {sandbox or '<none>'}",
        f"cwd: {cwd or os.getcwd()}",
        f"output_schema: {'yes' if output_schema is not None else 'no'}",
    ]
    if proc.stderr.strip():
        parts.append("stderr tail:\n" + _tail(proc.stderr))
    if proc.stdout.strip():
        parts.append("stdout tail:\n" + _tail(proc.stdout))
    return "\n".join(parts)


def _tail(text: str) -> str:
    text = text.strip()
    if len(text) <= _OUTPUT_TAIL_CHARS:
        return text
    return "..." + text[-_OUTPUT_TAIL_CHARS:]


def _last_text_from_jsonl(stdout: str) -> str | None:
    for line in reversed(stdout.splitlines()):
        if not line.strip():
            continue
        try:
            payload = json.loads(line)
        except json.JSONDecodeError:
            continue
        text = _find_text(payload)
        if text:
            return text
    return None


def _find_text(value: Any) -> str | None:
    if isinstance(value, str):
        return value
    if isinstance(value, dict):
        for key in ("last_message", "message", "content", "text"):
            found = value.get(key)
            if isinstance(found, str) and found:
                return found
        for nested in value.values():
            if isinstance(nested, (dict, list)):
                found = _find_text(nested)
                if found:
                    return found
    if isinstance(value, list):
        for item in value:
            found = _find_text(item)
            if found:
                return found
    return None
