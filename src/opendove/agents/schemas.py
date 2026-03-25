"""Structured output schemas for each agent role.

Each schema is what the LLM is asked to return. `BaseAgent._call_llm_structured`
uses `llm.with_structured_output(schema)` so responses are validated by Pydantic
before they touch `GraphState`.
"""

from __future__ import annotations

from typing import Annotated, Literal

from pydantic import BeforeValidator


def _normalise_risk_level(v: object) -> object:
    if isinstance(v, str):
        return v.lower()
    return v


RiskLevel = Annotated[Literal["low", "architectural"], BeforeValidator(_normalise_risk_level)]

from pydantic import BaseModel, Field


class ProductManagerOutput(BaseModel):
    """Output from the Product Manager agent."""

    success_criteria: list[str] = Field(
        description=(
            "Concrete, testable acceptance criteria for the task. "
            "Each item must be verifiable by AVA without ambiguity. "
            "Minimum 1, maximum 10."
        ),
        min_length=1,
    )
    scope_note: str = Field(
        description=(
            "One sentence confirming what is explicitly OUT of scope for this task, "
            "to prevent scope creep during implementation."
        )
    )


class ProjectManagerOutput(BaseModel):
    """Output from the Project Manager agent."""

    owner: Literal["product_manager", "project_manager", "lead_architect", "developer", "ava"] = Field(
        description="The role responsible for executing this task. Almost always 'developer'."
    )
    max_retries: int = Field(
        description=(
            "Maximum AVA rejection cycles before escalation. "
            "Use 2 for simple tasks, 3 for standard, 5 for high-complexity tasks."
        ),
        ge=1,
        le=5,
    )
    readiness_note: str = Field(
        description=(
            "Confirm the task is ready to enter the development queue. "
            "Flag any missing information that should be resolved first."
        )
    )


class LeadArchitectOutput(BaseModel):
    """Output from the Lead Architect agent."""

    technical_approach: str = Field(
        description=(
            "Step-by-step implementation plan. Include: "
            "(1) files to create or modify, "
            "(2) key design decisions and rationale, "
            "(3) interfaces or contracts that must be maintained, "
            "(4) testing approach."
        )
    )
    risk_level: RiskLevel = Field(
        description=(
            "Use 'architectural' when the change affects: core interfaces, "
            "database schema, public API contracts, or cross-cutting concerns. "
            "Use 'low' for isolated feature additions or bug fixes."
        )
    )
    affected_files: list[str] = Field(
        description="List of file paths (relative to repo root) expected to be created or modified.",
        default_factory=list,
    )


class DeveloperOutput(BaseModel):
    """Output from the Developer agent."""

    artifact: str = Field(
        description=(
            "Summary of what was implemented. Include: files changed, "
            "key implementation decisions, and how each success criterion is satisfied."
        )
    )
    files_changed: list[str] = Field(
        description="Paths of files actually created or modified (relative to worktree root).",
        default_factory=list,
    )


class ArchitectReviewOutput(BaseModel):
    """Output from the Lead Architect during an AVA-rejection review."""

    revised_approach: str = Field(
        description=(
            "Revised implementation guidance addressing AVA's rejection rationale. "
            "Be specific about what the developer must change."
        )
    )
    root_cause: str = Field(
        description="One sentence identifying the root cause of the AVA rejection."
    )
