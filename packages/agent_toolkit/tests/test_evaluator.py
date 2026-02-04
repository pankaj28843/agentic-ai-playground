"""Tests for Phoenix evaluator helpers."""

import sys
from types import ModuleType
from unittest.mock import MagicMock

from agent_toolkit.telemetry import evaluator
from agent_toolkit.telemetry.evaluator import EvalConfig


def test_create_llm_success(monkeypatch) -> None:
    mock_llm = MagicMock(return_value="llm")
    phoenix_module = ModuleType("phoenix")
    phoenix_module.__path__ = []
    evals_module = ModuleType("phoenix.evals")
    evals_module.__path__ = []
    llm_module = ModuleType("phoenix.evals.llm")
    llm_module.LLM = mock_llm
    monkeypatch.setitem(sys.modules, "phoenix", phoenix_module)
    monkeypatch.setitem(sys.modules, "phoenix.evals", evals_module)
    monkeypatch.setitem(sys.modules, "phoenix.evals.llm", llm_module)

    config = EvalConfig(enabled=True, model="bedrock/model-id")
    result = evaluator._create_llm(config)  # noqa: SLF001

    assert result == "llm"
    mock_llm.assert_called_once_with(provider="litellm", model="bedrock/model-id", client="litellm")


def test_create_llm_failure(monkeypatch) -> None:
    def _boom(*_args, **_kwargs):
        raise RuntimeError("boom")

    phoenix_module = ModuleType("phoenix")
    phoenix_module.__path__ = []
    evals_module = ModuleType("phoenix.evals")
    evals_module.__path__ = []
    llm_module = ModuleType("phoenix.evals.llm")
    llm_module.LLM = _boom
    monkeypatch.setitem(sys.modules, "phoenix", phoenix_module)
    monkeypatch.setitem(sys.modules, "phoenix.evals", evals_module)
    monkeypatch.setitem(sys.modules, "phoenix.evals.llm", llm_module)

    config = EvalConfig(enabled=True, model="bedrock/model-id")
    assert evaluator._create_llm(config) is None  # noqa: SLF001


def test_create_response_quality_evaluator(monkeypatch) -> None:
    mock_eval = MagicMock(return_value="evaluator")
    phoenix_module = ModuleType("phoenix")
    phoenix_module.__path__ = []
    evals_module = ModuleType("phoenix.evals")
    evals_module.__path__ = []
    evals_module.ClassificationEvaluator = mock_eval
    monkeypatch.setitem(sys.modules, "phoenix", phoenix_module)
    monkeypatch.setitem(sys.modules, "phoenix.evals", evals_module)

    config = EvalConfig(enabled=True, model="bedrock/model-id")
    result = evaluator._create_response_quality_evaluator("llm", config)  # noqa: SLF001

    assert result == "evaluator"
    assert mock_eval.called is True
