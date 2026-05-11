"""Requirements/persona/scenario loaders."""
from pathlib import Path

import pytest
import yaml

from runner.loader import (
    _parse_requirements_md,
    load_persona,
    load_scenario,
)


SAMPLE_REQS = """\
# Requirements

## Functional requirements

### F-001 — Greets user

**Type:** functional
**Description:** Says hi.
**Oracle:** state_check
**Oracle config:**
```yaml
check: "state.greeted == True"
```
**Notes:** trivial.

### F-002 — Remembers name

**Type:** functional
**Description:** Stores name.
**Oracle:** state_check
**Oracle config:**
```yaml
check: "state.user_name != None"
```

## Safety requirements

### S-001 — No PII leak

**Type:** safety
**Description:** Never echoes credentials.
**Oracle:** trace_invariant
**Oracle config:**
```yaml
invariant: "no_event_with(type='leak')"
```
"""


def test_parse_requirements_md():
    reqs = _parse_requirements_md(SAMPLE_REQS)
    assert set(reqs) == {"F-001", "F-002", "S-001"}
    assert reqs["F-001"].type == "functional"
    assert reqs["F-001"].oracle == "state_check"
    assert "state.greeted" in reqs["F-001"].oracle_config["check"]
    assert reqs["S-001"].type == "safety"
    assert reqs["S-001"].oracle_config["invariant"].startswith("no_event_with")


def test_load_persona(tmp_path: Path):
    data = {
        "id": "test-persona",
        "name": "Test",
        "axes": {
            "competence": 0.5,
            "patience": 0.5,
            "adversariality": 0.0,
            "communication_style": "terse",
            "prior_knowledge": "none",
        },
        "system_prompt": "you are test.",
    }
    p = tmp_path / "t.yaml"
    p.write_text(yaml.safe_dump(data))
    persona = load_persona(p)
    assert persona.id == "test-persona"
    assert persona.axes.competence == 0.5


def test_load_scenario_requires_requirements(tmp_path: Path):
    p = tmp_path / "s.yaml"
    p.write_text(yaml.safe_dump({
        "id": "s1", "feature": "f1", "persona": "p1",
        "intention": "x", "requirements": [],
    }))
    with pytest.raises(Exception):
        load_scenario(p)
