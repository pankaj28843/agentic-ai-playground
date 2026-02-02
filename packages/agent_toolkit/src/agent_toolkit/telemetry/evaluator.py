"""Online evaluation service using Phoenix evals with Bedrock models.

Provides real-time evaluation of agent responses for quality metrics like
hallucination detection, relevance scoring, and response quality.

NOTE: Phoenix's ClassificationEvaluator requires structured JSON output (response_format).
Bedrock models via LiteLLM don't support this feature, causing JSON decode errors.
Online evals are disabled by default until:
  - LiteLLM adds response_format support for Bedrock
  - Phoenix adds text-parsing fallback for ClassificationEvaluator
  - An OpenAI API key is configured (OpenAI models work)
"""

from __future__ import annotations

import logging
import random
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from phoenix.evals.evaluators import ClassificationEvaluator
    from phoenix.evals.llm import LLM

logger = logging.getLogger(__name__)

# Default EU Bedrock model for evals (cost-effective)
DEFAULT_EVAL_MODEL = "bedrock/eu.amazon.nova-micro-v1:0"


@dataclass
class EvalConfig:
    """Configuration for online evaluation."""

    enabled: bool
    model: str  # LiteLLM format: bedrock/{model_id}
    temperature: float = 0.0
    max_tokens: int = 256
    sample_rate: float = 0.1  # Fraction of responses to evaluate (0.0-1.0)

    @classmethod
    def from_settings(cls, settings: Any) -> EvalConfig:
        """Create config from Settings dataclass."""
        return cls(
            enabled=getattr(settings, "online_eval_enabled", False),
            model=getattr(settings, "online_eval_model", DEFAULT_EVAL_MODEL),
            temperature=getattr(settings, "online_eval_temperature", 0.0),
            max_tokens=getattr(settings, "online_eval_max_tokens", 256),
            sample_rate=getattr(settings, "online_eval_sample_rate", 0.1),
        )


@dataclass
class EvalResult:
    """Result of an evaluation."""

    evaluator_name: str
    label: str | None
    score: float | None
    explanation: str | None


def _create_llm(config: EvalConfig) -> LLM | None:
    """Create a Phoenix LLM wrapper for Bedrock via LiteLLM.

    Args:
        config: Evaluation configuration.

    Returns:
        LLM wrapper or None if creation fails.
    """
    try:
        from phoenix.evals.llm import LLM  # noqa: PLC0415

        # Use LiteLLM provider for Bedrock access
        # Model format: bedrock/{model_id}
        return LLM(
            provider="litellm",
            model=config.model,
            client="litellm",
        )
    except ImportError:
        logger.warning("phoenix.evals not available - install arize-phoenix-evals")
        return None
    except Exception:
        logger.exception("Failed to create LLM for evaluation")
        return None


def _create_response_quality_evaluator(
    llm: LLM, config: EvalConfig
) -> ClassificationEvaluator | None:
    """Create evaluator for response quality assessment.

    Evaluates whether the agent response is helpful, accurate, and well-formatted.
    """
    try:
        from phoenix.evals import ClassificationEvaluator  # noqa: PLC0415

        template = """You are evaluating an AI assistant's response quality.

User Query: {input}

Assistant Response: {output}

Evaluate the response on these criteria:
1. Helpfulness: Does it address the user's query?
2. Accuracy: Is the information correct (to the best of your knowledge)?
3. Clarity: Is it well-structured and easy to understand?

Classify the response as one of:
- "excellent": Meets all criteria very well
- "good": Meets most criteria adequately
- "poor": Fails to meet important criteria

Respond with just the classification label."""

        return ClassificationEvaluator(
            name="response_quality",
            prompt_template=template,
            choices={"excellent": 1.0, "good": 0.5, "poor": 0.0},
            llm=llm,
            temperature=config.temperature,
            max_tokens=config.max_tokens,
        )
    except Exception:
        logger.exception("Failed to create response quality evaluator")
        return None


def _create_hallucination_evaluator(llm: LLM, config: EvalConfig) -> ClassificationEvaluator | None:
    """Create evaluator for hallucination detection.

    Checks if the response contains information not grounded in provided context.
    """
    try:
        from phoenix.evals import ClassificationEvaluator  # noqa: PLC0415

        template = """You are evaluating whether an AI assistant's response contains hallucinations.

A hallucination is when the AI makes up information that:
- Was not in any provided context/documentation
- Is factually incorrect
- Claims certainty about uncertain topics

User Query: {input}

Assistant Response: {output}

Context/Sources Used (if any): {context}

Does this response contain hallucinations?

Classify as:
- "factual": Response is grounded in provided context or common knowledge
- "uncertain": Response makes claims that cannot be verified
- "hallucinated": Response contains clear fabrications or errors

Respond with just the classification label."""

        return ClassificationEvaluator(
            name="hallucination",
            prompt_template=template,
            choices={"factual": 1.0, "uncertain": 0.5, "hallucinated": 0.0},
            llm=llm,
            temperature=config.temperature,
            max_tokens=config.max_tokens,
        )
    except Exception:
        logger.exception("Failed to create hallucination evaluator")
        return None


class OnlineEvaluator:
    """Service for real-time evaluation of agent responses."""

    def __init__(self, config: EvalConfig) -> None:
        """Initialize the evaluator service.

        Args:
            config: Evaluation configuration.
        """
        self._config = config
        self._llm: LLM | None = None
        self._evaluators: dict[str, ClassificationEvaluator] = {}
        self._initialized = False

    @property
    def enabled(self) -> bool:
        """Check if online evaluation is enabled."""
        return self._config.enabled

    def should_sample(self) -> bool:
        """Determine if this response should be evaluated based on sample rate."""
        return random.random() < self._config.sample_rate  # noqa: S311

    def setup(self) -> bool:
        """Initialize evaluators lazily.

        Returns:
            True if setup succeeded, False otherwise.
        """
        if not self._config.enabled:
            logger.debug("Online evaluation is disabled")
            return False

        if self._initialized:
            return True

        self._llm = _create_llm(self._config)
        if self._llm is None:
            return False

        # Create evaluators
        quality_eval = _create_response_quality_evaluator(self._llm, self._config)
        if quality_eval:
            self._evaluators["response_quality"] = quality_eval

        hallucination_eval = _create_hallucination_evaluator(self._llm, self._config)
        if hallucination_eval:
            self._evaluators["hallucination"] = hallucination_eval

        self._initialized = bool(self._evaluators)
        if self._initialized:
            logger.info(
                "Online evaluation initialized with %d evaluators: %s",
                len(self._evaluators),
                list(self._evaluators.keys()),
            )
        return self._initialized

    def _build_eval_input(
        self,
        input_text: str,
        output_text: str,
        context: str,
    ) -> dict[str, str]:
        """Build evaluation input dictionary."""
        return {
            "input": input_text,
            "output": output_text,
            "context": context or "No specific context provided.",
        }

    def _select_evaluators(
        self, evaluator_names: list[str] | None
    ) -> dict[str, ClassificationEvaluator]:
        """Select evaluators to run based on optional name filter."""
        if evaluator_names:
            return {n: self._evaluators[n] for n in evaluator_names if n in self._evaluators}
        return self._evaluators

    @staticmethod
    def _score_to_result(name: str, score: Any) -> EvalResult:
        """Convert a score object to EvalResult."""
        return EvalResult(
            evaluator_name=name,
            label=getattr(score, "label", None),
            score=getattr(score, "score", None),
            explanation=getattr(score, "explanation", None),
        )

    def evaluate(
        self,
        input_text: str,
        output_text: str,
        context: str = "",
        evaluator_names: list[str] | None = None,
    ) -> list[EvalResult]:
        """Evaluate an agent response.

        Args:
            input_text: The user's input/query.
            output_text: The agent's response.
            context: Optional context/sources used (for hallucination detection).
            evaluator_names: Optional list of specific evaluators to run.
                            If None, runs all available evaluators.

        Returns:
            List of evaluation results.
        """
        if not self.setup():
            return []

        results: list[EvalResult] = []
        eval_input = self._build_eval_input(input_text, output_text, context)
        evaluators_to_run = self._select_evaluators(evaluator_names)

        for name, evaluator in evaluators_to_run.items():
            try:
                scores = evaluator.evaluate(eval_input)
                if scores:
                    result = self._score_to_result(name, scores[0])
                    results.append(result)
                    logger.debug("Eval %s: label=%s score=%s", name, result.label, result.score)
            except Exception:
                logger.exception("Evaluation failed for %s", name)

        return results

    async def evaluate_async(
        self,
        input_text: str,
        output_text: str,
        context: str = "",
        evaluator_names: list[str] | None = None,
    ) -> list[EvalResult]:
        """Async version of evaluate.

        Args:
            input_text: The user's input/query.
            output_text: The agent's response.
            context: Optional context/sources used.
            evaluator_names: Optional list of specific evaluators to run.

        Returns:
            List of evaluation results.
        """
        if not self.setup():
            return []

        results: list[EvalResult] = []
        eval_input = self._build_eval_input(input_text, output_text, context)
        evaluators_to_run = self._select_evaluators(evaluator_names)

        for name, evaluator in evaluators_to_run.items():
            try:
                scores = await evaluator.async_evaluate(eval_input)
                if scores:
                    results.append(self._score_to_result(name, scores[0]))
            except Exception:
                logger.exception("Async evaluation failed for %s", name)

        return results


# Module-level singleton
_evaluator: OnlineEvaluator | None = None


def get_online_evaluator(config: EvalConfig | None = None) -> OnlineEvaluator:
    """Get the singleton online evaluator instance.

    Args:
        config: Optional config (only used on first call).

    Returns:
        OnlineEvaluator instance.
    """
    global _evaluator  # noqa: PLW0603
    if _evaluator is None:
        if config is None:
            config = EvalConfig(enabled=False, model=DEFAULT_EVAL_MODEL)
        _evaluator = OnlineEvaluator(config)
    return _evaluator


def reset_evaluator() -> None:
    """Reset the singleton evaluator (useful for testing)."""
    global _evaluator  # noqa: PLW0603
    _evaluator = None
