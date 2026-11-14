"""Unit tests for the underwriting and reconciliation evaluation harness."""

import pytest

from eval.evaluate import run_evaluation


def test_offline_evaluation_harness_achieves_full_contract_accuracy():
    summary = run_evaluation("eval/dataset/underwriting_v1.jsonl", force_mock=True)

    assert summary.mode == "offline_heuristic_mock"
    assert summary.total_samples == 10
    assert summary.heuristic_contract_pass_rate == 1.0
    assert summary.live_action_accuracy is None
    assert summary.action_accuracy == 1.0
    assert summary.conflict_accuracy == 1.0
    assert summary.p95_latency_ms >= 0.0


def test_live_evaluation_refuses_to_run_without_api_key(monkeypatch):
    monkeypatch.setattr("src.config.settings.OPENAI_API_KEY", "")
    with pytest.raises(RuntimeError, match="OPENAI_API_KEY"):
        run_evaluation("eval/dataset/underwriting_v1.jsonl", force_mock=False)
