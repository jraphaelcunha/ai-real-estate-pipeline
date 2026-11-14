# Evaluation & Benchmarking Suite

The `eval/` suite validates underwriting action consistency, cross-document conflict detection (`FinancialReconciler`), and end-to-end execution latency against synthetic deal packages (`eval/dataset/underwriting_v1.jsonl`).

## Modes

1. **Offline Deterministic Contract Verification (`--mock`):**
   Exercises schema parsing, `FinancialReconciler` variance checks, `@model_validator` escalation guardrails, and `_compute_heuristic_underwriting` with zero API token spend (`heuristic_contract_pass_rate` verifies deterministic rule regressions; `live_action_accuracy` is explicitly `null` in offline mode):
   ```bash
   python eval/evaluate.py --dataset eval/dataset/underwriting_v1.jsonl --mock
   ```
2. **Live Provider Benchmark:**
   Requires `OPENAI_API_KEY` in `.env` and measures real `gpt-4o-mini` structured extraction (`LLMUnderwritingOutput`) + guardrail enforcement (`live_action_accuracy`):
   ```bash
   python eval/evaluate.py --dataset eval/dataset/underwriting_v1.jsonl
   ```

> **Note:** Synthetic fixtures in `underwriting_v1.jsonl` verify pipeline contracts and deterministic guardrails; they do not substitute for live market comps or human appraisal sign-off.
