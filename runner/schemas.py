"""Pydantic schemas for personas, scenarios, requirements."""
from __future__ import annotations

from typing import Any, Literal, Optional

from pydantic import BaseModel, Field, field_validator


class PersonaAxes(BaseModel):
    competence: float = Field(ge=0.0, le=1.0)
    patience: float = Field(ge=0.0, le=1.0)
    adversariality: float = Field(ge=0.0, le=1.0)
    communication_style: str
    prior_knowledge: str


class Persona(BaseModel):
    id: str
    name: str
    archetype: Optional[str] = None
    parent: Optional[str] = None              # for variants
    axes: PersonaAxes
    behaviors: list[str] = Field(default_factory=list)
    speech_examples: list[str] = Field(default_factory=list)
    system_prompt: str


class Bounds(BaseModel):
    max_turns: int = 20
    cost_cap_usd: float = 0.50
    stuck_detection_turns: int = 5
    persona_can_declare_done: bool = True


class Scenario(BaseModel):
    id: str
    feature: str
    persona: str
    intention: str
    initial_state: dict[str, Any] = Field(default_factory=dict)
    requirements: list[str]
    bounds: Bounds = Field(default_factory=Bounds)
    success_criteria: Optional[str] = None
    oracle_overrides: dict[str, dict[str, Any]] = Field(default_factory=dict)

    @field_validator("requirements")
    @classmethod
    def _at_least_one(cls, v):
        if not v:
            raise ValueError("scenario must reference at least one requirement")
        return v


RequirementType = Literal["functional", "safety", "performance", "ix", "correctness"]
OracleType = Literal[
    "state_check",
    "trace_invariant",
    "trace_metric",
    "persona_debrief",
    "llm_judge",
    "custom",
]

DEFAULT_ORACLE: dict[str, OracleType] = {
    "functional": "state_check",
    "safety": "trace_invariant",
    "performance": "trace_metric",
    "ix": "persona_debrief",
    "correctness": "llm_judge",
}


class Requirement(BaseModel):
    id: str
    type: RequirementType
    description: str
    oracle: Optional[OracleType] = None
    oracle_config: dict[str, Any] = Field(default_factory=dict)
    notes: Optional[str] = None

    def resolved_oracle(self) -> OracleType:
        return self.oracle or DEFAULT_ORACLE[self.type]


class Debrief(BaseModel):
    accomplished_goal: Literal["yes", "partial", "no", "gave_up"] = "no"
    accomplished_goal_reason: str = ""
    stuck_points: str = ""
    pain_points: str = ""
    felt_trustworthy: Literal["yes", "mostly", "unsure", "no"] = "unsure"
    felt_trustworthy_reason: str = ""
    would_return: Literal["yes", "maybe", "no"] = "maybe"
    one_change: str = ""


class OracleResult(BaseModel):
    requirement_id: str
    oracle: OracleType
    passed: bool
    evidence: str
    detail: dict[str, Any] = Field(default_factory=dict)
