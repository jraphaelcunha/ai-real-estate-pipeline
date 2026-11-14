"""
Offline and live evaluation harness for real estate underwriting & conflict reconciliation.

Strictly separates deterministic offline verification (--mock) from live LLM provider
telemetry, refusing to fabricate external API metrics when credentials are absent.
"""

import argparse
import json
import math
import os
import sys
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.config import settings
from src.domain.schemas import PropertyInput
from src.services.analyzer import RealEstateAnalyzer


@dataclass
class EvalSampleResult:
    """Per-sample verification outcome."""

    sample_id: str
    expected_action: str
    predicted_action: str
    action_match: bool
    expect_conflict: bool
    detected_conflict: bool
    conflict_match: bool
    latency_ms: float


@dataclass
class EvalSummary:
    """Aggregated evaluation telemetry across all dataset records."""

    mode: str
    total_samples: int
    heuristic_contract_pass_rate: float | None
    live_action_accuracy: float | None
    action_accuracy: float
    conflict_accuracy: float
    p50_latency_ms: float
    p95_latency_ms: float
    results: list[EvalSampleResult] = field(default_factory=list)


def compute_percentile(values: list[float], percentile: float) -> float:
    """Compute percentile using linear interpolation on sorted latency samples."""
    if not values:
        return 0.0
    sorted_vals = sorted(values)
    k = (len(sorted_vals) - 1) * (percentile / 100.0)
    f = math.floor(k)
    c = math.ceil(k)
    if f == c:
        return round(sorted_vals[int(k)], 3)
    d0 = sorted_vals[int(f)] * (c - k)
    d1 = sorted_vals[int(c)] * (k - f)
    return round(d0 + d1, 3)


def run_evaluation(
    dataset_path: str | Path,
    *,
    force_mock: bool = True,
) -> EvalSummary:
    """Execute evaluation suite in deterministic heuristic mode (--mock) or live LLM mode."""
    path = Path(dataset_path)
    if not path.exists():
        raise FileNotFoundError(f"Evaluation dataset not found: {path}")

    if not force_mock and not settings.OPENAI_API_KEY:
        raise RuntimeError(
            "Live evaluation requested without OPENAI_API_KEY configured. "
            "Pass --mock for offline deterministic verification."
        )

    analyzer = RealEstateAnalyzer()
    if force_mock:
        analyzer.heuristic_mode = True
        analyzer.llm = None

    results: list[EvalSampleResult] = []
    latencies: list[float] = []

    with open(path, encoding="utf-8") as handle:
        for line in handle:
            stripped = line.strip()
            if not stripped:
                continue
            record = json.loads(stripped)
            prop = PropertyInput(**record["property"])

            start = time.perf_counter()
            analysis = analyzer.analyze_property(prop)
            elapsed_ms = round((time.perf_counter() - start) * 1000, 3)
            latencies.append(elapsed_ms)

            predicted_action = analysis.recommended_action.value if analysis else "NONE"
            detected_conflict = bool(
                analysis and analysis.reconciliation and not analysis.reconciliation.is_consistent
            )

            expected_action = record["expected_action"]
            expect_conflict = bool(record["expect_conflict"])

            results.append(
                EvalSampleResult(
                    sample_id=record["id"],
                    expected_action=expected_action,
                    predicted_action=predicted_action,
                    action_match=predicted_action == expected_action,
                    expect_conflict=expect_conflict,
                    detected_conflict=detected_conflict,
                    conflict_match=detected_conflict == expect_conflict,
                    latency_ms=elapsed_ms,
                )
            )

    total = len(results)
    action_hits = sum(1 for item in results if item.action_match)
    conflict_hits = sum(1 for item in results if item.conflict_match)
    pass_rate = round(action_hits / total, 4) if total else 0.0

    return EvalSummary(
        mode="offline_heuristic_mock" if force_mock else "live_openai",
        total_samples=total,
        heuristic_contract_pass_rate=pass_rate if force_mock else None,
        live_action_accuracy=None if force_mock else pass_rate,
        action_accuracy=pass_rate,
        conflict_accuracy=round(conflict_hits / total, 4) if total else 0.0,
        p50_latency_ms=compute_percentile(latencies, 50),
        p95_latency_ms=compute_percentile(latencies, 95),
        results=results,
    )


def main() -> None:
    """CLI entrypoint for underwriting evaluation."""
    parser = argparse.ArgumentParser(
        description="Evaluate Real Estate Underwriting & Reconciliation Pipeline"
    )
    parser.add_argument(
        "--dataset",
        default="eval/dataset/underwriting_v1.jsonl",
        help="Path to JSONL evaluation dataset",
    )
    parser.add_argument(
        "--mock",
        action="store_true",
        help="Force deterministic offline heuristic execution (zero API cost)",
    )
    args = parser.parse_args()

    summary = run_evaluation(args.dataset, force_mock=args.mock)
    print(json.dumps(asdict(summary), indent=2))


if __name__ == "__main__":
    main()
