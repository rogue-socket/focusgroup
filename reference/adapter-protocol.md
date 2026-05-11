# Adapter protocol

The adapter is the user's contract with focusgroup. They implement one function:

```python
from adapters.base import Session, SUTResponse

def respond(user_text: str, session: Session) -> SUTResponse:
    """Given user text and session context, return the SUT's response.

    Args:
        user_text: The persona's most recent utterance.
        session: Mutable session object. session.state is a dict you can read/write
                 to track cross-turn state (auth, slot-filling progress, etc.).
                 session.turn is the current turn index (int).
                 session.history is a list of prior turns (read-only).

    Returns:
        SUTResponse(text=..., tool_calls=[...], metadata={...})
        - text: the SUT's reply to the user
        - tool_calls: optional list of tool invocations (logged to trace.jsonl)
        - metadata: optional dict — latency, token count, cost — logged to trace
    """
```

## Session

```python
class Session:
    state: dict           # mutable cross-turn state; persisted to runs/<id>/state.json
    turn: int             # 0-indexed; incremented after each persona turn
    history: list[Turn]   # read-only view of prior turns in order
    scenario_id: str      # current scenario
    persona_id: str       # which persona is driving
```

## SUTResponse

```python
class SUTResponse:
    text: str                              # required
    tool_calls: list[ToolCall] = []        # optional — each appended to trace.jsonl
    metadata: dict = {}                    # optional — appended to trace.jsonl
```

```python
class ToolCall:
    name: str
    arguments: dict
    result: Any | None = None              # if you executed it
    error: str | None = None
```

## Pre-built wrappers

Five adapters ship with focusgroup. Pick the one that matches your SUT and override only the bits you need.

| Wrapper | Use when | Configure via |
|---|---|---|
| `adapters/openai_compatible.py` | SUT is an OpenAI-compatible chat completions endpoint | `OPENAI_API_KEY`, `model`, `base_url` |
| `adapters/http_chat.py` | SUT is a generic HTTP service | request/response JSONPath spec |
| `adapters/stdio_cli.py` | SUT is a CLI taking stdin and returning stdout | command, prompts |
| `adapters/python_callable.py` | SUT is a Python function/class in your codebase | import path |
| `adapters/base.py` | None of the above fit | implement `respond()` yourself |

## Common patterns

### Stateful SUT with internal session

If your SUT has its own session object, store it in `session.state["sut_session"]` on
the first turn and reuse it:

```python
def respond(user_text, session):
    if "sut_session" not in session.state:
        session.state["sut_session"] = MyAgent.start_session()
    reply = session.state["sut_session"].send(user_text)
    return SUTResponse(text=reply)
```

### Logging tool calls for safety invariants

If safety requirements check "the SUT never called X", emit the tool calls in the response:

```python
def respond(user_text, session):
    reply, tool_calls = my_agent.invoke(user_text)
    return SUTResponse(
        text=reply,
        tool_calls=[
            ToolCall(name=tc.name, arguments=tc.args, result=tc.output)
            for tc in tool_calls
        ],
    )
```

These are written to `trace.jsonl` and consumed by `trace_invariant` oracles.

### Recording latency / cost

```python
import time

def respond(user_text, session):
    t0 = time.monotonic()
    reply = my_agent.respond(user_text)
    return SUTResponse(
        text=reply,
        metadata={
            "latency_ms": (time.monotonic() - t0) * 1000,
            "tokens_in": reply.usage.input,
            "tokens_out": reply.usage.output,
            "cost_usd": estimate_cost(reply.usage),
        },
    )
```

`trace_metric` oracles read these fields.

## Anti-patterns

- **Mutating `session.history`.** It's read-only. Use `session.state` for your own state.
- **Returning `None` or empty text.** The persona loop expects a non-empty reply. Return an error string if your SUT genuinely errored — that's a finding.
- **Catching errors silently.** Let exceptions propagate. The runner will log them as failures.
