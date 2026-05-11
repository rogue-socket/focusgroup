"""Load personas, scenarios, requirements from project files."""
from __future__ import annotations

import re
from pathlib import Path

import yaml

from runner.schemas import Persona, Requirement, Scenario


def load_persona(path: Path) -> Persona:
    return Persona(**yaml.safe_load(path.read_text()))


def load_scenario(path: Path) -> Scenario:
    return Scenario(**yaml.safe_load(path.read_text()))


def load_personas_dir(personas_dir: Path) -> dict[str, Persona]:
    out: dict[str, Persona] = {}
    if not personas_dir.exists():
        return out
    for p in sorted(personas_dir.glob("*.yaml")):
        persona = load_persona(p)
        out[persona.id] = persona
    return out


def load_scenarios_for_feature(features_dir: Path, feature: str) -> list[Scenario]:
    scen_dir = features_dir / feature / "scenarios"
    if not scen_dir.exists():
        return []
    return [load_scenario(p) for p in sorted(scen_dir.glob("*.yaml"))]


def load_all_scenarios(features_dir: Path) -> list[Scenario]:
    out: list[Scenario] = []
    if not features_dir.exists():
        return out
    for feat_dir in sorted(features_dir.iterdir()):
        if feat_dir.is_dir():
            out.extend(load_scenarios_for_feature(features_dir, feat_dir.name))
    return out


# ---------- requirements.md parser ----------

_HEADER_RE = re.compile(r"^###\s+([A-Z]-\d+)\s*[—-]\s*(.+)$")
_TYPE_RE = re.compile(r"^\*\*Type:\*\*\s+(\w+)\s*$", re.IGNORECASE)
_ORACLE_RE = re.compile(r"^\*\*Oracle:\*\*\s+(\w+)\s*$", re.IGNORECASE)


def load_requirements(path: Path) -> dict[str, Requirement]:
    """Parse a requirements.md or requirements.yaml file."""
    if path.suffix in (".yaml", ".yml"):
        data = yaml.safe_load(path.read_text())
        reqs = data.get("requirements", [])
        return {r["id"]: Requirement(**r) for r in reqs}
    return _parse_requirements_md(path.read_text())


def _parse_requirements_md(text: str) -> dict[str, Requirement]:
    out: dict[str, Requirement] = {}
    lines = text.splitlines()
    i = 0
    type_prefix = {"F": "functional", "S": "safety", "P": "performance", "I": "ix", "C": "correctness"}
    while i < len(lines):
        m = _HEADER_RE.match(lines[i])
        if not m:
            i += 1
            continue
        req_id, summary = m.group(1), m.group(2).strip()
        rtype_prefix = req_id[0]
        rtype = type_prefix.get(rtype_prefix)
        description_lines: list[str] = []
        oracle = None
        oracle_config: dict = {}
        notes = None
        j = i + 1
        in_yaml = False
        yaml_buf: list[str] = []
        section = None
        while j < len(lines) and not _HEADER_RE.match(lines[j]):
            line = lines[j]
            if line.startswith("## "):
                break
            t_match = _TYPE_RE.match(line)
            o_match = _ORACLE_RE.match(line)
            if t_match:
                rtype = t_match.group(1).lower()
            elif o_match:
                oracle = o_match.group(1).lower()
            elif line.strip().startswith("**Description:**"):
                section = "description"
                rest = line.split("**Description:**", 1)[1].strip()
                if rest:
                    description_lines.append(rest)
            elif line.strip().startswith("**Notes:**"):
                section = "notes"
                rest = line.split("**Notes:**", 1)[1].strip()
                if rest:
                    notes = rest
            elif line.strip().startswith("**Oracle config:**"):
                section = "oracle_config"
            elif line.strip().startswith("```yaml"):
                in_yaml = True
                yaml_buf = []
            elif line.strip().startswith("```") and in_yaml:
                in_yaml = False
                try:
                    parsed = yaml.safe_load("\n".join(yaml_buf)) or {}
                except Exception:
                    parsed = {}
                if section == "oracle_config":
                    oracle_config.update(parsed)
            elif in_yaml:
                yaml_buf.append(line)
            elif section == "description":
                description_lines.append(line)
            j += 1
        out[req_id] = Requirement(
            id=req_id,
            type=rtype,
            description=" ".join(l.strip() for l in description_lines if l.strip()) or summary,
            oracle=oracle,
            oracle_config=oracle_config,
            notes=notes,
        )
        i = j
    return out


def find_requirements_doc(project_dir: Path) -> Path | None:
    for candidate in (
        "requirements.md", "REQUIREMENTS.md",
        "requirements.yaml", "requirements.yml",
        "docs/requirements.md", "docs/requirements.yaml",
        "spec.md", "PRD.md",
    ):
        p = project_dir / candidate
        if p.exists():
            return p
    return None
