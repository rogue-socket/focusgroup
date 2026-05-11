"""stdio CLI adapter.

For SUTs that are command-line programs reading user input on stdin and emitting
responses on stdout. The process is kept alive across turns within a single run.

Configure CONFIG["command"] with the argv to launch. The adapter:
  - writes user_text + newline to stdin
  - reads stdout until a prompt marker (or a quiet period) appears
  - returns the buffered text
"""
from __future__ import annotations

import os
import select
import subprocess
import time

from adapters.base import Session, SUTResponse


CONFIG: dict = {
    "command": ["echo", "configure adapters/stdio_cli.py CONFIG['command']"],
    "prompt_marker": ">>> ",        # if set, reads until this marker appears
    "quiet_period_s": 0.5,          # otherwise reads until no new bytes for this long
    "max_wait_s": 30.0,
    "env": None,                    # extra env vars
}

_PROC_KEY = "_stdio_cli_proc"


def _get_proc(session: Session) -> subprocess.Popen:
    proc = session.state.get(_PROC_KEY)
    if proc and proc.poll() is None:
        return proc
    env = os.environ.copy()
    if CONFIG.get("env"):
        env.update(CONFIG["env"])
    proc = subprocess.Popen(
        CONFIG["command"],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        bufsize=0,
        env=env,
    )
    session.state[_PROC_KEY] = proc
    # drain any banner output
    _read_until_quiet(proc, CONFIG["quiet_period_s"], 2.0)
    return proc


def _read_until_marker(proc: subprocess.Popen, marker: str, max_wait_s: float) -> str:
    buf = b""
    deadline = time.monotonic() + max_wait_s
    while time.monotonic() < deadline:
        rlist, _, _ = select.select([proc.stdout], [], [], 0.1)
        if not rlist:
            continue
        chunk = os.read(proc.stdout.fileno(), 4096)
        if not chunk:
            break
        buf += chunk
        if marker.encode() in buf:
            break
    text = buf.decode("utf-8", errors="replace")
    return text.replace(marker, "").strip()


def _read_until_quiet(proc: subprocess.Popen, quiet_s: float, max_wait_s: float) -> str:
    buf = b""
    deadline = time.monotonic() + max_wait_s
    last_byte_at = time.monotonic()
    while time.monotonic() < deadline:
        rlist, _, _ = select.select([proc.stdout], [], [], 0.05)
        if rlist:
            chunk = os.read(proc.stdout.fileno(), 4096)
            if chunk:
                buf += chunk
                last_byte_at = time.monotonic()
                continue
        if buf and (time.monotonic() - last_byte_at) >= quiet_s:
            break
    return buf.decode("utf-8", errors="replace").strip()


def respond(user_text: str, session: Session) -> SUTResponse:
    proc = _get_proc(session)
    assert proc.stdin is not None
    t0 = time.monotonic()
    proc.stdin.write((user_text + "\n").encode("utf-8"))
    proc.stdin.flush()
    if CONFIG.get("prompt_marker"):
        text = _read_until_marker(proc, CONFIG["prompt_marker"], CONFIG["max_wait_s"])
    else:
        text = _read_until_quiet(proc, CONFIG["quiet_period_s"], CONFIG["max_wait_s"])
    latency_ms = (time.monotonic() - t0) * 1000.0
    return SUTResponse(text=text, metadata={"latency_ms": latency_ms})
