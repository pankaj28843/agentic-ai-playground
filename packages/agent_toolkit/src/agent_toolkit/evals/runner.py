"""Evaluation runner for agent evaluations.

This module provides utilities for running evaluations against agents
using the strands_evals framework.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

from agent_toolkit.evals.types import EvalCase, EvalConfig, EvalResult

if TYPE_CHECKING:
    from strands import Agent
    from strands_evals import Case, Experiment

logger = logging.getLogger(__name__)


def create_strands_case(eval_case: EvalCase) -> Case:
    """Convert an EvalCase to a strands_evals Case.

    Args:
        eval_case: Our EvalCase configuration

    Returns:
        A strands_evals Case object
    """
    from strands_evals import Case  # noqa: PLC0415

    return Case(
        name=eval_case.name,
        input=eval_case.input,
        expected_output=eval_case.expected_output,
        expected_trajectory=eval_case.expected_trajectory,
        metadata=eval_case.metadata,
    )


def create_experiment_from_config(config: EvalConfig) -> Experiment:
    """Create a strands_evals Experiment from our config.

    Args:
        config: EvalConfig with cases and evaluators

    Returns:
        A strands_evals Experiment object
    """
    from strands_evals import Experiment  # noqa: PLC0415
    from strands_evals.evaluators import OutputEvaluator  # noqa: PLC0415

    cases = [create_strands_case(c) for c in config.cases]

    # Create evaluators from config
    evaluators = []
    for eval_config in config.evaluators:
        eval_type = eval_config.get("type", "output")
        if eval_type == "output":
            rubric = eval_config.get("rubric", "The output is relevant and accurate.")
            evaluators.append(OutputEvaluator(rubric=rubric))
        # Add more evaluator types as needed

    # Default to OutputEvaluator if none specified
    if not evaluators:
        evaluators = [
            OutputEvaluator(
                rubric="The output is relevant, accurate, and addresses the input query."
            )
        ]

    return Experiment(cases=cases, evaluators=evaluators)


def run_agent_eval(
    agent: Agent,
    config: EvalConfig,
) -> list[EvalResult]:
    """Run an evaluation experiment against an agent.

    Args:
        agent: The Strands agent to evaluate
        config: Evaluation configuration

    Returns:
        List of EvalResult objects
    """
    experiment = create_experiment_from_config(config)

    def task(case: Any) -> str:
        """Task function that runs the agent on a case input."""
        result = agent(case.input)
        # Check for output first (Strands preferred), then message, then stringify
        if hasattr(result, "output") and result.output:
            return str(result.output)
        return getattr(result, "message", str(result))

    # Run the experiment - returns list of reports
    reports = experiment.run_evaluations(task)

    # Handle both list return (Strands evals API) and object with .results
    if isinstance(reports, list):
        # API returns list of Report objects, take first one's results
        report = reports[0] if reports else None
        case_results = report.results if report else []
    else:
        # Fallback for object with .results attribute
        case_results = getattr(reports, "results", [])

    return [
        EvalResult(
            case_name=case_result.case.name or "unnamed",
            passed=case_result.passed,
            score=case_result.score,
            reason=case_result.reason or "",
            actual_output=str(case_result.actual_output),
            actual_trajectory=case_result.actual_trajectory,
        )
        for case_result in case_results
    ]


class EvalRunner:
    """High-level evaluation runner that integrates with agent_toolkit.

    This class provides a convenient interface for running evaluations
    against agents created from profiles.
    """

    def __init__(
        self,
        config: EvalConfig,
    ) -> None:
        """Initialize the evaluation runner.

        Args:
            config: Evaluation configuration
        """
        self.config = config
        self._results: list[EvalResult] = []

    def run(self, agent: Agent) -> list[EvalResult]:
        """Run the evaluation against an agent.

        Args:
            agent: The agent to evaluate

        Returns:
            List of evaluation results
        """
        self._results = run_agent_eval(agent, self.config)
        return self._results

    @property
    def results(self) -> list[EvalResult]:
        """Get the results from the last run."""
        return self._results

    def summary(self) -> dict[str, Any]:
        """Get a summary of the evaluation results.

        Returns:
            Dictionary with pass_rate, total_cases, passed_cases, avg_score
        """
        if not self._results:
            return {"pass_rate": 0.0, "total_cases": 0, "passed_cases": 0, "avg_score": 0.0}

        total = len(self._results)
        passed = sum(1 for r in self._results if r.passed)
        avg_score = sum(r.score for r in self._results) / total

        return {
            "pass_rate": passed / total,
            "total_cases": total,
            "passed_cases": passed,
            "avg_score": avg_score,
        }
