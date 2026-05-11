"""Python callable adapter — in-process testing of a Python module.

Configure CONFIG["import_path"] to point at either:
  - "package.module.respond"  — a callable matching the protocol directly
  - "package.module.Agent"    — a class; the adapter instantiates it and calls .respond()

The instance is cached in session.state across turns.
"""
from __future__ import annotations

import importlib
import time
from typing import Any, Callable

from adapters.base import Session, SUTResponse


CONFIG: dict = {
    "import_path": None,  # e.g. "my_pkg.agent.MyAgent" or "my_pkg.agent.respond"
}

_FN_KEY = "_python_callable_fn"
_INSTANCE_KEY = "_python_callable_instance"


def _resolve(path: str) -> Any:
    mod_path, _, attr = path.rpartition(".")
    if not mod_path:
        raise ValueError(f"Invalid import_path: {path!r}")
    mod = importlib.import_module(mod_path)
    return getattr(mod, attr)


def _get_callable(session: Session) -> Callable[[str, Session], SUTResponse]:
    cached = session.state.get(_FN_KEY)
    if cached:
        return cached
    path = CONFIG["import_path"]
    if not path:
        raise RuntimeError("Set adapters.python_callable.CONFIG['import_path'].")
    target = _resolve(path)
    if isinstance(target, type):
        instance = session.state.get(_INSTANCE_KEY) or target()
        session.state[_INSTANCE_KEY] = instance
        fn = lambda text, sess: _adapt(instance.respond(text, sess), instance)
    else:
        fn = lambda text, sess: _adapt(target(text, sess), None)
    session.state[_FN_KEY] = fn
    return fn


def _adapt(result, _instance) -> SUTResponse:
    if isinstance(result, SUTResponse):
        return result
    if isinstance(result, str):
        return SUTResponse(text=result)
    if isinstance(result, dict) and "text" in result:
        return SUTResponse(
            text=result["text"],
            metadata=result.get("metadata", {}),
        )
    raise TypeError(f"Unsupported respond() return type: {type(result)}")


def respond(user_text: str, session: Session) -> SUTResponse:
    fn = _get_callable(session)
    t0 = time.monotonic()
    out = fn(user_text, session)
    out.metadata.setdefault("latency_ms", (time.monotonic() - t0) * 1000.0)
    return out
