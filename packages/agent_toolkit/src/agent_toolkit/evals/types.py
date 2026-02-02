"""Pydantic types for evaluation configuration."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class EvalCase(BaseModel, frozen=True):
    """A single evaluation test case.

    Attributes:
        name: Human-readable name for the test case
        input: The input/query to test
        expected_output: Expected output (for semantic comparison)
        expected_trajectory: Expected sequence of tool calls
        metadata: Additional case metadata
    """

    name: str
    input: str
    expected_output: str | None = None
    expected_trajectory: list[str] | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class EvalConfig(BaseModel, frozen=True):
    """Configuration for an evaluation experiment.

    Attributes:
        name: Experiment name
        description: Experiment description
        agent_profile: Name of agent profile to evaluate
        cases: List of test cases
        evaluators: List of evaluator configurations
        model_config: Model config overrides for evaluation
    """

    name: str
    description: str = ""
    agent_profile: str
    cases: list[EvalCase] = Field(default_factory=list)
    evaluators: list[dict[str, Any]] = Field(default_factory=list)
    model_config_overrides: dict[str, Any] = Field(default_factory=dict, alias="model_config")

    model_config = {"populate_by_name": True}


class EvalResult(BaseModel):
    """Result of a single evaluation case.

    Attributes:
        case_name: Name of the test case
        passed: Whether the test passed
        score: Numeric score (0.0-1.0)
        reason: Explanation of the result
        actual_output: Actual agent output
        actual_trajectory: Actual tool call sequence
        metadata: Additional result metadata
    """

    case_name: str
    passed: bool
    score: float
    reason: str = ""
    actual_output: str | None = None
    actual_trajectory: list[str] | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
