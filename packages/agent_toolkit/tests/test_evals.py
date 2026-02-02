"""Tests for evaluation framework integration."""

import pytest
from agent_toolkit.evals.types import EvalCase, EvalConfig, EvalResult


class TestEvalTypes:
    """Tests for evaluation types."""

    def test_eval_case_creation(self) -> None:
        """Test EvalCase model creation."""
        case = EvalCase(
            name="Test case",
            input="What is 2+2?",
            expected_output="4",
            expected_trajectory=["calculator"],
            metadata={"category": "math"},
        )
        assert case.name == "Test case"
        assert case.input == "What is 2+2?"
        assert case.expected_output == "4"

    def test_eval_case_minimal(self) -> None:
        """Test EvalCase with minimal fields."""
        case = EvalCase(name="Minimal", input="Hello")
        assert case.name == "Minimal"
        assert case.expected_output is None
        assert case.expected_trajectory is None

    def test_eval_config_creation(self) -> None:
        """Test EvalConfig model creation."""
        config = EvalConfig(
            name="Test Experiment",
            description="Test description",
            agent_profile="general",
            cases=[EvalCase(name="Case 1", input="Test input")],
            evaluators=[{"type": "output", "rubric": "Test rubric"}],
        )
        assert config.name == "Test Experiment"
        assert config.agent_profile == "general"
        assert len(config.cases) == 1

    def test_eval_config_with_model_override(self) -> None:
        """Test EvalConfig with model_config alias."""
        config = EvalConfig(
            name="Test",
            agent_profile="general",
            model_config={"temperature": 0.5},
        )
        assert config.model_config_overrides == {"temperature": 0.5}

    def test_eval_result_creation(self) -> None:
        """Test EvalResult model creation."""
        result = EvalResult(
            case_name="Test case",
            passed=True,
            score=0.95,
            reason="Good answer",
            actual_output="4",
            actual_trajectory=["calculator"],
        )
        assert result.passed is True
        assert result.score == 0.95


class TestEvalRunner:
    """Tests for EvalRunner (requires strands_evals - skip if not available)."""

    def test_create_experiment_from_config(self) -> None:
        """Test experiment creation from config."""
        pytest.importorskip("strands_evals")
        from agent_toolkit.evals.runner import create_experiment_from_config

        config = EvalConfig(
            name="Test",
            agent_profile="general",
            cases=[EvalCase(name="Case 1", input="Test", expected_output="Result")],
        )
        experiment = create_experiment_from_config(config)
        assert len(experiment.cases) == 1
